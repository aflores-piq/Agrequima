"""Agregaciones del dashboard de plaguicidas, calculadas en SQL/SQLAlchemy
sobre dbo.Importacion (no en el frontend).

Cada bloque (gráfico o tabla) se calcula en una función `df_*` que
devuelve un DataFrame de pandas — es la única fuente de verdad para ese
bloque, reutilizada tanto por `obtener_dashboard_plaguicidas` (JSON para
la pantalla) como por `services/export.py` (descarga en Excel), así lo
exportado es siempre idéntico a lo que se ve en pantalla.

Nota: el filtro de "Departamento/Aduana" que aparece en el dashboard de
Power BI original queda pendiente (ver sección 9 del documento de
instrucciones) porque sus categorías no corresponden a ninguna columna
documentada de dbo.Importacion.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy import Integer, cast, func, literal_column, or_
from sqlalchemy.orm import Query, Session

from app.models.importacion import Importacion
from app.schemas.dashboard import (
    ComparacionAcumuladaMensual,
    ComparacionMensual,
    DashboardPlaguicidasResponse,
    DetalleTransaccionPlaguicida,
    GrupoItem,
    KpisPlaguicidas,
    NombreComercialItem,
    OpcionesFiltroPlaguicidas,
    PaginaDetallePlaguicidas,
    PuntoAcumuladoAnual,
    RankingItem,
    ResumenItem,
    SerieAcumuladoAnual,
)
from app.services.clasificacion import CATEGORIAS_APLICACION_ORDEN, clasificar_aplicacion
from app.services.df_utils import series_multianual_desde_df, sin_nan

_TOP_N = 10
_TABLA_RESUMEN_MAX = 50

# Valor especial del filtro de "Ingrediente activo" (que en realidad
# filtra por Importacion.Grupo, ver _aplicar_filtros) para seleccionar las
# filas que quedaron sin agrupador (Grupo IS NULL) — no es un valor real
# del catálogo, así que no puede confundirse con un Grupo legítimo.
SIN_AGRUPADOR = "Sin agrupador"


def _mes_expr():
    # dbo.Importacion.fecha es VARCHAR(15) en formato "YYYY/MM/DD"
    # (lo produce el propio ETL), así que el mes son los caracteres 6-7.
    # Los índices van como literal_column (no bind params): SQL Server no
    # reconoce dos SUBSTRING(fecha, ?, ?) parametrizados por separado como
    # la misma expresión al validar el SELECT contra el GROUP BY.
    return cast(func.substring(Importacion.fecha, literal_column("6"), literal_column("2")), Integer)


def _valores_crudos_para_categoria(db: Session, categoria: str) -> list[str]:
    """El filtro de Aplicación recibe una categoría normalizada (ej.
    'Herbicida'); esto la traduce a la lista de valores crudos de
    dbo.Importacion.aplicacion que caen en esa categoría, para poder
    filtrar con IN en SQL (la clasificación en sí vive en Python)."""
    todos = [a for (a,) in db.query(Importacion.aplicacion).distinct().all() if a]
    return [a for a in todos if clasificar_aplicacion(a) == categoria]


def _filtro_grupo(query, valores: list[str] | None):
    """Filtro de Grupo con selección múltiple (OR entre los valores
    marcados). SIN_AGRUPADOR se combina con el resto en vez de ser
    exclusivo: si viene junto con Grupos reales, el resultado es
    (Grupo IN (reales) OR Grupo IS NULL)."""
    if not valores:
        return query
    incluye_sin_agrupador = SIN_AGRUPADOR in valores
    valores_reales = [v for v in valores if v != SIN_AGRUPADOR]
    condiciones = []
    if valores_reales:
        condiciones.append(Importacion.Grupo.in_(valores_reales))
    if incluye_sin_agrupador:
        condiciones.append(Importacion.Grupo.is_(None))
    return query.filter(or_(*condiciones)) if condiciones else query


def _aplicar_filtros(
    query,
    db: Session,
    origen: list[str] | None,
    ingrediente_act: list[str] | None,
    aplicacion: list[str] | None,
    producto: list[str] | None,
):
    if origen:
        query = query.filter(Importacion.origen.in_(origen))
    query = _filtro_grupo(query, ingrediente_act)
    if aplicacion:
        valores = [v for categoria in aplicacion for v in _valores_crudos_para_categoria(db, categoria)]
        query = query.filter(Importacion.aplicacion.in_(valores)) if valores else query.filter(False)
    if producto:
        query = query.filter(Importacion.producto.in_(producto))
    return query


def _anio_default(db: Session) -> int:
    return db.query(func.max(Importacion.anio)).scalar() or 0


def obtener_opciones_filtro_plaguicidas(db: Session) -> OpcionesFiltroPlaguicidas:
    """Valores reales y distintos para poblar los dropdowns/autocompletado
    de la fila de filtros (en vez de cuadros de texto en blanco)."""
    anios = sorted(
        (a for (a,) in db.query(Importacion.anio).distinct().all() if a is not None), reverse=True
    )
    origenes = sorted({o for (o,) in db.query(Importacion.origen).distinct().all() if o})
    aplicaciones_crudas = [a for (a,) in db.query(Importacion.aplicacion).distinct().all() if a]
    categorias_presentes = {clasificar_aplicacion(a) for a in aplicaciones_crudas}
    aplicaciones = [c for c in CATEGORIAS_APLICACION_ORDEN if c in categorias_presentes]
    grupos_presentes = db.query(Importacion.Grupo).distinct().all()
    ingredientes_activos = sorted({g for (g,) in grupos_presentes if g})
    if any(g is None for (g,) in grupos_presentes):
        ingredientes_activos.append(SIN_AGRUPADOR)
    productos = sorted({p for (p,) in db.query(Importacion.producto).distinct().all() if p})
    return OpcionesFiltroPlaguicidas(
        anios=anios,
        origenes=origenes,
        aplicaciones=aplicaciones,
        ingredientes_activos=ingredientes_activos,
        productos=productos,
    )


def _mes_maximo_disponible(db: Session, anio: int) -> int:
    """Mes por defecto del selector 'hasta el mes': el mes más reciente
    con datos EN dbo.Importacion para el año seleccionado (no un valor
    fijo ni compartido con nutrientes, que vive en otra tabla)."""
    mes_expr = _mes_expr()
    resultado = db.query(func.max(mes_expr)).filter(Importacion.anio == anio).scalar()
    return int(resultado) if resultado else 12


@dataclass
class ContextoPlaguicidas:
    """Filtros y años ya resueltos + las dos queries base (año actual y
    año anterior, con todos los filtros y el tope de mes ya aplicados).
    Todas las funciones df_* parten de aquí, así que un cambio de filtro
    se refleja igual en pantalla y en el Excel exportado."""

    db: Session
    anio_actual: int
    anio_anterior: int
    mes_seleccionado: int
    mes_maximo: int
    base_actual: Query
    base_anterior: Query
    cif_total: float
    base_para_anio: Any  # Callable[[int], Query] — mismos filtros/tope de mes, año arbitrario


def construir_contexto_plaguicidas(
    db: Session,
    anio: int | None,
    mes: int | None,
    origen: list[str] | None,
    ingrediente_act: list[str] | None,
    aplicacion: list[str] | None,
    producto: list[str] | None,
) -> ContextoPlaguicidas:
    anio_actual = anio or _anio_default(db)
    anio_anterior = anio_actual - 1
    mes_maximo = _mes_maximo_disponible(db, anio_actual)
    mes_seleccionado = mes or mes_maximo

    mes_expr = _mes_expr()

    def _base(anio_query: int):
        query = _aplicar_filtros(
            db.query(Importacion).filter(Importacion.anio == anio_query),
            db, origen, ingrediente_act, aplicacion, producto,
        )
        # El selector "hasta el mes" acota TODO el dashboard (KPIs,
        # gráficos, tablas) a Enero..mes_seleccionado, en ambos años que
        # se comparan — no solo los dos gráficos mensuales.
        return query.filter(mes_expr <= mes_seleccionado)

    base_actual = _base(anio_actual)
    base_anterior = _base(anio_anterior)
    cif_total = float(base_actual.with_entities(func.sum(Importacion.cif_USD)).scalar() or 0) or 1

    return ContextoPlaguicidas(
        db=db,
        anio_actual=anio_actual,
        anio_anterior=anio_anterior,
        mes_seleccionado=mes_seleccionado,
        mes_maximo=mes_maximo,
        base_actual=base_actual,
        base_anterior=base_anterior,
        cif_total=cif_total,
        base_para_anio=_base,
    )


def _kpis_plaguicidas(ctx: ContextoPlaguicidas) -> KpisPlaguicidas:
    fila = ctx.base_actual.with_entities(
        func.sum(Importacion.cif_USD),
        func.sum(Importacion.cif_Q),
        func.count(Importacion.importacionplaguicidaid),
        func.count(Importacion.ingrediente_act.distinct()),
    ).one()
    return KpisPlaguicidas(
        cif_total_usd=float(fila[0] or 0),
        cif_total_q=float(fila[1] or 0),
        registros=int(fila[2] or 0),
        ingredientes_activos=int(fila[3] or 0),
    )


def _totales_por_mes(query: Query) -> dict[int, float]:
    mes_expr = _mes_expr()
    return dict(query.with_entities(mes_expr, func.sum(Importacion.cif_USD)).group_by(mes_expr).all())


def df_acumulado_mensual(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Gráfico 1: comparativo acumulado de CIF USD por mes."""
    totales_actual = _totales_por_mes(ctx.base_actual)
    totales_anterior = _totales_por_mes(ctx.base_anterior)
    acumulado_actual = 0.0
    acumulado_anterior = 0.0
    filas = []
    for m in range(1, ctx.mes_seleccionado + 1):
        acumulado_actual += float(totales_actual.get(m) or 0)
        acumulado_anterior += float(totales_anterior.get(m) or 0)
        filas.append((m, acumulado_actual, acumulado_anterior))
    return pd.DataFrame(filas, columns=["mes", "cif_usd_actual_acumulado", "cif_usd_anterior_acumulado"])


def df_comparativo_mensual(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Gráfico 2: comparación mensual de CIF (actual vs. anterior)."""
    totales_actual = _totales_por_mes(ctx.base_actual)
    totales_anterior = _totales_por_mes(ctx.base_anterior)
    filas = [
        (m, float(totales_actual.get(m) or 0), float(totales_anterior.get(m) or 0))
        for m in range(1, ctx.mes_seleccionado + 1)
    ]
    return pd.DataFrame(filas, columns=["mes", "cif_usd_actual", "cif_usd_anterior"])


_VENTANA_MULTIANUAL = 5


def df_acumulado_multianual(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Gráfico nuevo: comparativo acumulado de CIF USD por año — una
    línea por cada año del año seleccionado y hasta los 4 anteriores (5
    en total) que tenga al menos una fila con los filtros activos hasta
    el mismo mes de corte (ctx.mes_seleccionado, sin recalcularlo). Un
    año sin ninguna fila en esa ventana simplemente no aparece (no se
    dibuja en cero)."""
    filas = []
    for anio in range(ctx.anio_actual, ctx.anio_actual - _VENTANA_MULTIANUAL, -1):
        totales = _totales_por_mes(ctx.base_para_anio(anio))
        if not totales:
            continue
        acumulado = 0.0
        for m in range(1, ctx.mes_seleccionado + 1):
            acumulado += float(totales.get(m) or 0)
            filas.append((anio, m, acumulado))
    return pd.DataFrame(filas, columns=["anio", "mes", "cif_usd_acumulado"])


def df_acumulado_multianual_ancho(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Misma información que df_acumulado_multianual, en formato ancho
    (una columna por año) para exportar a Excel."""
    df = df_acumulado_multianual(ctx)
    if df.empty:
        return pd.DataFrame(columns=["mes"])
    ancho = df.pivot(index="mes", columns="anio", values="cif_usd_acumulado").reset_index()
    anios_desc = sorted(ancho.columns[1:], reverse=True)  # pivot ordena ascendente por defecto
    ancho = ancho[["mes"] + anios_desc]
    ancho.columns = ["mes"] + [f"CIF USD {c}" for c in anios_desc]
    return ancho


def df_por_aplicacion(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Gráfico 3: dona de diversificación por tipo de aplicación.

    aplicacion trae >60 variantes de texto crudo; se normaliza a un
    conjunto fijo y pequeño de categorías antes de agrupar (orden y
    color de cada categoría son fijos, ver theme/colors.ts en el
    frontend)."""
    cif_por_categoria: dict[str, float] = defaultdict(float)
    for aplicacion_raw, cif_usd in ctx.base_actual.with_entities(
        Importacion.aplicacion, func.sum(Importacion.cif_USD)
    ).group_by(Importacion.aplicacion).all():
        categoria = clasificar_aplicacion(aplicacion_raw)
        cif_por_categoria[categoria] += float(cif_usd or 0)

    filas = [
        (c, cif_por_categoria[c]) for c in CATEGORIAS_APLICACION_ORDEN if c in cif_por_categoria
    ]
    return pd.DataFrame(filas, columns=["etiqueta", "cif_usd"])


def _df_ranking(query: Query, columna, limite: int) -> pd.DataFrame:
    filas = (
        query.with_entities(columna, func.sum(Importacion.cif_USD))
        .filter(columna.isnot(None))
        .group_by(columna)
        .order_by(func.sum(Importacion.cif_USD).desc())
        .limit(limite)
        .all()
    )
    return pd.DataFrame(
        [(fila[0], float(fila[1] or 0)) for fila in filas], columns=["etiqueta", "cif_usd"]
    )


def df_top_moleculas(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Gráfico 4: top ingredientes activos (moléculas) por CIF USD."""
    return _df_ranking(ctx.base_actual, Importacion.ingrediente_act, _TOP_N)


def df_top_importadores(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Gráfico 5: top importadores por CIF USD."""
    return _df_ranking(ctx.base_actual, Importacion.importador, _TOP_N)


def _df_resumen(query: Query, columna, cif_total: float, limite: int) -> pd.DataFrame:
    filas = (
        query.with_entities(columna, func.count(Importacion.importacionplaguicidaid), func.sum(Importacion.cif_USD))
        .filter(columna.isnot(None))
        .group_by(columna)
        .order_by(func.sum(Importacion.cif_USD).desc())
        .limit(limite)
        .all()
    )
    return pd.DataFrame(
        [
            (
                fila[0],
                int(fila[1]),
                float(fila[2] or 0),
                round(float(fila[2] or 0) / cif_total * 100, 2),
            )
            for fila in filas
        ],
        columns=["etiqueta", "transacciones", "cif_usd", "porcentaje_del_total"],
    )


def df_top_paises(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Gráfico 6: top países de origen (tabla numerada)."""
    return _df_resumen(ctx.base_actual, Importacion.origen, ctx.cif_total, _TOP_N)


def df_resumen_importadores(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Tabla: importadores — transacciones y CIF (no forma parte de los
    elementos exportables pedidos, pero se deja disponible por si se
    necesita más adelante)."""
    return _df_resumen(ctx.base_actual, Importacion.importador, ctx.cif_total, _TABLA_RESUMEN_MAX)


def df_nombres_comerciales(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Tabla: nombres comerciales, ordenado por CIF USD."""
    filas = (
        ctx.base_actual.with_entities(
            Importacion.producto,
            Importacion.Grupo,
            Importacion.aplicacion,
            Importacion.importador,
            Importacion.origen,
            func.sum(Importacion.cantidad),
            Importacion.unidad_medida,
            func.sum(Importacion.cif_USD),
            func.sum(Importacion.cif_Q),
        )
        .filter(Importacion.producto.isnot(None))
        .group_by(
            Importacion.producto,
            Importacion.Grupo,
            Importacion.aplicacion,
            Importacion.importador,
            Importacion.origen,
            Importacion.unidad_medida,
        )
        .order_by(func.sum(Importacion.cif_USD).desc())
        .limit(_TABLA_RESUMEN_MAX)
        .all()
    )
    return sin_nan(pd.DataFrame(
        [
            (
                f[0], f[1], f[2], f[3], f[4],
                float(f[5] or 0), f[6], float(f[7] or 0), float(f[8] or 0),
            )
            for f in filas
        ],
        columns=[
            "producto", "grupo", "aplicacion", "importador", "origen",
            "cantidad", "unidad_medida", "cif_usd", "cif_q",
        ],
    ))


def df_grupo(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Tabla: grupo, ordenado por CIF USD.

    SQL Server no tiene MODE() nativo: se trae (Grupo, aplicacion,
    unidad_medida) ya sumado por combinación, y la "aplicación
    principal"/"unidad" de cada Grupo se resuelve en Python como la
    combinación con más transacciones dentro de ese Grupo."""
    filas_detalle = (
        ctx.base_actual.with_entities(
            Importacion.Grupo,
            Importacion.aplicacion,
            Importacion.unidad_medida,
            func.count(Importacion.importacionplaguicidaid),
            func.sum(Importacion.cantidad),
            func.sum(Importacion.cif_USD),
            func.sum(Importacion.cif_Q),
        )
        .filter(Importacion.Grupo.isnot(None))
        .group_by(Importacion.Grupo, Importacion.aplicacion, Importacion.unidad_medida)
        .all()
    )
    agregados: dict[str, dict[str, Any]] = {}
    for grupo, aplicacion_fila, unidad, transacciones, cantidad, cif_usd_fila, cif_q_fila in filas_detalle:
        acc = agregados.setdefault(
            grupo,
            {"cantidad": 0.0, "cif_usd": 0.0, "cif_q": 0.0, "aplicaciones": Counter(), "unidades": Counter()},
        )
        acc["cantidad"] += float(cantidad or 0)
        acc["cif_usd"] += float(cif_usd_fila or 0)
        acc["cif_q"] += float(cif_q_fila or 0)
        acc["aplicaciones"][aplicacion_fila] += transacciones
        acc["unidades"][unidad] += transacciones

    filas = [
        (
            grupo,
            round(datos["cif_usd"] / ctx.cif_total * 100, 2),
            datos["aplicaciones"].most_common(1)[0][0] if datos["aplicaciones"] else None,
            datos["cantidad"],
            datos["unidades"].most_common(1)[0][0] if datos["unidades"] else None,
            datos["cif_usd"],
            datos["cif_q"],
        )
        for grupo, datos in sorted(agregados.items(), key=lambda kv: -kv[1]["cif_usd"])[:_TABLA_RESUMEN_MAX]
    ]
    return sin_nan(pd.DataFrame(
        filas,
        columns=["grupo", "porcentaje_del_total", "aplicacion_principal", "cantidad", "unidad_medida", "cif_usd", "cif_q"],
    ))


def df_detalle(ctx: ContextoPlaguicidas) -> pd.DataFrame:
    """Detalle de transacciones — TODAS las filas que cumplen el filtro
    vigente (sin paginar), en el mismo orden que se ve en pantalla. Lo
    usa el endpoint de exportación; el endpoint JSON del dashboard pagina
    esta misma query base (ctx.base_actual) por separado para el scroll
    continuo, sin traer miles de filas a Python en cada bloque."""
    filas = ctx.base_actual.order_by(
        Importacion.fecha.desc(), Importacion.importacionplaguicidaid.desc()
    ).all()
    return sin_nan(pd.DataFrame(
        [
            (
                f.fecha, f.recibointerno, f.aplicacion, f.importador, f.producto,
                f.ingrediente_act, f.exportador, f.origen, f.institucion,
            )
            for f in filas
        ],
        columns=[
            "fecha", "recibointerno", "aplicacion", "importador", "producto",
            "ingrediente_act", "exportador", "origen", "institucion",
        ],
    ))


def obtener_dashboard_plaguicidas(
    db: Session,
    anio: int | None,
    mes: int | None,
    origen: list[str] | None,
    ingrediente_act: list[str] | None,
    aplicacion: list[str] | None,
    producto: list[str] | None,
    pagina: int,
    tamano_pagina: int,
) -> DashboardPlaguicidasResponse:
    ctx = construir_contexto_plaguicidas(db, anio, mes, origen, ingrediente_act, aplicacion, producto)

    kpis = _kpis_plaguicidas(ctx)

    comparacion_acumulada_mensual = [
        ComparacionAcumuladaMensual(**fila) for fila in df_acumulado_mensual(ctx).to_dict("records")
    ]
    comparacion_mensual = [
        ComparacionMensual(**fila) for fila in df_comparativo_mensual(ctx).to_dict("records")
    ]
    comparativo_acumulado_multianual = series_multianual_desde_df(df_acumulado_multianual(ctx))
    diversificacion_aplicacion = [RankingItem(**fila) for fila in df_por_aplicacion(ctx).to_dict("records")]
    top_ingredientes = [RankingItem(**fila) for fila in df_top_moleculas(ctx).to_dict("records")]
    top_importadores = [RankingItem(**fila) for fila in df_top_importadores(ctx).to_dict("records")]
    top_origenes = [ResumenItem(**fila) for fila in df_top_paises(ctx).to_dict("records")]
    tabla_resumen_importadores = [
        ResumenItem(**fila) for fila in df_resumen_importadores(ctx).to_dict("records")
    ]
    tabla_nombres_comerciales = [
        NombreComercialItem(**fila) for fila in df_nombres_comerciales(ctx).to_dict("records")
    ]
    tabla_grupos = [GrupoItem(**fila) for fila in df_grupo(ctx).to_dict("records")]

    # --- Tabla detalle paginada (SQL-side OFFSET/LIMIT, independiente de
    # df_detalle: ver nota en esa función) ---
    total_detalle = ctx.base_actual.with_entities(func.count(Importacion.importacionplaguicidaid)).scalar() or 0
    filas_detalle = (
        ctx.base_actual.order_by(Importacion.fecha.desc(), Importacion.importacionplaguicidaid.desc())
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )
    detalle = PaginaDetallePlaguicidas(
        total=total_detalle,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
        filas=[
            DetalleTransaccionPlaguicida(
                fecha=fila.fecha,
                recibointerno=fila.recibointerno,
                aplicacion=fila.aplicacion,
                importador=fila.importador,
                producto=fila.producto,
                ingrediente_act=fila.ingrediente_act,
                exportador=fila.exportador,
                origen=fila.origen,
                institucion=fila.institucion,
            )
            for fila in filas_detalle
        ],
    )

    return DashboardPlaguicidasResponse(
        anio_actual=ctx.anio_actual,
        anio_anterior=ctx.anio_anterior,
        mes_seleccionado=ctx.mes_seleccionado,
        mes_maximo=ctx.mes_maximo,
        kpis=kpis,
        comparacion_acumulada_mensual=comparacion_acumulada_mensual,
        comparacion_mensual=comparacion_mensual,
        comparativo_acumulado_multianual=comparativo_acumulado_multianual,
        diversificacion_aplicacion=diversificacion_aplicacion,
        top_ingredientes=top_ingredientes,
        top_importadores=top_importadores,
        top_origenes=top_origenes,
        tabla_resumen_importadores=tabla_resumen_importadores,
        tabla_nombres_comerciales=tabla_nombres_comerciales,
        tabla_grupos=tabla_grupos,
        detalle=detalle,
    )

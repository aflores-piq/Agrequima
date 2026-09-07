"""Agregaciones del dashboard de nutrientes, calculadas en SQL/SQLAlchemy
sobre dbo.Nutrientes (no en el frontend).

Cada bloque (gráfico o tabla) se calcula en una función `df_*` que
devuelve un DataFrame de pandas — es la única fuente de verdad para ese
bloque, reutilizada tanto por `obtener_dashboard_nutrientes` (JSON para
la pantalla) como por `services/export.py` (descarga en Excel), así lo
exportado es siempre idéntico a lo que se ve en pantalla.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy import and_, extract, func, or_
from sqlalchemy.orm import Query, Session, aliased

from app.models.nutriente import Nutriente
from app.schemas.dashboard import (
    ComparacionAcumuladaMensual,
    ComparacionMensual,
    DashboardNutrientesResponse,
    DetalleLicenciaNutriente,
    FormulaComponenteItem,
    KpisNutrientes,
    OpcionesFiltroNutrientes,
    PaginaDetalleNutrientes,
    RankingItem,
    ResumenItem,
)
from app.services.clasificacion import normalizar_aduana
from app.services.df_utils import series_multianual_desde_df, sin_nan

_TOP_N_FORMULAS = 20
_TOP_N_ADUANAS = 12
_TOP_N_PAISES = 20
_TABLA_RESUMEN_MAX = 50

# "PLAGUICIDA" es un registro que no pertenece a esta tabla (1 fila) —
# se excluye de TODO el dashboard (KPIs y los 3 rankings). Tipo="." ya
# NO necesita filtro: el cliente confirmó que significa "Licencias", así
# que se corrige en el origen (ver _mapear_tipo_nutriente en
# etl_nutrientes.py, más el backfill de las filas históricas) en vez de
# ocultarse/reinterpretarse acá.
_TIPOS_INVALIDOS = ["PLAGUICIDA"]

# Columnas que identifican una fila real: dos filas iguales en las 6 son
# la MISMA transacción capturada dos veces, no dos transacciones
# distintas (39 grupos duplicados exactos auditados contra la base).
_COLUMNAS_IDENTIDAD_FILA = (
    Nutriente.No_Licencia,
    Nutriente.No_Registro,
    Nutriente.FechaEmision,
    Nutriente.EmpresaImportadora,
    Nutriente.NombreComercial,
    Nutriente.CIF_dolares,
)


def _filtro_no_duplicado_exacto(db: Session, query: Query) -> Query:
    """Excluye filas EXTRA dentro de cada grupo de duplicados exactos —
    se conserva el nutrienteid más bajo de cada grupo, se excluyen los
    demás. No filtra por Tipo (eso se aplica aparte en `_base`).

    Reescrito con NOT EXISTS correlacionado en vez de
    NOT IN (SELECT ... ROW_NUMBER() OVER toda la tabla): ese patrón
    generaba un plan de ejecución muy costoso en SQL Server (~30s y
    ~900k lecturas lógicas tras la recarga masiva de 2026-08-28) — un
    NOT EXISTS por fila es sargable y usa los índices normalmente. Los
    IDs excluidos son exactamente los mismos (verificado antes/después
    del cambio); las comparaciones son NULL-safe (a = b OR ambos NULL)
    para reproducir el mismo agrupamiento que hacía PARTITION BY, que
    trata NULL = NULL como iguales dentro de una partición."""
    otra = aliased(Nutriente)
    condiciones_igualdad = [
        or_(getattr(otra, col.key) == col, and_(getattr(otra, col.key).is_(None), col.is_(None)))
        for col in _COLUMNAS_IDENTIDAD_FILA
    ]
    existe_duplicado_con_id_mas_bajo = (
        db.query(otra.nutrienteid)
        .filter(otra.nutrienteid < Nutriente.nutrienteid)
        .filter(*condiciones_igualdad)
        .exists()
    )
    return query.filter(~existe_duplicado_con_id_mas_bajo)

# Ver comentario equivalente en dashboard_plaguicidas.py: valor especial
# del filtro de "Nombre comercial" (que filtra por
# Nutriente.ProductoAgrupado, ver _aplicar_filtros) para las filas sin
# agrupador (ProductoAgrupado IS NULL).
SIN_AGRUPADOR = "Sin agrupador"


def _filtro_producto_agrupado(query, valores: list[str] | None):
    """Ver comentario equivalente en dashboard_plaguicidas.py:
    _filtro_grupo — SIN_AGRUPADOR se combina con el resto en vez de ser
    exclusivo."""
    if not valores:
        return query
    incluye_sin_agrupador = SIN_AGRUPADOR in valores
    valores_reales = [v for v in valores if v != SIN_AGRUPADOR]
    condiciones = []
    if valores_reales:
        condiciones.append(Nutriente.ProductoAgrupado.in_(valores_reales))
    if incluye_sin_agrupador:
        condiciones.append(Nutriente.ProductoAgrupado.is_(None))
    return query.filter(or_(*condiciones)) if condiciones else query


def _aplicar_filtros(
    query,
    nombre_comercial: list[str] | None,
    nombre_comercial_raw: list[str] | None,
    origen: list[str] | None,
    componente: list[str] | None,
):
    query = _filtro_producto_agrupado(query, nombre_comercial)
    # "Nombre comercial" (crudo): filtra directo sobre NombreComercial tal
    # como viene del archivo original, sin pasar por el catálogo de
    # agrupación — independiente del filtro de arriba (ProductoAgrupado).
    if nombre_comercial_raw:
        query = query.filter(Nutriente.NombreComercial.in_(nombre_comercial_raw))
    if origen:
        query = query.filter(Nutriente.PaisOrigen.in_(origen))
    if componente:
        query = query.filter(Nutriente.Componentes.in_(componente))
    return query


def _anio_default(db: Session) -> int:
    return db.query(func.max(Nutriente.anio)).scalar() or 0


def obtener_opciones_filtro_nutrientes(db: Session) -> OpcionesFiltroNutrientes:
    """Valores reales y distintos para poblar los dropdowns/autocompletado
    de la fila de filtros (en vez de cuadros de texto en blanco). No
    ofrece opciones que solo existen en filas Excluido=1 -- si se
    seleccionaran, el dashboard nunca mostraría resultados para ellas."""
    no_excluido = db.query(Nutriente).filter(Nutriente.Excluido == False)
    anios = sorted(
        (a for (a,) in no_excluido.with_entities(Nutriente.anio).distinct().all() if a is not None),
        reverse=True,
    )
    paises_origen = sorted(
        {p for (p,) in no_excluido.with_entities(Nutriente.PaisOrigen).distinct().all() if p}
    )
    componentes = sorted(
        {c for (c,) in no_excluido.with_entities(Nutriente.Componentes).distinct().all() if c}
    )
    grupos_presentes = no_excluido.with_entities(Nutriente.ProductoAgrupado).distinct().all()
    nombres_comerciales = sorted({g for (g,) in grupos_presentes if g})
    if any(g is None for (g,) in grupos_presentes):
        nombres_comerciales.append(SIN_AGRUPADOR)
    nombres_comerciales_raw = sorted(
        {n for (n,) in no_excluido.with_entities(Nutriente.NombreComercial).distinct().all() if n}
    )
    return OpcionesFiltroNutrientes(
        anios=anios,
        paises_origen=paises_origen,
        componentes=componentes,
        nombres_comerciales=nombres_comerciales,
        nombres_comerciales_raw=nombres_comerciales_raw,
    )


def _mes_maximo_disponible(db: Session, anio: int) -> int:
    """Mes por defecto del selector 'hasta el mes': el mes más reciente
    con datos EN dbo.Nutrientes para el año seleccionado (independiente
    de plaguicidas, que vive en otra tabla)."""
    resultado = (
        db.query(func.max(extract("month", Nutriente.FechaEmision)))
        .filter(Nutriente.anio == anio)
        .scalar()
    )
    return int(resultado) if resultado else 12


@dataclass
class ContextoNutrientes:
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


def construir_contexto_nutrientes(
    db: Session,
    anio: int | None,
    mes: int | None,
    nombre_comercial: list[str] | None,
    origen: list[str] | None,
    componente: list[str] | None,
    nombre_comercial_raw: list[str] | None,
) -> ContextoNutrientes:
    anio_actual = anio or _anio_default(db)
    anio_anterior = anio_actual - 1
    mes_maximo = _mes_maximo_disponible(db, anio_actual)
    mes_seleccionado = mes or mes_maximo

    mes_expr = extract("month", Nutriente.FechaEmision)

    def _base(anio_query: int):
        query = _filtro_no_duplicado_exacto(
            db,
            db.query(Nutriente)
            .filter(Nutriente.anio == anio_query)
            .filter(Nutriente.Tipo.notin_(_TIPOS_INVALIDOS))
            # Productos marcados Excluido=1 en el catálogo (ver
            # CatalogoAgrupadorNutrientes.Excluido): no corresponden a
            # Nutrientes según el cliente. La fila cruda sigue en la
            # base -- solo se oculta de dashboards/exports.
            .filter(Nutriente.Excluido == False),
        )
        query = _aplicar_filtros(
            query, nombre_comercial, nombre_comercial_raw, origen, componente,
        )
        # El selector "hasta el mes" acota TODO el dashboard a
        # Enero..mes_seleccionado, en ambos años que se comparan.
        return query.filter(mes_expr <= mes_seleccionado)

    base_actual = _base(anio_actual)
    base_anterior = _base(anio_anterior)
    cif_total = float(base_actual.with_entities(func.sum(Nutriente.CIF_dolares)).scalar() or 0) or 1

    return ContextoNutrientes(
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


def _kpis_nutrientes(ctx: ContextoNutrientes) -> KpisNutrientes:
    fila = ctx.base_actual.with_entities(
        func.sum(Nutriente.CIF_dolares),
        func.sum(Nutriente.CIF_Q),
        func.count(Nutriente.nutrienteid),
        func.count(Nutriente.EmpresaImportadora.distinct()),
    ).one()
    return KpisNutrientes(
        cif_total_usd=float(fila[0] or 0),
        cif_total_q=float(fila[1] or 0),
        registros=int(fila[2] or 0),
        empresas=int(fila[3] or 0),
    )


def _totales_por_mes(query: Query) -> dict[int, float]:
    mes_expr = extract("month", Nutriente.FechaEmision)
    return dict(query.with_entities(mes_expr, func.sum(Nutriente.CIF_dolares)).group_by(mes_expr).all())


def df_acumulado_mensual(ctx: ContextoNutrientes) -> pd.DataFrame:
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


def df_comparativo_mensual(ctx: ContextoNutrientes) -> pd.DataFrame:
    """Gráfico 2: comparación mensual de CIF (actual vs. anterior)."""
    totales_actual = _totales_por_mes(ctx.base_actual)
    totales_anterior = _totales_por_mes(ctx.base_anterior)
    filas = [
        (m, float(totales_actual.get(m) or 0), float(totales_anterior.get(m) or 0))
        for m in range(1, ctx.mes_seleccionado + 1)
    ]
    return pd.DataFrame(filas, columns=["mes", "cif_usd_actual", "cif_usd_anterior"])


_VENTANA_MULTIANUAL = 5


def df_acumulado_multianual(ctx: ContextoNutrientes) -> pd.DataFrame:
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


def df_acumulado_multianual_ancho(ctx: ContextoNutrientes) -> pd.DataFrame:
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


def df_top_formulas(ctx: ContextoNutrientes) -> pd.DataFrame:
    """Gráfico 3: top fórmulas químicas (ProductoAgrupado) por CIF."""
    filas = (
        ctx.base_actual.with_entities(Nutriente.ProductoAgrupado, func.sum(Nutriente.CIF_dolares))
        .filter(Nutriente.ProductoAgrupado.isnot(None))
        .group_by(Nutriente.ProductoAgrupado)
        .order_by(func.sum(Nutriente.CIF_dolares).desc())
        .limit(_TOP_N_FORMULAS)
        .all()
    )
    return pd.DataFrame(
        [(f[0], float(f[1] or 0)) for f in filas], columns=["etiqueta", "cif_usd"]
    )


def df_top_aduanas(ctx: ContextoNutrientes) -> pd.DataFrame:
    """Gráfico 4: top aduanas de ingreso.

    AduanadeIngreso trae variantes del mismo lugar (mayúsculas, con/sin
    acentos, con/sin el prefijo "Puerto"): se normaliza antes de agrupar."""
    cif_por_aduana: dict[str, float] = defaultdict(float)
    for aduana_raw, cif_usd in (
        ctx.base_actual.with_entities(Nutriente.AduanadeIngreso, func.sum(Nutriente.CIF_dolares))
        .filter(Nutriente.AduanadeIngreso.isnot(None))
        .group_by(Nutriente.AduanadeIngreso)
        .all()
    ):
        aduana = normalizar_aduana(aduana_raw)
        cif_por_aduana[aduana] += float(cif_usd or 0)

    filas = [
        (aduana, cif_por_aduana[aduana])
        for aduana in sorted(cif_por_aduana, key=lambda a: -cif_por_aduana[a])[:_TOP_N_ADUANAS]
    ]
    return pd.DataFrame(filas, columns=["etiqueta", "cif_usd"])


def df_top_paises_origen(ctx: ContextoNutrientes) -> pd.DataFrame:
    """Gráfico 5: top países de origen (tabla numerada; no forma parte de
    los elementos exportables pedidos, pero se deja disponible)."""
    filas = (
        ctx.base_actual.with_entities(
            Nutriente.PaisOrigen,
            func.count(Nutriente.nutrienteid),
            func.sum(Nutriente.CIF_dolares),
        )
        .filter(Nutriente.PaisOrigen.isnot(None))
        .group_by(Nutriente.PaisOrigen)
        .order_by(func.sum(Nutriente.CIF_dolares).desc())
        .limit(_TOP_N_PAISES)
        .all()
    )
    return pd.DataFrame(
        [
            (f[0], int(f[1]), float(f[2] or 0), round(float(f[2] or 0) / ctx.cif_total * 100, 2))
            for f in filas
        ],
        columns=["etiqueta", "transacciones", "cif_usd", "porcentaje_del_total"],
    )


def df_formulas_componentes(ctx: ContextoNutrientes) -> pd.DataFrame:
    """Tabla: fórmulas/componentes, ordenado por CIF USD (spec de Power BI:
    "FÓRMULAS/COMPONENTES - ORDENADO POR CIF USD", columnas Proporción,
    Concentración principal, Cantidad, Unidad, CIF USD, CIF Q).

    Mismo patrón que df_grupo en dashboard_plaguicidas.py: SQL Server no
    tiene MODE() nativo, se trae (Componentes, Concentraciones, UMedida)
    ya sumado por combinación, y la "concentración principal"/"unidad" de
    cada Componentes se resuelve en Python como la combinación con más
    transacciones dentro de ese Componentes.

    Nota: agrupa por `Componentes` (fórmula química, ej. "N", "K2O, N,
    P2O5"), NO por `ProductoAgrupado` (nombre comercial agrupado, ej.
    "Urea", "DAP") — verificado contra la captura real de Power BI, los
    valores de esa columna vienen de Componentes."""
    filas_detalle = (
        ctx.base_actual.with_entities(
            Nutriente.Componentes,
            Nutriente.Concentraciones,
            Nutriente.UMedida,
            func.count(Nutriente.nutrienteid),
            func.sum(Nutriente.Cantidad),
            func.sum(Nutriente.CIF_dolares),
            func.sum(Nutriente.CIF_Q),
        )
        .filter(Nutriente.Componentes.isnot(None))
        .group_by(Nutriente.Componentes, Nutriente.Concentraciones, Nutriente.UMedida)
        .all()
    )
    agregados: dict[str, dict[str, Any]] = {}
    for componente, concentracion, unidad, transacciones, cantidad, cif_usd_fila, cif_q_fila in filas_detalle:
        acc = agregados.setdefault(
            componente,
            {"cantidad": 0.0, "cif_usd": 0.0, "cif_q": 0.0, "concentraciones": Counter(), "unidades": Counter()},
        )
        acc["cantidad"] += float(cantidad or 0)
        acc["cif_usd"] += float(cif_usd_fila or 0)
        acc["cif_q"] += float(cif_q_fila or 0)
        acc["concentraciones"][concentracion] += transacciones
        acc["unidades"][unidad] += transacciones

    filas = [
        (
            componente,
            round(datos["cif_usd"] / ctx.cif_total * 100, 2),
            datos["concentraciones"].most_common(1)[0][0] if datos["concentraciones"] else None,
            datos["cantidad"],
            datos["unidades"].most_common(1)[0][0] if datos["unidades"] else None,
            datos["cif_usd"],
            datos["cif_q"],
        )
        for componente, datos in sorted(agregados.items(), key=lambda kv: -kv[1]["cif_usd"])[:_TABLA_RESUMEN_MAX]
    ]
    return sin_nan(pd.DataFrame(
        filas,
        columns=[
            "componente", "porcentaje_del_total", "concentracion_principal",
            "cantidad", "unidad", "cif_usd", "cif_q",
        ],
    ))


def df_detalle(ctx: ContextoNutrientes) -> pd.DataFrame:
    """Detalle de licencias — TODAS las filas que cumplen el filtro
    vigente (sin paginar), en el mismo orden que se ve en pantalla. Lo
    usa el endpoint de exportación; el endpoint JSON del dashboard pagina
    esta misma query base (ctx.base_actual) por separado para el scroll
    continuo, sin traer miles de filas a Python en cada bloque."""
    filas = ctx.base_actual.order_by(
        Nutriente.FechaEmision.desc(), Nutriente.nutrienteid.desc()
    ).all()
    return sin_nan(pd.DataFrame(
        [
            (
                f.AduanadeIngreso, f.No_Licencia, f.No_Registro, f.NombreComercial,
                f.EmpresaImportadora, f.FechaEmision.isoformat() if f.FechaEmision else None, f.UMedida,
            )
            for f in filas
        ],
        columns=["aduana", "no_licencia", "no_registro", "nombre_comercial", "empresa_importadora", "fecha_emision", "unidad"],
    ))


def obtener_dashboard_nutrientes(
    db: Session,
    anio: int | None,
    mes: int | None,
    nombre_comercial: list[str] | None,
    origen: list[str] | None,
    componente: list[str] | None,
    pagina: int,
    tamano_pagina: int,
    nombre_comercial_raw: list[str] | None = None,
) -> DashboardNutrientesResponse:
    ctx = construir_contexto_nutrientes(
        db, anio, mes, nombre_comercial, origen, componente, nombre_comercial_raw
    )

    kpis = _kpis_nutrientes(ctx)

    comparacion_acumulada_mensual = [
        ComparacionAcumuladaMensual(**fila) for fila in df_acumulado_mensual(ctx).to_dict("records")
    ]
    comparacion_mensual = [
        ComparacionMensual(**fila) for fila in df_comparativo_mensual(ctx).to_dict("records")
    ]
    comparativo_acumulado_multianual = series_multianual_desde_df(df_acumulado_multianual(ctx))
    top_formulas = [RankingItem(**fila) for fila in df_top_formulas(ctx).to_dict("records")]
    top_aduanas = [RankingItem(**fila) for fila in df_top_aduanas(ctx).to_dict("records")]
    top_paises_origen = [ResumenItem(**fila) for fila in df_top_paises_origen(ctx).to_dict("records")]
    tabla_formulas_componentes = [
        FormulaComponenteItem(**fila) for fila in df_formulas_componentes(ctx).to_dict("records")
    ]

    # --- Tabla detalle paginada (SQL-side OFFSET/LIMIT, independiente de
    # df_detalle: ver nota en esa función) ---
    total_detalle = ctx.base_actual.with_entities(func.count(Nutriente.nutrienteid)).scalar() or 0
    filas_detalle = (
        ctx.base_actual.order_by(Nutriente.FechaEmision.desc(), Nutriente.nutrienteid.desc())
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )
    detalle = PaginaDetalleNutrientes(
        total=total_detalle,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
        filas=[
            DetalleLicenciaNutriente(
                aduana=fila.AduanadeIngreso,
                no_licencia=fila.No_Licencia,
                no_registro=fila.No_Registro,
                nombre_comercial=fila.NombreComercial,
                empresa_importadora=fila.EmpresaImportadora,
                fecha_emision=fila.FechaEmision.isoformat() if fila.FechaEmision else None,
                unidad=fila.UMedida,
            )
            for fila in filas_detalle
        ],
    )

    return DashboardNutrientesResponse(
        anio_actual=ctx.anio_actual,
        anio_anterior=ctx.anio_anterior,
        mes_seleccionado=ctx.mes_seleccionado,
        mes_maximo=ctx.mes_maximo,
        kpis=kpis,
        comparacion_acumulada_mensual=comparacion_acumulada_mensual,
        comparacion_mensual=comparacion_mensual,
        comparativo_acumulado_multianual=comparativo_acumulado_multianual,
        top_formulas=top_formulas,
        top_paises_origen=top_paises_origen,
        top_aduanas=top_aduanas,
        tabla_formulas_componentes=tabla_formulas_componentes,
        detalle=detalle,
    )

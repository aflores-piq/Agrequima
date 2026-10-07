"""Cálculos del grupo "Otros informes financieros" (sub-sección hermana
de "Estados financieros" en el Sidebar). Por ahora solo Cuotas Asociados
-- las otras 4 páginas (Conciliación Bancaria, Flujo de Caja, Ejecución
gastos por mes/acumulado) se agregan acá mismo a medida que se
implementan, mismo patrón que dashboard_financiero.py: SQL crudo vía
text(), sin ORM, sin clase de contexto compartida.

--- Cuotas Asociados -----------------------------------------------------

Fuentes reales:
    dbo.AsociadosCuota(emp_nit, Sal_Ano, cod_n5, nom_n5, grupo,
        nombre_mostrar, cuota) -- una fila por asociado/año, "grupo" es
        el Tipo (A/B/C) tal cual lo carga CONTACC (hay un cuarto valor
        "Q" en datos históricos de 2023 que no corresponde a ningún tipo
        real -- se excluye).
    dbo.BalanceGeneral(cod_n5, Sal_Ano, Creditos) -- incluida acá porque
        cod_n5 es una clave real compartida con AsociadosCuota (cada
        asociado tiene su propia cuenta contable 110201xxx), NO por
        nombre (nom_n5 tiene inconsistencias de espacios/mayúsculas que
        cod_n5 no tiene -- confirmado que ambos joins dan el mismo total).

Semántica CONFIRMADA contra los datos reales (Total/Cancelado/Por cobrar
del año 2026 cuadran exacto contra la captura de referencia: Q756,000 /
Q660,000 / Q96,000):
    CuotaTotal = SUM(cuota) de AsociadosCuota para el año filtrado -- NO
        varía por mes (la cuota es un monto fijo anual por asociado).
    Cancelado = SUM(Creditos) de BalanceGeneral, ACUMULADO hasta el mes
        filtrado (Sal_Mes <= mes), de las cuentas (cod_n5) que aparecen
        en AsociadosCuota para ese año.
        CORRECCIÓN a una nota anterior de este docstring: se había
        anotado que "filtrar por Sal_Mes daba 634,000 en vez de 660,000
        exacto" y se concluyó (mal) que el filtro de mes "no aplica" a
        este concepto. Investigado de nuevo con una consulta directa: el
        acumulado por mes es monótono creciente y CORRECTO (12,000 en
        enero -> 634,000 en julio -> 660,000 desde agosto en adelante,
        que es el último mes con pagos cargados a la fecha) -- 634,000
        es simplemente el acumulado REAL hasta julio, no un error.
    Saldo (Por cobrar) = CuotaTotal - Cancelado (del mismo corte de mes).

Selector de período (CORREGIDO): el .pbix real define MiCalendario =
CALENDAR(DATE(2023,1,1),
EOMONTH(MAX(vw_piq_balance_general[Fecha]), 0)) -- el filtro de mes llega
solo hasta el último mes con datos de BalanceGeneral (hoy Septiembre
2026), igual que las demás páginas de "Otros informes financieros". Antes
`periodos_disponibles` traía solo años (de AsociadosCuota) y el mes
"siempre disponible 1-12" -- eso permitía elegir Diciembre 2026 aunque no
exista ese dato todavía. Ahora usa pares año+mes reales de
dbo.BalanceGeneral (mismo criterio y misma función de resolución de
default, `_anio_mes_default_gastos`, que Ejecución de Gastos/Conciliación/
Flujo), y por default apunta al último período real en vez de a
diciembre -- el cálculo de Cancelado/Saldo en sí NO cambia (mismo SQL,
mismo filtro Sal_Mes <= mes), solo cambia qué meses son seleccionables.
"""

import re
import unicodedata
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.dashboard_otros_informes import (
    BancoConciliacion,
    BarraFlujoCaja,
    ComparativoEjecutadoResponse,
    ConciliacionBancariaResponse,
    CuotasAsociadosResponse,
    EjecucionGastosResponse,
    EjecucionVsPresupuestoResponse,
    FilaComparativoEjecutado,
    FilaConciliacionBanco,
    FilaCuotaAsociado,
    FilaFlujoCaja,
    FilaGastoCategoria,
    FilaPresupuesto,
    FlujoCajaResponse,
    KpisCuotasAsociados,
    PeriodoDisponibleGastos,
    TarjetaResumenGasto,
    TipoCuotaAsociados,
)
from app.services.agrupador_cuentas import cargar_mapas_agrupador, grupo_de_cuenta
from app.services.catalogo_bancos import (
    BancoResuelto,
    ResolutorBancos,
    cargar_catalogo_bancos,
    limpiar_texto,
    ordenar_conciliacion,
    ordenar_flujo,
)

_TIPOS_CUOTA = ("A", "B", "C")


def _num(valor) -> float:
    return float(valor) if valor is not None else 0.0


def _periodos_disponibles_cuotas(db: Session) -> list[PeriodoDisponibleGastos]:
    # Misma fuente que el filtro de mes real del .pbix (MiCalendario, ver
    # docstring del módulo): dbo.BalanceGeneral es continuo desde 2023-01
    # sin huecos (confirmado con SELECT DISTINCT), así que esto reproduce
    # exactamente CALENDAR(DATE(2023,1,1), EOMONTH(MAX(Fecha), 0)) sin
    # necesidad de generar un calendario aparte.
    filas = db.execute(
        text("SELECT DISTINCT Sal_Ano, Sal_Mes FROM dbo.BalanceGeneral ORDER BY Sal_Ano, Sal_Mes")
    ).all()
    return [PeriodoDisponibleGastos(anio=int(a), mes=int(m)) for a, m in filas if a is not None and m is not None]


def obtener_cuotas_asociados(db: Session, anio: int | None, mes: int | None = None) -> CuotasAsociadosResponse:
    periodos = _periodos_disponibles_cuotas(db)
    # Misma función de resolución de default que Ejecución de Gastos/
    # Conciliación/Flujo: si falta año y/o mes, usa el último período real
    # disponible (antes: año más reciente de AsociadosCuota + mes=12 fijo,
    # lo que permitía llegar hasta diciembre aunque no hubiera datos).
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)

    filas = (
        db.execute(
            text(
                """
                SELECT
                    ac.grupo AS tipo,
                    ac.nombre_mostrar AS nombre,
                    ac.cuota AS cuota,
                    COALESCE(bg.creditos, 0) AS cancelado
                FROM dbo.AsociadosCuota ac
                LEFT JOIN (
                    SELECT cod_n5, SUM(Creditos) AS creditos
                    FROM dbo.BalanceGeneral
                    WHERE Sal_Ano = :anio AND Sal_Mes <= :mes
                    GROUP BY cod_n5
                ) bg ON bg.cod_n5 = ac.cod_n5
                WHERE ac.Sal_Ano = :anio AND ac.grupo IN ('A', 'B', 'C')
                ORDER BY ac.grupo, ac.nombre_mostrar
                """
            ),
            {"anio": anio_resuelto, "mes": mes_resuelto},
        )
        .mappings()
        .all()
    )

    por_tipo: dict[str, list[FilaCuotaAsociado]] = {t: [] for t in _TIPOS_CUOTA}
    for f in filas:
        cuota, cancelado = _num(f["cuota"]), _num(f["cancelado"])
        por_tipo[f["tipo"]].append(
            FilaCuotaAsociado(
                nombre=(f["nombre"] or "").strip(),
                cuota=cuota,
                cancelado=cancelado,
                saldo=cuota - cancelado,
            )
        )

    tipos = [
        TipoCuotaAsociados(
            tipo=t,
            filas=por_tipo[t],
            total_cuota=sum(r.cuota for r in por_tipo[t]),
            total_cancelado=sum(r.cancelado for r in por_tipo[t]),
            total_saldo=sum(r.saldo for r in por_tipo[t]),
        )
        for t in _TIPOS_CUOTA
    ]

    total = sum(t.total_cuota for t in tipos)
    cancelado_total = sum(t.total_cancelado for t in tipos)
    kpis = KpisCuotasAsociados(total=total, cancelado=cancelado_total, por_cobrar=total - cancelado_total)

    return CuotasAsociadosResponse(
        anio=anio_resuelto, mes=mes_resuelto, periodos_disponibles=periodos, kpis=kpis, tipos=tipos
    )


# --- Ejecución de gastos (por mes / acumulado) ---------------------------
#
# CORREGIDO -- una versión anterior de esta sección agrupaba por centro
# de costo individual (22 filas). Se descartó por completo: verificado
# con la fórmula DAX real del .pbix original Y con las capturas de
# referencia (ambas coinciden entre sí) que la tabla agrupa por
# CATEGORÍA DE GASTO ("GroupEgresos" en el .pbix), no por centro.
#
# "GroupEgresos" no es una columna propia -- es exactamente
# dbo.CatalogoAgrupadorCuentas con TipoAgrupador='Egresos' (la MISMA
# tabla/mecanismo que ya usa la columna "Grupo" de Ingresos/Egresos en
# Estados Financieros, ver agrupador_cuentas.py: cargar_mapas_agrupador +
# grupo_de_cuenta). Confirmado sin huecos: cada Cta_Codigo que aparece en
# BalanceSaldos para Administración/Operación matchea alguna categoría
# (0 filas "Sin clasificar" en la verificación contra agosto 2026).
#
# Fuentes reales:
#     dbo.BalanceSaldos(Cta_Codigo, Sal_Ano, Sal_Mes, Debitos, Creditos,
#         Cod_Centro) -- Ejecutado = SUM(Debitos) - SUM(Creditos) (NETO,
#         no solo Debitos -- a diferencia de Estados Financieros).
#     dbo.Presupuestos(par_ano, par_mes, cta_codigo, pre_presupuesto,
#         cod_centro).
#
# Administración = Cod_Centro IN ('AD-01', 'AD-02') -- OJO: AD-03 NO
#     entra acá (a diferencia de la versión anterior, que agrupaba TODO
#     lo que empezaba con "AD-").
# Operación = el resto, pero con un filtro explícito, NO "todo lo que no
#     sea Administración": Cod_Centro que empieza con 'O', o que empieza
#     con 'A' y no es AD-01/AD-02 (esto incluye AD-03). Cod_Centro = '0'
#     ("NO APLICA") queda EXCLUIDO de los dos grupos a propósito -- tiene
#     un neto grande (-Q917,109.82 en agosto 2026 nada más) que si se
#     incluyera en Operación arruina el total; el .pbix simplemente no lo
#     cuenta en ningún lado.
# Presupuesto Operativo excluye además cta_codigo='410104001' (una fila
#     de ingresos suelta dentro de la tabla de Presupuestos).
#
# Verificado EXACTO contra la captura de referencia real de agosto 2026
# (mensual Y acumulado a agosto, dos verificaciones independientes):
#   Mensual:    Administración Q143,505 (88.1%, ppto Q162,825, dif -Q19,320)
#               Operación      Q710,318 (96.7%, ppto Q734,909, dif -Q24,590)
#               Consolidado    Q853,823 (95.1%, ppto Q897,734, dif -Q43,911)
#   Acumulado:  Administración Q1,328,560 (88.8%, ppto Q1,496,204)
#               Operación      Q5,247,423 (75.6%, ppto Q6,943,846)
#               Consolidado    Q6,575,984 (77.9%, ppto Q8,440,050)
#   Categoría "Sueldos Bonificaciones y Prestaciones de Ley" dentro de
#   Administración, agosto 2026: Q88,180.97 = 61.4% del peso -- exacto.
#
# "Peso %" (columnas 2 y 4 de la tabla) = participación de esa categoría
# sobre el TOTAL EJECUTADO de su propio grupo (Administración u
# Operación por separado, no sobre el consolidado ni sobre el
# presupuesto) -- fórmula DAX real: DIVIDE(valor_categoria,
# CALCULATE(total, REMOVEFILTERS(GroupEgresos)), 0).

_FILTRO_ADMIN_SQL = "bs.Cod_Centro IN ('AD-01', 'AD-02')"
_FILTRO_OP_SQL = "(LEFT(bs.Cod_Centro, 1) = 'O' OR (LEFT(bs.Cod_Centro, 1) = 'A' AND bs.Cod_Centro NOT IN ('AD-01', 'AD-02')))"


def _periodos_disponibles_gastos(db: Session) -> list[PeriodoDisponibleGastos]:
    filas = db.execute(
        text("SELECT DISTINCT Sal_Ano, Sal_Mes FROM dbo.BalanceSaldos ORDER BY Sal_Ano, Sal_Mes")
    ).all()
    return [PeriodoDisponibleGastos(anio=int(a), mes=int(m)) for a, m in filas if a is not None and m is not None]


def _anio_mes_default_gastos(
    anio: int | None, mes: int | None, periodos: list[PeriodoDisponibleGastos]
) -> tuple[int, int]:
    if not periodos:
        hoy = date.today()
        return anio or hoy.year, mes or hoy.month
    if anio is not None and mes is not None:
        return anio, mes
    ultimo = periodos[-1]
    return anio or ultimo.anio, mes or ultimo.mes


def _neto_por_categoria(db: Session, anio: int, mes: int, acumulado: bool, filtro_centro_sql: str) -> dict[str, float]:
    condicion_mes = "bs.Sal_Mes <= :mes" if acumulado else "bs.Sal_Mes = :mes"
    filas = db.execute(
        text(
            f"""
            SELECT bs.Cta_Codigo AS codigo, SUM(bs.Debitos) - SUM(bs.Creditos) AS neto
            FROM dbo.BalanceSaldos bs
            WHERE bs.Sal_Ano = :anio AND {condicion_mes} AND {filtro_centro_sql}
            GROUP BY bs.Cta_Codigo
            """
        ),
        {"anio": anio, "mes": mes},
    ).all()

    mapas, _ = cargar_mapas_agrupador(db, "Egresos")
    por_categoria: dict[str, float] = {}
    for codigo, neto in filas:
        categoria = grupo_de_cuenta(mapas, codigo) or "Sin clasificar"
        por_categoria[categoria] = por_categoria.get(categoria, 0.0) + _num(neto)
    return por_categoria


def _presupuesto_grupo(db: Session, anio: int, mes: int, acumulado: bool, es_admin: bool) -> float:
    condicion_mes = "p.par_mes <= :mes" if acumulado else "p.par_mes = :mes"
    if es_admin:
        filtro = "p.cod_centro IN ('AD-01', 'AD-02')"
    else:
        filtro = "p.cod_centro NOT IN ('AD-01', 'AD-02') AND p.cta_codigo <> '410104001'"
    valor = db.execute(
        text(f"SELECT SUM(p.pre_presupuesto) FROM dbo.Presupuestos p WHERE p.par_ano = :anio AND {condicion_mes} AND {filtro}"),
        {"anio": anio, "mes": mes},
    ).scalar()
    return _num(valor)


# Los nombres reales de Power BI llevan comas que dbo.CatalogoAgrupadorCuentas.Nombre
# NO tiene -- confirmado con SQL directo contra esa tabla (sin comas en
# el campo). La vista que usa el .pbix (vw_piq_balance_saldos) no existe
# en esta base para comparar directo, así que no se puede saber con
# certeza por qué difieren; se corrige solo el TEXTO de presentación de
# las 3 categorías que el usuario confirmó contra su captura real, sin
# tocar el nombre que se usa como clave de agrupamiento/suma.
_NOMBRES_DISPLAY_EJECUCION_GASTOS = {
    "Literatura y Material para Capacitación Programa Educación": "Literatura y Material para Capacitación, Programa Educación",
    "Viáticos Mantenimiento Incineración Programa CampoLimpio": "Viáticos, Mantenimiento, Incineración Programa CampoLimpio",
    "Sueldos Bonificaciones y Prestaciones de Ley": "Sueldos, Bonificaciones y Prestaciones de Ley",
}


def _nombre_display_ejecucion_gastos(categoria: str) -> str:
    return _NOMBRES_DISPLAY_EJECUCION_GASTOS.get(categoria, categoria)


def _ejecucion_gastos(db: Session, anio: int, mes: int, acumulado: bool) -> EjecucionGastosResponse:
    periodos = _periodos_disponibles_gastos(db)

    por_categoria_admin = _neto_por_categoria(db, anio, mes, acumulado, _FILTRO_ADMIN_SQL)
    por_categoria_op = _neto_por_categoria(db, anio, mes, acumulado, _FILTRO_OP_SQL)

    total_ejecutado_admin = sum(por_categoria_admin.values())
    total_ejecutado_op = sum(por_categoria_op.values())

    # Desempate alfabético SIN distinguir mayúsculas/minúsculas -- Python
    # ordena strings por valor de código (case-sensitive), así que
    # "Gastos Proyectos..." (P mayúscula, 0x50) quedaba ANTES que
    # "Gastos de Apoyo..." (d minúscula, 0x64) aunque alfabéticamente
    # "de" va antes que "Proyectos". El sort final de más abajo es
    # estable, así que este orden inicial es el que decide el empate
    # entre categorías con el mismo valor (ej. Administración=0).
    nombres_categoria = sorted(set(list(por_categoria_admin) + list(por_categoria_op)), key=str.lower)
    categorias = [
        FilaGastoCategoria(
            categoria=_nombre_display_ejecucion_gastos(cat),
            administracion=por_categoria_admin.get(cat, 0.0),
            peso_administracion=(por_categoria_admin.get(cat, 0.0) / total_ejecutado_admin * 100) if total_ejecutado_admin else 0.0,
            operacion=por_categoria_op.get(cat, 0.0),
            peso_operacion=(por_categoria_op.get(cat, 0.0) / total_ejecutado_op * 100) if total_ejecutado_op else 0.0,
            consolidado=por_categoria_admin.get(cat, 0.0) + por_categoria_op.get(cat, 0.0),
        )
        for cat in nombres_categoria
    ]
    # Orden ASCENDENTE -- calcado del pivotTable real de cada página del
    # .pbix: "Centros de Costo" (mensual) ordena por TotalEjecutado
    # (Consolidado); "Centros de Costo acumulado" ordena por
    # EjecutadoAdministrativo_Acumulado (Administración) -- son medidas
    # DAX distintas con OrderBy distinto, confirmado comparando ambos
    # pivotTable.config extraídos del Layout.json. No es el mismo
    # criterio en las 2 páginas, así que no se puede asumir uno para
    # ambas.
    categorias.sort(key=lambda f: (f.administracion if acumulado else f.consolidado))

    fila_total_ejecutado = FilaGastoCategoria(
        categoria="Total ejecutado",
        administracion=total_ejecutado_admin,
        # Guardia contra el bug reportado: si el total de una columna es
        # 0 (esa mitad del reporte no tiene ejecución en el período), su
        # Peso % debe ser 0.0, NO 100.0 -- antes quedaba fijo en 100.0
        # sin importar si la columna tenía datos.
        peso_administracion=100.0 if total_ejecutado_admin else 0.0,
        operacion=total_ejecutado_op,
        peso_operacion=100.0 if total_ejecutado_op else 0.0,
        consolidado=total_ejecutado_admin + total_ejecutado_op,
    )

    presupuesto_admin = _presupuesto_grupo(db, anio, mes, acumulado, es_admin=True)
    presupuesto_op = _presupuesto_grupo(db, anio, mes, acumulado, es_admin=False)

    fila_presupuesto = FilaGastoCategoria(
        categoria="Presupuesto",
        administracion=presupuesto_admin,
        peso_administracion=100.0 if presupuesto_admin else 0.0,
        operacion=presupuesto_op,
        peso_operacion=100.0 if presupuesto_op else 0.0,
        consolidado=presupuesto_admin + presupuesto_op,
    )

    pct_admin = (total_ejecutado_admin / presupuesto_admin * 100) if presupuesto_admin else 0.0
    pct_op = (total_ejecutado_op / presupuesto_op * 100) if presupuesto_op else 0.0
    fila_ejecucion = FilaGastoCategoria(
        categoria="Ejecución",
        administracion=total_ejecutado_admin,
        peso_administracion=pct_admin,
        operacion=total_ejecutado_op,
        peso_operacion=pct_op,
        consolidado=total_ejecutado_admin + total_ejecutado_op,
    )

    presupuesto_total = presupuesto_admin + presupuesto_op
    ejecutado_total = total_ejecutado_admin + total_ejecutado_op
    pct_consolidado = (ejecutado_total / presupuesto_total * 100) if presupuesto_total else 0.0

    tarjetas = [
        TarjetaResumenGasto(
            grupo="Administración",
            presupuesto=presupuesto_admin,
            ejecutado=total_ejecutado_admin,
            porcentaje_ejecucion=pct_admin,
            diferencia=total_ejecutado_admin - presupuesto_admin,
        ),
        TarjetaResumenGasto(
            grupo="Operación",
            presupuesto=presupuesto_op,
            ejecutado=total_ejecutado_op,
            porcentaje_ejecucion=pct_op,
            diferencia=total_ejecutado_op - presupuesto_op,
        ),
        TarjetaResumenGasto(
            grupo="Consolidado",
            presupuesto=presupuesto_total,
            ejecutado=ejecutado_total,
            porcentaje_ejecucion=pct_consolidado,
            diferencia=ejecutado_total - presupuesto_total,
        ),
    ]

    return EjecucionGastosResponse(
        anio=anio,
        mes=mes,
        periodos_disponibles=periodos,
        categorias=categorias,
        fila_total_ejecutado=fila_total_ejecutado,
        fila_presupuesto=fila_presupuesto,
        fila_ejecucion=fila_ejecucion,
        tarjetas=tarjetas,
    )


def obtener_ejecucion_gastos_mensual(db: Session, anio: int | None, mes: int | None) -> EjecucionGastosResponse:
    periodos = _periodos_disponibles_gastos(db)
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)
    return _ejecucion_gastos(db, anio_resuelto, mes_resuelto, acumulado=False)


def obtener_ejecucion_gastos_acumulado(db: Session, anio: int | None, mes: int | None) -> EjecucionGastosResponse:
    periodos = _periodos_disponibles_gastos(db)
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)
    return _ejecucion_gastos(db, anio_resuelto, mes_resuelto, acumulado=True)


# --- Presupuestos: Ejecución vs presupuesto (mensual / acumulado) --------
#
# 3 páginas nuevas del menú "Presupuestos": "Ejecucion vs Presupuesto",
# "Ejecucion vs Presupuesto Acumulado" y "Comparativo ejecutado" --
# fuentes/fórmulas extraídas del DataModel real del .pbix con pbixray
# (medidas DAX de las tablas EjecutadoVsPresupuestado, vw_piq_presupuestos,
# vw_piq_balance_saldos) y del Report/Layout (OrderBy, formato condicional,
# anchos de columna, spec Deneb de "Comparativo ejecutado").
#
# A diferencia de "Ejecución Gastos" (Centros de Costo, separada en
# Administración/Operación), estas 2 primeras páginas muestran una sola
# fila CONSOLIDADA por categoría -- mismas fuentes (dbo.BalanceSaldos +
# dbo.Presupuestos), mismos filtros de Cod_Centro admin/operativo que ya
# existen (_FILTRO_ADMIN_SQL/_FILTRO_OP_SQL, _presupuesto_grupo), solo que
# acá se suman las 2 mitades en vez de mostrarlas por separado.
#
# Verificado con SQL directo contra Agosto 2026 (mensual y acumulado):
# 20 categorías reales (el universo completo de
# dbo.CatalogoAgrupadorCuentas con TipoAgrupador='Egresos', confirmado
# contando esa tabla -- no 22, un conteo manual de la captura original que
# el usuario confirmó que estaba mal). Totales, filas de control y orden
# (ascendente por Gastos en mensual -- Direction=1 en el Layout real;
# descendente por Presupuesto en acumulado -- Direction=2) cuadran exacto.


def _presupuesto_por_categoria_grupo(db: Session, anio: int, mes: int, acumulado: bool, es_admin: bool) -> dict[str, float]:
    condicion_mes = "p.par_mes <= :mes" if acumulado else "p.par_mes = :mes"
    if es_admin:
        filtro = "p.cod_centro IN ('AD-01', 'AD-02')"
    else:
        filtro = "p.cod_centro NOT IN ('AD-01', 'AD-02') AND p.cta_codigo <> '410104001'"
    filas = db.execute(
        text(
            f"""
            SELECT p.cta_codigo AS codigo, SUM(p.pre_presupuesto) AS presupuesto
            FROM dbo.Presupuestos p
            WHERE p.par_ano = :anio AND {condicion_mes} AND {filtro}
            GROUP BY p.cta_codigo
            """
        ),
        {"anio": anio, "mes": mes},
    ).all()
    mapas, _ = cargar_mapas_agrupador(db, "Egresos")
    por_categoria: dict[str, float] = {}
    for codigo, presupuesto in filas:
        categoria = grupo_de_cuenta(mapas, codigo) or "Sin clasificar"
        por_categoria[categoria] = por_categoria.get(categoria, 0.0) + _num(presupuesto)
    return por_categoria


def _presupuesto_por_categoria(db: Session, anio: int, mes: int, acumulado: bool) -> dict[str, float]:
    admin = _presupuesto_por_categoria_grupo(db, anio, mes, acumulado, es_admin=True)
    op = _presupuesto_por_categoria_grupo(db, anio, mes, acumulado, es_admin=False)
    combinado = dict(admin)
    for cat, val in op.items():
        combinado[cat] = combinado.get(cat, 0.0) + val
    return combinado


def _ejecutado_por_categoria(db: Session, anio: int, mes: int, acumulado: bool) -> dict[str, float]:
    admin = _neto_por_categoria(db, anio, mes, acumulado, _FILTRO_ADMIN_SQL)
    op = _neto_por_categoria(db, anio, mes, acumulado, _FILTRO_OP_SQL)
    combinado = dict(admin)
    for cat, val in op.items():
        combinado[cat] = combinado.get(cat, 0.0) + val
    return combinado


def _ejecucion_vs_presupuesto(db: Session, anio: int, mes: int, acumulado: bool) -> EjecucionVsPresupuestoResponse:
    periodos = _periodos_disponibles_gastos(db)

    ejecutado = _ejecutado_por_categoria(db, anio, mes, acumulado)
    presupuesto = _presupuesto_por_categoria(db, anio, mes, acumulado)

    # Orden ASCENDENTE por nombre de categoría (RAW, antes del mapeo de
    # comas de presentación) -- Direction=1 en el Layout real de
    # "Ejecucion vs Presupuesto" (mensual), mismo desempate case-
    # insensitive que ya usa Ejecución Gastos.
    nombres_categoria = sorted(set(list(ejecutado) + list(presupuesto)), key=str.lower)
    filas = []
    for cat in nombres_categoria:
        pres = presupuesto.get(cat, 0.0)
        ejec = ejecutado.get(cat, 0.0)
        dif = ejec - pres
        filas.append(
            FilaPresupuesto(
                categoria=_nombre_display_ejecucion_gastos(cat),
                presupuesto=pres,
                ejecutado=ejec,
                diferencia=dif,
                diferencia_pct=(dif / pres * 100) if pres else 0.0,
            )
        )

    # Acumulado: Direction=2 en el Layout real de "Ejecucion vs
    # Presupuesto Acumulado" -- descendente por Presupuesto (TotalPresupuesto_AcumuladoN),
    # NO por nombre. El sort de Python es estable, así que las filas con
    # el mismo presupuesto (ej. dos en Q0) quedan en el orden alfabético
    # ya establecido arriba como desempate.
    if acumulado:
        filas.sort(key=lambda f: f.presupuesto, reverse=True)

    presupuesto_total = sum(f.presupuesto for f in filas)
    ejecutado_total = sum(f.ejecutado for f in filas)
    diferencia_total = ejecutado_total - presupuesto_total
    fila_total = FilaPresupuesto(
        categoria="Total",
        presupuesto=presupuesto_total,
        ejecutado=ejecutado_total,
        diferencia=diferencia_total,
        diferencia_pct=(diferencia_total / presupuesto_total * 100) if presupuesto_total else 0.0,
        negrita=True,
    )

    return EjecucionVsPresupuestoResponse(
        anio=anio, mes=mes, periodos_disponibles=periodos, filas=filas, fila_total=fila_total
    )


def obtener_ejecucion_vs_presupuesto_mensual(db: Session, anio: int | None, mes: int | None) -> EjecucionVsPresupuestoResponse:
    periodos = _periodos_disponibles_gastos(db)
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)
    return _ejecucion_vs_presupuesto(db, anio_resuelto, mes_resuelto, acumulado=False)


def obtener_ejecucion_vs_presupuesto_acumulado(db: Session, anio: int | None, mes: int | None) -> EjecucionVsPresupuestoResponse:
    periodos = _periodos_disponibles_gastos(db)
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)
    return _ejecucion_vs_presupuesto(db, anio_resuelto, mes_resuelto, acumulado=True)


# --- Presupuestos: Comparativo ejecutado (año-1 vs año, acumulado) -------
#
# DAX real: EgresosAnioAnterior filtra el MISMO acumulado (Sal_Mes <=
# mes) pero del año anterior -- no es el año anterior completo, es el
# acumulado hasta el mismo mes en los 2 años, para que la comparación sea
# pareja. Solo entran las categorías con movimiento en AL MENOS uno de
# los 2 años (17 filas en Agosto 2026, confirmado); las que no tuvieron
# ningún movimiento ni en 2025 ni en 2026 se excluyen -- a diferencia de
# las 2 páginas de arriba, que sí incluyen categorías con presupuesto Q0.
# Orden DESCENDENTE por Variación Q. (Direction=2 en el Layout real).
# Encabezados: en el .pbix real las columnas de la tabla vienen CRUZADAS
# (la medida TotalEjecutado_Acumulado -- año actual -- aparece bajo un
# encabezado que dice el año anterior y viceversa) -- acá se corrige: la
# columna "{año-1}" siempre trae EgresosAnioAnterior, "{año}" siempre
# TotalEjecutado_Acumulado, igual que la gráfica.


def obtener_comparativo_ejecutado(db: Session, anio: int | None, mes: int | None) -> ComparativoEjecutadoResponse:
    periodos = _periodos_disponibles_gastos(db)
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)

    actual = _ejecutado_por_categoria(db, anio_resuelto, mes_resuelto, acumulado=True)
    anterior = _ejecutado_por_categoria(db, anio_resuelto - 1, mes_resuelto, acumulado=True)

    nombres_categoria = sorted(set(list(actual) + list(anterior)), key=str.lower)
    filas = []
    for cat in nombres_categoria:
        a_anterior = anterior.get(cat, 0.0)
        a_actual = actual.get(cat, 0.0)
        if a_anterior == 0.0 and a_actual == 0.0:
            continue
        variacion = a_actual - a_anterior
        filas.append(
            FilaComparativoEjecutado(
                categoria=_nombre_display_ejecucion_gastos(cat),
                anio_anterior=a_anterior,
                anio_actual=a_actual,
                variacion=variacion,
                variacion_pct=(variacion / a_anterior * 100) if a_anterior else 0.0,
            )
        )

    filas.sort(key=lambda f: f.variacion, reverse=True)

    total_anterior = sum(f.anio_anterior for f in filas)
    total_actual = sum(f.anio_actual for f in filas)
    variacion_total = total_actual - total_anterior
    fila_total = FilaComparativoEjecutado(
        categoria="Total",
        anio_anterior=total_anterior,
        anio_actual=total_actual,
        variacion=variacion_total,
        variacion_pct=(variacion_total / total_anterior * 100) if total_anterior else 0.0,
        negrita=True,
    )

    return ComparativoEjecutadoResponse(
        anio=anio_resuelto,
        mes=mes_resuelto,
        anio_anterior=anio_resuelto - 1,
        periodos_disponibles=periodos,
        filas=filas,
        fila_total=fila_total,
    )


# --- Conciliación bancaria / Flujo de caja --------------------------------
#
# Fuentes reales:
#     dbo.SaldosBancos(ban_codigo, Sal_Mes, Sal_Ano, InicialL, EntradasL,
#         SalidasL, FinalL) -- cargada de vw_piq_saldos_bancos.csv, ES EL
#         SALDO CONTABLE por banco/mes (columna "Saldo Contabilidad" de
#         la conciliación real), confirmado contra el .pbix real: para
#         los 4 bancos en Agosto 2026, EntradasL/SalidasL cuadran EXACTO
#         (al centavo) contra SUM(Debitos)/SUM(Creditos) de
#         dbo.BalanceGeneral para esas mismas cuentas de banco. BANRURAL
#         trae 3 filas por período en el CSV (2 en cero) -- ya vienen
#         sumadas por banco/mes en la carga (cargar_datos_financiero_inicial.py).
#     dbo.ChequesCirculacion(ban_codigo, doc_fecha, doc_fchcobro, doc_monto)
#         -- "Documentos en Circulación" = emitidos hasta el cierre del
#         mes Y no cobrados a esa fecha (doc_fecha <= fin de mes AND
#         (doc_fchcobro IS NULL OR doc_fchcobro > fin de mes)) --
#         confirmado exacto contra Agosto 2026 (Q19,250.00 BAC / Q4,000.00
#         BANRURAL, los valores de control dados por el usuario). El
#         filtro anterior (agrupar por par_ano/par_mes del cheque) daba
#         un número distinto -- ESE era el filtro equivocado, no este.
#     dbo.BalanceGeneral -- Caja (cod_n5 110101001) e Inversión a Plazo
#         Fijo (TODAS las cuentas 110103xxx, antes solo 110103003 BAC y 110103004 Promérica), acumulado DENTRO DEL
#         AÑO (Sal_Ano = :anio AND Sal_Mes <= :mes, MISMA semántica YTD
#         que ya usa dashboard_financiero.py para el balance general --
#         NO acumulado desde 2023, ese fue un error de una investigación
#         previa que sumaba todos los años). Confirmado exacto contra
#         Agosto 2026 (Q1,200 / Q2,300,001 / Q1,500,000).
#
# "Saldo Banco" (columna independiente de la conciliación, el estado de
# cuenta real que reporta cada banco) NO es derivable de lo que tenemos:
# dbo.SaldoBancario existe pero está vacía, y aunque tuviera datos su
# esquema (Concepto/Año/Mes/Banco/Valor, un solo "Valor") no alcanza
# para las 4 cifras que hacen falta por banco/mes (Saldo inicial,
# Créditos, Débitos, Totales). Confirmado con BANRURAL Agosto 2026: el
# saldo inicial y el total que dio el usuario como referencia difieren
# en Q0.16 del saldo contable -- una diferencia real, no redondeo, que
# demuestra que es una fuente independiente.
#
# [ACTUALIZADO] El usuario pasó docs/legacy/financiero/SaldoBancario.csv
# -- export real de Agrequima.dbo.SaldoBancario del servidor 10.10.0.6,
# cargado en dbo.SaldoBancario (Concepto/Anio/Mes/Banco/Valor). 3
# conceptos por banco/mes: "Saldo inicial", "Creditos", "Debitos".
# Totales = Inicial + Créditos − Débitos − Documentos en Circulación
# (medida DAX real "Saldo Banco Conciliacion" del .pbix) -- verificado
# exacto contra Agosto 2026 para los 4 bancos. El banco se cruza SIN
# tilde (PROMÉRICA interno -> "PROMERICA" en este CSV).

# [BANCOS DINÁMICOS] Ya NO hay listas de bancos escritas a mano. La lista
# de bancos sale de los datos (unión de SaldosBancos, ChequesCirculacion y
# SaldoBancario, con el código normalizado: mayúsculas, sin tildes, sin
# espacios ni caracteres invisibles -- PROMÉRICA y PROMERICA son el mismo
# banco) y el nombre de cada pantalla, el color y el orden salen de
# dbo.CatalogoBancos (ver services/catalogo_bancos.py y
# deploy_servidor_real/19_catalogo_bancos_financiero.sql). Los valores que
# antes estaban acá (BAC #E31B23, BANRURAL #009B4D, BI #004B87, PROMÉRICA
# #00A651; en Flujo "BAC Reformador", "Banrural", "Banco Industrial",
# "Promerica", en ese orden) viven ahora como filas sembradas de esa tabla.
# Un banco que no esté en el catálogo aparece igual, con su código como
# nombre, en gris #9E9E9E y al final.
#
# [INVERSIONES A PLAZO] Tampoco hay cuentas fijas (antes 110103003 y
# 110103004): se toman TODAS las cuentas de BalanceGeneral cuyo cod_n5
# empiece con 110103, con la etiqueta derivada de nom_n5.
_PREFIJO_INVERSIONES_PLAZO = "110103"


def _ultimo_dia_mes(anio: int, mes: int) -> date:
    if mes == 12:
        return date(anio, 12, 31)
    return date(anio, mes + 1, 1) - timedelta(days=1)


def _periodos_disponibles_saldos_bancos(db: Session) -> list[PeriodoDisponibleGastos]:
    filas = db.execute(
        text("SELECT DISTINCT Sal_Ano, Sal_Mes FROM dbo.SaldosBancos ORDER BY Sal_Ano, Sal_Mes")
    ).all()
    return [PeriodoDisponibleGastos(anio=int(a), mes=int(m)) for a, m in filas if a is not None and m is not None]


def _bancos_en_datos(db: Session, resolutor: ResolutorBancos) -> list[BancoResuelto]:
    """Bancos ACTIVOS que aparecen en los datos: unión de SaldosBancos,
    ChequesCirculacion y SaldoBancario (de TODOS los períodos, igual que
    antes la lista fija se mostraba siempre completa), con el código
    normalizado para que PROMÉRICA y PROMERICA sean el mismo banco.
    Para retirar un banco viejo se pone activo = 0 en CatalogoBancos."""
    filas = db.execute(
        text(
            """
            SELECT ban_codigo AS codigo, 1 AS prioridad FROM dbo.SaldosBancos
            UNION
            SELECT ban_codigo, 2 FROM dbo.ChequesCirculacion
            UNION
            SELECT Banco, 3 FROM dbo.SaldoBancario
            """
        )
    ).all()
    # Texto con el que se ve el banco: el de la fuente más "contable"
    # (SaldosBancos > ChequesCirculacion > SaldoBancario), limpio.
    visibles: dict[str, tuple[int, str]] = {}
    for codigo, prioridad in filas:
        clave = resolutor.clave(codigo)
        texto = limpiar_texto(codigo)
        if clave is None or not texto:
            continue
        candidato = (prioridad, texto)
        if clave not in visibles or candidato < visibles[clave]:
            visibles[clave] = candidato
    return resolutor.resolver({clave: texto for clave, (_, texto) in visibles.items()})


def _saldos_bancos_del_mes(
    db: Session, anio: int, mes: int, resolutor: ResolutorBancos
) -> dict[str, tuple[float, float, float, float]]:
    filas = db.execute(
        text(
            """
            SELECT ban_codigo, InicialL, EntradasL, SalidasL, FinalL
            FROM dbo.SaldosBancos
            WHERE Sal_Ano = :anio AND Sal_Mes = :mes
            """
        ),
        {"anio": anio, "mes": mes},
    ).all()
    por_banco: dict[str, tuple[float, float, float, float]] = {}
    for codigo, inicial, entradas, salidas, final in filas:
        clave = resolutor.clave(codigo)
        if clave is None:
            continue
        nuevo = (_num(inicial), _num(entradas), _num(salidas), _num(final))
        previo = por_banco.get(clave)
        # Dos filas del mismo banco en el mes (el código vino escrito de
        # dos formas) se SUMAN en vez de pisarse.
        por_banco[clave] = nuevo if previo is None else tuple(a + b for a, b in zip(previo, nuevo))
    return por_banco


def _saldo_banco_del_mes(
    db: Session, anio: int, mes: int, resolutor: ResolutorBancos
) -> dict[str, tuple[float, float, float]]:
    filas = db.execute(
        text(
            """
            SELECT Banco, Concepto, SUM(Valor)
            FROM dbo.SaldoBancario
            WHERE Anio = :anio AND Mes = :mes
            GROUP BY Banco, Concepto
            """
        ),
        {"anio": anio, "mes": mes},
    ).all()
    por_banco: dict[str, dict[str, float]] = {}
    for banco, concepto, valor in filas:
        clave = resolutor.clave(banco)
        if clave is None:
            continue
        conceptos = por_banco.setdefault(clave, {})
        nombre_concepto = limpiar_texto(concepto)
        conceptos[nombre_concepto] = conceptos.get(nombre_concepto, 0.0) + _num(valor)
    return {
        banco: (
            valores.get("Saldo inicial", 0.0),
            valores.get("Creditos", 0.0),
            valores.get("Debitos", 0.0),
        )
        for banco, valores in por_banco.items()
    }


def _documentos_circulacion_por_banco(
    db: Session, anio: int, mes: int, resolutor: ResolutorBancos
) -> dict[str, float]:
    ultimo_dia = _ultimo_dia_mes(anio, mes)
    filas = db.execute(
        text(
            """
            SELECT ban_codigo, SUM(doc_monto)
            FROM dbo.ChequesCirculacion
            WHERE doc_fecha <= :ultimo_dia
              AND (doc_fchcobro IS NULL OR doc_fchcobro > :ultimo_dia)
            GROUP BY ban_codigo
            """
        ),
        {"ultimo_dia": ultimo_dia},
    ).all()
    por_banco: dict[str, float] = {}
    for codigo, monto in filas:
        clave = resolutor.clave(codigo)
        if clave is None:
            continue
        por_banco[clave] = por_banco.get(clave, 0.0) + _num(monto)
    return {clave: monto for clave, monto in por_banco.items() if monto}


def obtener_conciliacion_bancaria(db: Session, anio: int | None, mes: int | None) -> ConciliacionBancariaResponse:
    periodos = _periodos_disponibles_saldos_bancos(db)
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)

    resolutor = ResolutorBancos(cargar_catalogo_bancos(db))
    bancos_resueltos = ordenar_conciliacion(_bancos_en_datos(db, resolutor))
    saldos_por_banco = _saldos_bancos_del_mes(db, anio_resuelto, mes_resuelto, resolutor)
    saldo_banco_por_banco = _saldo_banco_del_mes(db, anio_resuelto, mes_resuelto, resolutor)
    documentos = _documentos_circulacion_por_banco(db, anio_resuelto, mes_resuelto, resolutor)

    bancos: list[BancoConciliacion] = []
    for banco_resuelto in bancos_resueltos:
        clave = banco_resuelto.clave
        datos = saldos_por_banco.get(clave)
        inicial, entradas, salidas, final = datos if datos else (None, None, None, None)

        datos_banco = saldo_banco_por_banco.get(clave)
        inicial_banco, creditos_banco, debitos_banco = datos_banco if datos_banco else (None, None, None)
        doc_circulacion = documentos.get(clave, 0.0)
        # Totales (Saldo Banco) = Inicial + Créditos − Débitos −
        # Documentos en Circulación -- medida DAX real "Saldo Banco
        # Conciliacion" del .pbix, verificada exacta contra Agosto 2026.
        total_banco = (
            inicial_banco + creditos_banco - debitos_banco - doc_circulacion if datos_banco is not None else None
        )

        filas = [
            FilaConciliacionBanco(descripcion="Saldo inicial", saldo_banco=inicial_banco, saldo_contabilidad=inicial),
            FilaConciliacionBanco(descripcion="(+) Créditos", saldo_banco=creditos_banco, saldo_contabilidad=entradas),
            FilaConciliacionBanco(descripcion="(−) Débitos", saldo_banco=debitos_banco, saldo_contabilidad=salidas),
            FilaConciliacionBanco(
                # 0.0 explícito (no None) -- un banco sin cheques
                # pendientes SÍ tiene un valor real (cero), no es un dato
                # faltante. La columna Contabilidad de esta fila queda
                # vacía siempre (no aplica ahí).
                descripcion="(−) Documentos en Circulación",
                saldo_banco=doc_circulacion,
                saldo_contabilidad=None,
            ),
            FilaConciliacionBanco(descripcion="Totales", saldo_banco=total_banco, saldo_contabilidad=final, negrita=True),
        ]
        bancos.append(
            BancoConciliacion(nombre=banco_resuelto.nombre_conciliacion, color=banco_resuelto.color, filas=filas)
        )

    return ConciliacionBancariaResponse(
        anio=anio_resuelto, mes=mes_resuelto, periodos_disponibles=periodos, bancos=bancos
    )


def _etiqueta_inversion_plazo(nom_n5, codigo: str) -> str:
    """Etiqueta de una fila de inversión a plazo, derivada de nom_n5 (sin
    caracteres invisibles): la entidad es lo que va antes del primer
    " - " (si no hay, el nombre completo), sin tildes y en minúsculas con
    inicial mayúscula. "BAC - FONDO DE INVERSIÓN" -> "(+) Inversiones Plazo
    Fijo Bac"; "PROMÉRICA - FONDO DE INVERSIÓN" -> "(+) Inversiones Plazo
    Fijo Promerica" (los mismos textos que antes estaban fijos en el
    código). Si el nombre ya dice "plazo fijo" no se repite."""
    nombre = limpiar_texto(nom_n5) or codigo
    entidad = re.split(r"\s+[-–—]\s+", nombre, maxsplit=1)[0]
    entidad = "".join(
        ch for ch in unicodedata.normalize("NFD", entidad) if unicodedata.category(ch) != "Mn"
    ).title()
    if "plazo fijo" in entidad.lower():
        return f"(+) {entidad}"
    return f"(+) Inversiones Plazo Fijo {entidad}"


def _inversiones_plazo(db: Session, anio: int, mes: int) -> list[tuple[str, float]]:
    """(etiqueta, saldo) de CADA cuenta de BalanceGeneral cuyo cod_n5
    empiece con 110103, ordenadas por cuenta. La lista sale de todos los
    datos (una cuenta sin movimiento en el período se muestra en Q0, como
    antes las dos fijas); el saldo es el acumulado DENTRO DEL AÑO
    (Sal_Ano = :anio AND Sal_Mes <= :mes), la misma semántica de siempre."""
    filas = db.execute(
        text(
            """
            SELECT cod_n5, nom_n5, Sal_Ano, Sal_Mes, Saldo
            FROM dbo.BalanceGeneral
            WHERE cod_n5 LIKE :patron
            """
        ),
        {"patron": f"%{_PREFIJO_INVERSIONES_PLAZO}%"},
    ).all()
    cuentas: dict[str, dict] = {}
    for cod_n5, nom_n5, sal_ano, sal_mes, saldo in filas:
        codigo = limpiar_texto(cod_n5).replace(" ", "")
        if not codigo.startswith(_PREFIJO_INVERSIONES_PLAZO):
            continue
        cuenta = cuentas.setdefault(codigo, {"periodo": (-1, -1), "nombre": None, "saldo": Decimal(0)})
        if sal_ano is None or sal_mes is None:
            continue
        # El nombre es el del último período en que existe la cuenta.
        if (sal_ano, sal_mes) >= cuenta["periodo"]:
            cuenta["periodo"], cuenta["nombre"] = (sal_ano, sal_mes), nom_n5
        if sal_ano == anio and sal_mes <= mes and saldo is not None:
            cuenta["saldo"] += saldo if isinstance(saldo, Decimal) else Decimal(str(saldo))
    return [
        (_etiqueta_inversion_plazo(cuentas[codigo]["nombre"], codigo), _num(cuentas[codigo]["saldo"]))
        for codigo in sorted(cuentas)
    ]


def obtener_flujo_caja(db: Session, anio: int | None, mes: int | None) -> FlujoCajaResponse:
    periodos = _periodos_disponibles_saldos_bancos(db)
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)

    caja = _num(
        db.execute(
            text(
                """
                SELECT SUM(Saldo) FROM dbo.BalanceGeneral
                WHERE cod_n5 = '110101001' AND Sal_Ano = :anio AND Sal_Mes <= :mes
                """
            ),
            {"anio": anio_resuelto, "mes": mes_resuelto},
        ).scalar()
    )
    inversiones = _inversiones_plazo(db, anio_resuelto, mes_resuelto)

    resolutor = ResolutorBancos(cargar_catalogo_bancos(db))
    bancos_resueltos = ordenar_flujo(_bancos_en_datos(db, resolutor))
    saldos_por_banco = _saldos_bancos_del_mes(db, anio_resuelto, mes_resuelto, resolutor)
    documentos = _documentos_circulacion_por_banco(db, anio_resuelto, mes_resuelto, resolutor)

    filas: list[FilaFlujoCaja] = [
        FilaFlujoCaja(tipo="TITULO_BANCOS", descripcion="Disponibilidad en bancos", saldos=None, disponibilidad=None),
        FilaFlujoCaja(tipo="CAJA", descripcion="Caja y Caja chica", saldos=caja, disponibilidad=None),
    ]
    total_bancos = caja
    for banco in bancos_resueltos:
        datos = saldos_por_banco.get(banco.clave)
        final = datos[3] if datos else 0.0
        total_bancos += final
        filas.append(FilaFlujoCaja(tipo="BANCO", descripcion=banco.nombre_flujo, saldos=final, disponibilidad=None))
    # Sin la palabra "Total" -- en Power BI/el spec Deneb la fila de
    # total no lleva descripción, solo los montos.
    filas.append(FilaFlujoCaja(tipo="TOTAL_BANCOS", descripcion="", saldos=total_bancos, disponibilidad=total_bancos))

    filas.append(
        FilaFlujoCaja(
            tipo="TITULO_CHEQUES",
            descripcion="(−) Cheques en circulación según conciliaciones bancarias",
            saldos=None,
            disponibilidad=None,
        )
    )
    total_cheques = 0.0
    # Mismo orden que la sección de bancos; bancos sin cheques pendientes
    # no se muestran (igual que en el reporte real).
    for banco in bancos_resueltos:
        monto = documentos.get(banco.clave)
        if monto:
            total_cheques += monto
            filas.append(FilaFlujoCaja(tipo="CHEQUE", descripcion=banco.nombre_flujo, saldos=monto, disponibilidad=None))
    filas.append(
        FilaFlujoCaja(tipo="TOTAL_CHEQUES", descripcion="", saldos=total_cheques, disponibilidad=total_cheques)
    )

    # OJO (instrucción explícita del usuario, verificada contra el
    # reporte real): NO se le restan los cheques -- el saldo contable
    # que ya trae dbo.SaldosBancos los tiene descontados.
    filas.append(
        FilaFlujoCaja(
            tipo="DISPONIBILIDAD",
            descripcion="Disponibilidad en depósitos monetarios y caja",
            saldos=None,
            disponibilidad=total_bancos,
        )
    )
    total_final = total_bancos
    for etiqueta, saldo in inversiones:
        total_final += saldo
        filas.append(FilaFlujoCaja(tipo="INVERSION", descripcion=etiqueta, saldos=None, disponibilidad=saldo))

    filas.append(
        FilaFlujoCaja(tipo="TOTAL_FINAL", descripcion="Disponibilidad", saldos=None, disponibilidad=total_final)
    )

    total_inversiones = sum(saldo for _, saldo in inversiones)
    grafica = [
        BarraFlujoCaja(etiqueta="Monetarios, Ahorro", valor=total_bancos, color="#4DB6AC"),
        BarraFlujoCaja(etiqueta="Inversiones", valor=total_inversiones, color="#90A4AE"),
        BarraFlujoCaja(etiqueta="Total disponibilidad", valor=total_final, color="#2C786C"),
    ]

    return FlujoCajaResponse(
        anio=anio_resuelto, mes=mes_resuelto, periodos_disponibles=periodos, filas=filas, grafica=grafica
    )

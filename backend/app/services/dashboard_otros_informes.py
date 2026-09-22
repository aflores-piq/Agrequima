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
    CuotaTotal = SUM(cuota) de AsociadosCuota para el año filtrado.
    Cancelado = SUM(Creditos) de BalanceGeneral para el mismo año, de las
        cuentas (cod_n5) que aparecen en AsociadosCuota para ese año --
        SIN filtro de mes: es la cancelación acumulada de TODO el año,
        no "hasta el mes" (confirmado: filtrar además por Sal_Mes daba
        634,000 en vez de 660,000 exacto).
    Saldo (Por cobrar) = CuotaTotal - Cancelado.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.dashboard_otros_informes import (
    CuotasAsociadosResponse,
    EjecucionGastosResponse,
    FilaCuotaAsociado,
    FilaGastoCategoria,
    KpisCuotasAsociados,
    PeriodoDisponibleGastos,
    TarjetaResumenGasto,
    TipoCuotaAsociados,
)
from app.services.agrupador_cuentas import cargar_mapas_agrupador, grupo_de_cuenta

_TIPOS_CUOTA = ("A", "B", "C")


def _num(valor) -> float:
    return float(valor) if valor is not None else 0.0


def _anios_disponibles_cuotas(db: Session) -> list[int]:
    filas = db.execute(text("SELECT DISTINCT Sal_Ano FROM dbo.AsociadosCuota ORDER BY Sal_Ano")).all()
    return [int(a) for (a,) in filas if a is not None]


def obtener_cuotas_asociados(db: Session, anio: int | None) -> CuotasAsociadosResponse:
    periodos = _anios_disponibles_cuotas(db)
    if anio is not None:
        anio_resuelto = anio
    elif periodos:
        anio_resuelto = periodos[-1]
    else:
        anio_resuelto = date.today().year

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
                    WHERE Sal_Ano = :anio
                    GROUP BY cod_n5
                ) bg ON bg.cod_n5 = ac.cod_n5
                WHERE ac.Sal_Ano = :anio AND ac.grupo IN ('A', 'B', 'C')
                ORDER BY ac.grupo, ac.nombre_mostrar
                """
            ),
            {"anio": anio_resuelto},
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
        anio=anio_resuelto, periodos_disponibles=periodos, kpis=kpis, tipos=tipos
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


def _ejecucion_gastos(db: Session, anio: int, mes: int, acumulado: bool) -> EjecucionGastosResponse:
    periodos = _periodos_disponibles_gastos(db)

    por_categoria_admin = _neto_por_categoria(db, anio, mes, acumulado, _FILTRO_ADMIN_SQL)
    por_categoria_op = _neto_por_categoria(db, anio, mes, acumulado, _FILTRO_OP_SQL)

    total_ejecutado_admin = sum(por_categoria_admin.values())
    total_ejecutado_op = sum(por_categoria_op.values())

    nombres_categoria = sorted(set(list(por_categoria_admin) + list(por_categoria_op)))
    categorias = [
        FilaGastoCategoria(
            categoria=cat,
            administracion=por_categoria_admin.get(cat, 0.0),
            peso_administracion=(por_categoria_admin.get(cat, 0.0) / total_ejecutado_admin * 100) if total_ejecutado_admin else 0.0,
            operacion=por_categoria_op.get(cat, 0.0),
            peso_operacion=(por_categoria_op.get(cat, 0.0) / total_ejecutado_op * 100) if total_ejecutado_op else 0.0,
            consolidado=por_categoria_admin.get(cat, 0.0) + por_categoria_op.get(cat, 0.0),
        )
        for cat in nombres_categoria
    ]
    categorias.sort(key=lambda f: -f.consolidado)

    fila_total_ejecutado = FilaGastoCategoria(
        categoria="Total ejecutado",
        administracion=total_ejecutado_admin,
        peso_administracion=100.0,
        operacion=total_ejecutado_op,
        peso_operacion=100.0,
        consolidado=total_ejecutado_admin + total_ejecutado_op,
    )

    presupuesto_admin = _presupuesto_grupo(db, anio, mes, acumulado, es_admin=True)
    presupuesto_op = _presupuesto_grupo(db, anio, mes, acumulado, es_admin=False)

    fila_presupuesto = FilaGastoCategoria(
        categoria="Presupuesto",
        administracion=presupuesto_admin,
        peso_administracion=100.0,
        operacion=presupuesto_op,
        peso_operacion=100.0,
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

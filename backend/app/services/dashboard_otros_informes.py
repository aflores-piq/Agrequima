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
    FilaCentroCosto,
    FilaCuotaAsociado,
    GrupoCentrosCosto,
    KpisCuotasAsociados,
    KpisEjecucionGastos,
    PeriodoDisponibleGastos,
    TipoCuotaAsociados,
)

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
# Fuentes reales:
#     dbo.Presupuestos(emp_nit, par_ano, par_mes, cta_codigo,
#         pre_presupuesto, cod_centro) -- presupuesto cargado mes a mes,
#         con datos completos 2023-2026 para los 22 centros de costo
#         reales (confirmado, sin huecos).
#     dbo.BalanceSaldos(Cta_Codigo, Sal_Ano, Sal_Mes, Debitos, Cod_Centro)
#         -- Ejecutado = SUM(Debitos), mismo campo que usa Egresos en
#         Estados Financieros (dashboard_financiero.py).
#     dbo.CentrosDeCosto(Cod_centro, Des_centro, nivel, CC_Grupo1) --
#         nombre de cada centro. Los códigos REALES usados en Presupuestos/
#         BalanceSaldos son siempre nivel 3 o 4 (el nivel hoja de cada
#         rama): AD-01/AD-02/AD-03 (Administración) y OP-01 + OP-0X-YY
#         (Operación) -- NUNCA aparecen los nodos intermedios "AD"/"OP"/
#         "OP-02"/"OP-03"/"OP-04" sueltos como código de transacción, solo
#         como agrupadores jerárquicos. Se agrupa por el prefijo del
#         código (AD- / OP-), no por CC_Grupo1 (que solo cubre un nivel).
#
# Filtro de cuenta: solo cta_codigo/Cta_Codigo que empiezan con '5'
# (cuentas de gastos) -- consistente con el nombre de la página
# ("Ejecución de GASTOS"); Presupuestos también trae una fila suelta con
# cta_codigo '410104001' (ingresos) que queda excluida a propósito.
#
# "Mensual" (página 4) filtra por mes exacto; "Acumulado" (página 5) usa
# Sal_Mes/par_mes <= mes, dentro del MISMO año (mismo patrón "acumulado"
# que el resto del módulo Financiero, reinicia cada enero).
#
# "Peso %" = participación de cada centro sobre el PRESUPUESTO TOTAL del
# grupo Administración+Operación (no sobre el ejecutado) -- es la
# interpretación estándar de "peso" en un reporte de ejecución
# presupuestaria (cuánto pesa cada centro en el presupuesto asignado).
# No hay una cifra de referencia del cliente para esta página todavía
# (a diferencia de Cuotas Asociados) -- los números se muestran
# transparentes para que el cliente los valide.

_GRUPOS_CENTRO_COSTO = (("Administración", "AD-"), ("Operación", "OP-"))


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


def _detalle_centros_costo(
    db: Session, anio: int, mes: int, acumulado: bool
) -> tuple[list[GrupoCentrosCosto], KpisEjecucionGastos]:
    condicion_mes_presupuesto = "p.par_mes <= :mes" if acumulado else "p.par_mes = :mes"
    condicion_mes_ejecutado = "bs.Sal_Mes <= :mes" if acumulado else "bs.Sal_Mes = :mes"

    presupuesto_por_centro = {
        centro: _num(valor)
        for centro, valor in db.execute(
            text(
                f"""
                SELECT p.cod_centro AS centro, SUM(p.pre_presupuesto) AS presupuesto
                FROM dbo.Presupuestos p
                WHERE p.par_ano = :anio AND {condicion_mes_presupuesto} AND p.cta_codigo LIKE '5%'
                GROUP BY p.cod_centro
                """
            ),
            {"anio": anio, "mes": mes},
        ).all()
    }

    ejecutado_por_centro = {
        centro: _num(valor)
        for centro, valor in db.execute(
            text(
                f"""
                SELECT bs.Cod_Centro AS centro, SUM(bs.Debitos) AS ejecutado
                FROM dbo.BalanceSaldos bs
                WHERE bs.Sal_Ano = :anio AND {condicion_mes_ejecutado} AND bs.Cta_Codigo LIKE '5%'
                GROUP BY bs.Cod_Centro
                """
            ),
            {"anio": anio, "mes": mes},
        ).all()
    }

    nombres_centro = dict(db.execute(text("SELECT Cod_centro, Des_centro FROM dbo.CentrosDeCosto")).all())

    presupuesto_total = sum(v for c, v in presupuesto_por_centro.items() if c != "0")

    grupos: list[GrupoCentrosCosto] = []
    for etiqueta, prefijo in _GRUPOS_CENTRO_COSTO:
        centros = sorted(
            c
            for c in set(list(presupuesto_por_centro) + list(ejecutado_por_centro))
            if c.startswith(prefijo)
        )
        filas = []
        for c in centros:
            presupuesto = presupuesto_por_centro.get(c, 0.0)
            ejecutado = ejecutado_por_centro.get(c, 0.0)
            filas.append(
                FilaCentroCosto(
                    centro=c,
                    nombre=nombres_centro.get(c) or c,
                    peso_porcentaje=(presupuesto / presupuesto_total * 100) if presupuesto_total else 0.0,
                    presupuesto=presupuesto,
                    ejecutado=ejecutado,
                    diferencia=presupuesto - ejecutado,
                )
            )
        grupos.append(
            GrupoCentrosCosto(
                grupo=etiqueta,
                filas=filas,
                total_presupuesto=sum(f.presupuesto for f in filas),
                total_ejecutado=sum(f.ejecutado for f in filas),
                total_diferencia=sum(f.diferencia for f in filas),
            )
        )

    kpis = KpisEjecucionGastos(
        presupuesto=sum(g.total_presupuesto for g in grupos),
        ejecutado=sum(g.total_ejecutado for g in grupos),
        diferencia=sum(g.total_diferencia for g in grupos),
    )
    return grupos, kpis


def obtener_ejecucion_gastos_mensual(db: Session, anio: int | None, mes: int | None) -> EjecucionGastosResponse:
    periodos = _periodos_disponibles_gastos(db)
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)
    grupos, kpis = _detalle_centros_costo(db, anio_resuelto, mes_resuelto, acumulado=False)
    return EjecucionGastosResponse(
        anio=anio_resuelto, mes=mes_resuelto, periodos_disponibles=periodos, kpis=kpis, grupos=grupos
    )


def obtener_ejecucion_gastos_acumulado(db: Session, anio: int | None, mes: int | None) -> EjecucionGastosResponse:
    periodos = _periodos_disponibles_gastos(db)
    anio_resuelto, mes_resuelto = _anio_mes_default_gastos(anio, mes, periodos)
    grupos, kpis = _detalle_centros_costo(db, anio_resuelto, mes_resuelto, acumulado=True)
    return EjecucionGastosResponse(
        anio=anio_resuelto, mes=mes_resuelto, periodos_disponibles=periodos, kpis=kpis, grupos=grupos
    )

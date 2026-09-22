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
    FilaCuotaAsociado,
    KpisCuotasAsociados,
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

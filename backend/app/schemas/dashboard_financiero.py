"""Esquemas de respuesta del dashboard Financiero (grupo "Estados
Financieros", 4 páginas) -- ver services/dashboard_financiero.py para
la lógica de cálculo y las fuentes (vw_piq_balance_saldos /
vw_piq_balance_general, espejadas desde CONTACC)."""

from pydantic import BaseModel


class GrupoMontoItem(BaseModel):
    grupo: str
    monto: float


class DetalleCuentaMovimiento(BaseModel):
    """Fila de detalle de Ingresos/Egresos por cuenta (páginas 1)."""

    grupo: str | None
    nombre_cuenta_n5: str | None
    mes_anterior: float
    saldo_acumulado: float


class DetalleCuentaComparativoMovimiento(BaseModel):
    """Fila de detalle de Ingresos/Egresos por cuenta (página 2)."""

    cuenta: str | None
    grupo: str | None
    monto_anio_anterior: float
    variacion: float
    monto_anio_actual: float


class DistribucionBalanceItem(BaseModel):
    etiqueta: str
    monto: float


class DetalleCuentaBalance(BaseModel):
    """Fila de detalle de Activo/Pasivo/Patrimonio (página 3)."""

    nombre_n5: str | None
    grupo: str | None
    saldo_mes_anterior: float
    saldo_acumulado_actual: float
    variacion: float


class DetalleCuentaBalanceComparativo(BaseModel):
    """Fila de detalle de Activo/Pasivo/Patrimonio (página 4)."""

    nombre_n5: str | None
    grupo: str | None
    saldo_acumulado_actual: float
    saldo_acumulado_anterior: float
    variacion: float


# --- Página 1: Estado de ingresos y desembolsos mensual ---


class KpisIngresosDesembolsosMensual(BaseModel):
    ingresos: float
    egresos: float
    resultado: float
    saldo_mes_corriente: float
    acumulado_saldo_mes_corriente: float
    saldo_mes_anterior: float


class IngresosDesembolsosMensual(BaseModel):
    kpis: KpisIngresosDesembolsosMensual
    cascada_ingresos_por_grupo: list[GrupoMontoItem]
    cascada_egresos_por_grupo: list[GrupoMontoItem]
    detalle_egresos: list[DetalleCuentaMovimiento]
    detalle_ingresos: list[DetalleCuentaMovimiento]


# --- Página 2: Estado de ingresos y desembolsos acumulado ---


class KpisIngresosDesembolsosAcumulado(BaseModel):
    ingresos: float
    egresos: float
    saldo_acumulado: float
    resultado_anio_actual: float
    variacion_resultado: float
    er_anio_anterior: float
    er_anio_actual: float
    er_mensual: float
    acumulado_saldo_anio_anterior: float


class IngresosDesembolsosAcumulado(BaseModel):
    kpis: KpisIngresosDesembolsosAcumulado
    detalle_egresos: list[DetalleCuentaComparativoMovimiento]
    detalle_ingresos: list[DetalleCuentaComparativoMovimiento]


# --- Página 3: Balance general acumulado mensual ---


class KpisBalanceGeneralMensual(BaseModel):
    activo: float
    pasivo: float
    patrimonio: float
    porcentaje_activo: float
    porcentaje_pasivo: float
    porcentaje_patrimonio: float
    porcentaje_fondos_por_aplicar: float
    balance_mensual: float


class BalanceGeneralMensual(BaseModel):
    kpis: KpisBalanceGeneralMensual
    distribucion_balance: list[DistribucionBalanceItem]
    detalle_activo: list[DetalleCuentaBalance]
    detalle_pasivo: list[DetalleCuentaBalance]
    detalle_patrimonio: list[DetalleCuentaBalance]


# --- Página 4: Balance general acumulado comparativo ---


class KpisBalanceGeneralComparativo(BaseModel):
    diferencia_porcentaje_activo: float
    variacion_q_activo: float
    diferencia_porcentaje_pasivo: float
    variacion_q_pasivo: float
    diferencia_porcentaje_patrimonio: float
    variacion_q_patrimonio: float
    total_acumulado_anterior: float
    total_acumulado_actual: float
    total_variacion: float
    balance_acumulado: float


class BalanceGeneralComparativo(BaseModel):
    kpis: KpisBalanceGeneralComparativo
    detalle_activo: list[DetalleCuentaBalanceComparativo]
    detalle_pasivo: list[DetalleCuentaBalanceComparativo]
    detalle_patrimonio: list[DetalleCuentaBalanceComparativo]


class DashboardFinancieroResponse(BaseModel):
    anio: int
    mes: int
    ingresos_desembolsos_mensual: IngresosDesembolsosMensual
    ingresos_desembolsos_acumulado: IngresosDesembolsosAcumulado
    balance_general_mensual: BalanceGeneralMensual
    balance_general_comparativo: BalanceGeneralComparativo

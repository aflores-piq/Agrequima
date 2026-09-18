"""Esquemas de respuesta del dashboard Financiero (grupo "Estados
Financieros", 4 páginas) -- ver services/dashboard_financiero.py para
la lógica de cálculo (fuentes: dbo.BalanceSaldos / dbo.BalanceGeneral,
cargadas con datos reales -- ver
services/cargar_datos_financiero_inicial.py).

Estructura calcada de las capturas reales del reporte viejo (Power BI,
ver docs/legacy/Financiero_capturas/): tablas de detalle agrupadas por
Grupo (dbo.CatalogoAgrupadorCuentas), con fila "Total" por tabla, y una
banda final por página ("Resultado del ejercicio" en las páginas 1/2,
"Total pasivo y patrimonio" en las páginas 3/4)."""

from pydantic import BaseModel


class PeriodoDisponible(BaseModel):
    anio: int
    mes: int


# --- Compartidos ---


class FilaCuentaMensual(BaseModel):
    """Una cuenta individual dentro de un grupo (página 1) -- nivel que
    se muestra al expandir la fila de Grupo en la tabla."""

    cuenta: str
    mes_anterior: float
    mes_actual: float
    acumulado_anio: float


class FilaGrupoMensual(BaseModel):
    """Una fila de detalle (página 1): grupo + los 2 meses + acumulado
    del año, con las cuentas individuales que lo componen."""

    grupo: str
    mes_anterior: float
    mes_actual: float
    acumulado_anio: float
    cuentas: list[FilaCuentaMensual] = []


class TotalMensual(BaseModel):
    mes_anterior: float
    mes_actual: float
    acumulado_anio: float


class FilaCuentaComparativa(BaseModel):
    cuenta: str
    anio_anterior: float
    anio_actual: float
    variacion: float


class FilaGrupoComparativa(BaseModel):
    """Una fila de detalle (página 2): grupo + año anterior/actual +
    variación (variación al final), con las cuentas individuales."""

    grupo: str
    anio_anterior: float
    anio_actual: float
    variacion: float
    cuentas: list[FilaCuentaComparativa] = []


class TotalComparativo(BaseModel):
    anio_anterior: float
    anio_actual: float
    variacion: float


class FilaCuentaBalanceMensual(BaseModel):
    cuenta: str
    mes_anterior: float
    mes_actual: float
    diferencia: float


class FilaGrupoBalanceMensual(BaseModel):
    """Detalle de Activo/Pasivo/Patrimonio (página 3): grupo + los 2
    meses + diferencia, con las cuentas individuales."""

    grupo: str
    mes_anterior: float
    mes_actual: float
    diferencia: float
    cuentas: list[FilaCuentaBalanceMensual] = []


class TotalBalanceMensual(BaseModel):
    mes_anterior: float
    mes_actual: float
    diferencia: float


class FilaCuentaBalanceComparativa(BaseModel):
    cuenta: str
    anio_anterior: float
    anio_actual: float
    variacion: float


class FilaGrupoBalanceComparativa(BaseModel):
    """Detalle de Activo/Pasivo/Patrimonio (página 4): grupo + [mes]
    año anterior/actual + variación, con las cuentas individuales."""

    grupo: str
    anio_anterior: float
    anio_actual: float
    variacion: float
    cuentas: list[FilaCuentaBalanceComparativa] = []


class TotalBalanceComparativo(BaseModel):
    anio_anterior: float
    anio_actual: float
    variacion: float


# --- Página 1: Estado de ingresos y desembolsos mensual ---


class KpisIngresosDesembolsosMensual(BaseModel):
    ingresos: float
    egresos: float
    resultado: float


class BarraTresCategorias(BaseModel):
    """3 barras de un solo período: Ingresos netos / Egresos / Resultado."""

    ingresos: float
    egresos: float
    resultado: float


class IngresosDesembolsosMensual(BaseModel):
    kpis: KpisIngresosDesembolsosMensual
    etiqueta_mes_anterior: str
    etiqueta_mes_actual: str
    etiqueta_acumulado: str
    titulo_grafico_mes: str
    titulo_grafico_acumulado: str
    grafico_mes: BarraTresCategorias
    grafico_acumulado: BarraTresCategorias
    detalle_ingresos: list[FilaGrupoMensual]
    total_ingresos: TotalMensual
    detalle_egresos: list[FilaGrupoMensual]
    total_egresos: TotalMensual
    resultado_del_ejercicio: TotalMensual


# --- Página 2: Estado de ingresos y desembolsos acumulado ---


class KpisIngresosDesembolsosAcumulado(BaseModel):
    ingresos: float
    egresos: float
    saldo: float


class SerieAnioTresCategorias(BaseModel):
    """Una serie (un año) del gráfico agrupado: Ingresos/Egresos/Resultado."""

    anio: int
    ingresos: float
    egresos: float
    resultado: float


class IngresosDesembolsosAcumulado(BaseModel):
    kpis: KpisIngresosDesembolsosAcumulado
    etiqueta_anio_anterior: str
    etiqueta_anio_actual: str
    titulo_grafico: str
    grafico: list[SerieAnioTresCategorias]
    detalle_ingresos: list[FilaGrupoComparativa]
    total_ingresos: TotalComparativo
    detalle_egresos: list[FilaGrupoComparativa]
    total_egresos: TotalComparativo
    resultado_del_ejercicio: TotalComparativo


# --- Página 3: Balance general acumulado mensual ---


class KpisBalanceGeneralMensual(BaseModel):
    activo: float
    pasivo: float
    patrimonio: float


class DistribucionBalanceItem(BaseModel):
    etiqueta: str
    monto: float
    porcentaje: float


class BalanceGeneralMensual(BaseModel):
    kpis: KpisBalanceGeneralMensual
    etiqueta_mes_anterior: str
    etiqueta_mes_actual: str
    # 3 porciones (Pasivo sin fondos / Patrimonio / Fondos por aplicar)
    # que suman 100% de Activo -- Activo NO es una porción, se muestra
    # aparte como total de referencia (ver activo_referencia).
    distribucion_balance: list[DistribucionBalanceItem]
    activo_referencia: float
    detalle_activo: list[FilaGrupoBalanceMensual]
    total_activo: TotalBalanceMensual
    detalle_pasivo: list[FilaGrupoBalanceMensual]
    total_pasivo: TotalBalanceMensual
    detalle_patrimonio: list[FilaGrupoBalanceMensual]
    total_patrimonio: TotalBalanceMensual
    total_pasivo_y_patrimonio: TotalBalanceMensual


# --- Página 4: Balance general acumulado comparativo ---


class KpiComparativoActivoPasivoPatrimonio(BaseModel):
    diferencia_porcentaje: float
    variacion_q: float


class KpisBalanceGeneralComparativo(BaseModel):
    activo: KpiComparativoActivoPasivoPatrimonio
    pasivo: KpiComparativoActivoPasivoPatrimonio
    patrimonio: KpiComparativoActivoPasivoPatrimonio


class SerieAnioBalance(BaseModel):
    anio: int
    activo: float
    pasivo: float
    patrimonio: float


class BalanceGeneralComparativo(BaseModel):
    kpis: KpisBalanceGeneralComparativo
    etiqueta_anio_anterior: str
    etiqueta_anio_actual: str
    titulo_grafico: str
    grafico: list[SerieAnioBalance]
    detalle_activo: list[FilaGrupoBalanceComparativa]
    total_activo: TotalBalanceComparativo
    detalle_pasivo: list[FilaGrupoBalanceComparativa]
    total_pasivo: TotalBalanceComparativo
    detalle_patrimonio: list[FilaGrupoBalanceComparativa]
    total_patrimonio: TotalBalanceComparativo
    total_pasivo_y_patrimonio: TotalBalanceComparativo


class DashboardFinancieroResponse(BaseModel):
    anio: int
    mes: int
    periodos_disponibles: list[PeriodoDisponible]
    ingresos_desembolsos_mensual: IngresosDesembolsosMensual
    ingresos_desembolsos_acumulado: IngresosDesembolsosAcumulado
    balance_general_mensual: BalanceGeneralMensual
    balance_general_comparativo: BalanceGeneralComparativo

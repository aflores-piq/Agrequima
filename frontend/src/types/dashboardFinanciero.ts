export interface PeriodoDisponible {
  anio: number;
  mes: number;
}

export interface FilaCuentaMensual {
  cuenta: string;
  mes_anterior: number;
  mes_actual: number;
  acumulado_anio: number;
}

export interface FilaGrupoMensual {
  grupo: string;
  mes_anterior: number;
  mes_actual: number;
  acumulado_anio: number;
  cuentas: FilaCuentaMensual[];
}

export interface TotalMensual {
  mes_anterior: number;
  mes_actual: number;
  acumulado_anio: number;
}

export interface FilaCuentaComparativa {
  cuenta: string;
  anio_anterior: number;
  anio_actual: number;
  variacion: number;
}

export interface FilaGrupoComparativa {
  grupo: string;
  anio_anterior: number;
  anio_actual: number;
  variacion: number;
  cuentas: FilaCuentaComparativa[];
}

export interface TotalComparativo {
  anio_anterior: number;
  anio_actual: number;
  variacion: number;
}

export interface FilaCuentaBalanceMensual {
  cuenta: string;
  mes_anterior: number;
  mes_actual: number;
  diferencia: number;
}

export interface FilaGrupoBalanceMensual {
  grupo: string;
  mes_anterior: number;
  mes_actual: number;
  diferencia: number;
  cuentas: FilaCuentaBalanceMensual[];
}

export interface TotalBalanceMensual {
  mes_anterior: number;
  mes_actual: number;
  diferencia: number;
}

export interface FilaCuentaBalanceComparativa {
  cuenta: string;
  anio_anterior: number;
  anio_actual: number;
  variacion: number;
}

export interface FilaGrupoBalanceComparativa {
  grupo: string;
  anio_anterior: number;
  anio_actual: number;
  variacion: number;
  cuentas: FilaCuentaBalanceComparativa[];
}

export interface TotalBalanceComparativo {
  anio_anterior: number;
  anio_actual: number;
  variacion: number;
}

export interface KpisIngresosDesembolsosMensual {
  ingresos: number;
  egresos: number;
  resultado: number;
}

export interface BarraTresCategorias {
  ingresos: number;
  egresos: number;
  resultado: number;
}

export interface IngresosDesembolsosMensual {
  kpis: KpisIngresosDesembolsosMensual;
  etiqueta_mes_anterior: string;
  etiqueta_mes_actual: string;
  etiqueta_acumulado: string;
  titulo_grafico_mes: string;
  titulo_grafico_acumulado: string;
  grafico_mes: BarraTresCategorias;
  grafico_acumulado: BarraTresCategorias;
  detalle_ingresos: FilaGrupoMensual[];
  total_ingresos: TotalMensual;
  detalle_egresos: FilaGrupoMensual[];
  total_egresos: TotalMensual;
  resultado_del_ejercicio: TotalMensual;
}

export interface KpisIngresosDesembolsosAcumulado {
  ingresos: number;
  egresos: number;
  saldo: number;
}

export interface SerieAnioTresCategorias {
  anio: number;
  ingresos: number;
  egresos: number;
  resultado: number;
}

export interface IngresosDesembolsosAcumulado {
  kpis: KpisIngresosDesembolsosAcumulado;
  etiqueta_anio_anterior: string;
  etiqueta_anio_actual: string;
  titulo_grafico: string;
  grafico: SerieAnioTresCategorias[];
  detalle_ingresos: FilaGrupoComparativa[];
  total_ingresos: TotalComparativo;
  detalle_egresos: FilaGrupoComparativa[];
  total_egresos: TotalComparativo;
  resultado_del_ejercicio: TotalComparativo;
}

export interface KpisBalanceGeneralMensual {
  activo: number;
  pasivo: number;
  patrimonio: number;
}

export interface DistribucionBalanceItem {
  etiqueta: string;
  monto: number;
  porcentaje: number;
}

export interface BalanceGeneralMensual {
  kpis: KpisBalanceGeneralMensual;
  etiqueta_mes_anterior: string;
  etiqueta_mes_actual: string;
  distribucion_balance: DistribucionBalanceItem[];
  activo_referencia: number;
  detalle_activo: FilaGrupoBalanceMensual[];
  total_activo: TotalBalanceMensual;
  detalle_pasivo: FilaGrupoBalanceMensual[];
  total_pasivo: TotalBalanceMensual;
  detalle_patrimonio: FilaGrupoBalanceMensual[];
  total_patrimonio: TotalBalanceMensual;
  total_pasivo_y_patrimonio: TotalBalanceMensual;
}

export interface KpiComparativoActivoPasivoPatrimonio {
  diferencia_porcentaje: number;
  variacion_q: number;
}

export interface KpisBalanceGeneralComparativo {
  activo: KpiComparativoActivoPasivoPatrimonio;
  pasivo: KpiComparativoActivoPasivoPatrimonio;
  patrimonio: KpiComparativoActivoPasivoPatrimonio;
}

export interface SerieAnioBalance {
  anio: number;
  activo: number;
  pasivo: number;
  patrimonio: number;
}

export interface BalanceGeneralComparativo {
  kpis: KpisBalanceGeneralComparativo;
  etiqueta_anio_anterior: string;
  etiqueta_anio_actual: string;
  titulo_grafico: string;
  grafico: SerieAnioBalance[];
  detalle_activo: FilaGrupoBalanceComparativa[];
  total_activo: TotalBalanceComparativo;
  detalle_pasivo: FilaGrupoBalanceComparativa[];
  total_pasivo: TotalBalanceComparativo;
  detalle_patrimonio: FilaGrupoBalanceComparativa[];
  total_patrimonio: TotalBalanceComparativo;
  total_pasivo_y_patrimonio: TotalBalanceComparativo;
}

export interface DashboardFinancieroResponse {
  anio: number;
  mes: number;
  periodos_disponibles: PeriodoDisponible[];
  ingresos_desembolsos_mensual: IngresosDesembolsosMensual;
  ingresos_desembolsos_acumulado: IngresosDesembolsosAcumulado;
  balance_general_mensual: BalanceGeneralMensual;
  balance_general_comparativo: BalanceGeneralComparativo;
}

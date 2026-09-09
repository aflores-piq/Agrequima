export interface GrupoMontoItem {
  grupo: string;
  monto: number;
}

export interface DetalleCuentaMovimiento {
  grupo: string | null;
  nombre_cuenta_n5: string | null;
  mes_anterior: number;
  saldo_acumulado: number;
}

export interface DetalleCuentaComparativoMovimiento {
  cuenta: string | null;
  grupo: string | null;
  monto_anio_anterior: number;
  variacion: number;
  monto_anio_actual: number;
}

export interface DistribucionBalanceItem {
  etiqueta: string;
  monto: number;
}

export interface DetalleCuentaBalance {
  nombre_n5: string | null;
  grupo: string | null;
  saldo_mes_anterior: number;
  saldo_acumulado_actual: number;
  variacion: number;
}

export interface DetalleCuentaBalanceComparativo {
  nombre_n5: string | null;
  grupo: string | null;
  saldo_acumulado_actual: number;
  saldo_acumulado_anterior: number;
  variacion: number;
}

export interface KpisIngresosDesembolsosMensual {
  ingresos: number;
  egresos: number;
  resultado: number;
  saldo_mes_corriente: number;
  acumulado_saldo_mes_corriente: number;
  saldo_mes_anterior: number;
}

export interface IngresosDesembolsosMensual {
  kpis: KpisIngresosDesembolsosMensual;
  cascada_ingresos_por_grupo: GrupoMontoItem[];
  cascada_egresos_por_grupo: GrupoMontoItem[];
  detalle_egresos: DetalleCuentaMovimiento[];
  detalle_ingresos: DetalleCuentaMovimiento[];
}

export interface KpisIngresosDesembolsosAcumulado {
  ingresos: number;
  egresos: number;
  saldo_acumulado: number;
  resultado_anio_actual: number;
  variacion_resultado: number;
  er_anio_anterior: number;
  er_anio_actual: number;
  er_mensual: number;
  acumulado_saldo_anio_anterior: number;
}

export interface IngresosDesembolsosAcumulado {
  kpis: KpisIngresosDesembolsosAcumulado;
  detalle_egresos: DetalleCuentaComparativoMovimiento[];
  detalle_ingresos: DetalleCuentaComparativoMovimiento[];
}

export interface KpisBalanceGeneralMensual {
  activo: number;
  pasivo: number;
  patrimonio: number;
  porcentaje_activo: number;
  porcentaje_pasivo: number;
  porcentaje_patrimonio: number;
  porcentaje_fondos_por_aplicar: number;
  balance_mensual: number;
}

export interface BalanceGeneralMensual {
  kpis: KpisBalanceGeneralMensual;
  distribucion_balance: DistribucionBalanceItem[];
  detalle_activo: DetalleCuentaBalance[];
  detalle_pasivo: DetalleCuentaBalance[];
  detalle_patrimonio: DetalleCuentaBalance[];
}

export interface KpisBalanceGeneralComparativo {
  diferencia_porcentaje_activo: number;
  variacion_q_activo: number;
  diferencia_porcentaje_pasivo: number;
  variacion_q_pasivo: number;
  diferencia_porcentaje_patrimonio: number;
  variacion_q_patrimonio: number;
  total_acumulado_anterior: number;
  total_acumulado_actual: number;
  total_variacion: number;
  balance_acumulado: number;
}

export interface BalanceGeneralComparativo {
  kpis: KpisBalanceGeneralComparativo;
  detalle_activo: DetalleCuentaBalanceComparativo[];
  detalle_pasivo: DetalleCuentaBalanceComparativo[];
  detalle_patrimonio: DetalleCuentaBalanceComparativo[];
}

export interface DashboardFinancieroResponse {
  anio: number;
  mes: number;
  ingresos_desembolsos_mensual: IngresosDesembolsosMensual;
  ingresos_desembolsos_acumulado: IngresosDesembolsosAcumulado;
  balance_general_mensual: BalanceGeneralMensual;
  balance_general_comparativo: BalanceGeneralComparativo;
}

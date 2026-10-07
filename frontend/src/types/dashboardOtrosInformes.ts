// Tipos del grupo "Otros informes financieros" -- 1:1 con
// backend/app/schemas/dashboard_otros_informes.py.

export interface FilaCuotaAsociado {
  nombre: string;
  cuota: number;
  cancelado: number;
  saldo: number;
}

export interface TipoCuotaAsociados {
  tipo: string;
  filas: FilaCuotaAsociado[];
  total_cuota: number;
  total_cancelado: number;
  total_saldo: number;
}

export interface KpisCuotasAsociados {
  total: number;
  cancelado: number;
  por_cobrar: number;
}

export interface CuotasAsociadosResponse {
  anio: number;
  mes: number;
  periodos_disponibles: PeriodoDisponibleGastos[];
  kpis: KpisCuotasAsociados;
  tipos: TipoCuotaAsociados[];
}

export interface PeriodoDisponibleGastos {
  anio: number;
  mes: number;
}

// Misma forma para las filas de la tabla (una por categoría de
// GroupEgresos) y para las 2 filas de resumen que van debajo
// (Presupuesto / Ejecución) -- ver dashboard_otros_informes.py.
export interface FilaGastoCategoria {
  categoria: string;
  administracion: number;
  peso_administracion: number;
  operacion: number;
  peso_operacion: number;
  consolidado: number;
}

export interface TarjetaResumenGasto {
  grupo: string;
  presupuesto: number;
  ejecutado: number;
  porcentaje_ejecucion: number;
  diferencia: number;
}

export interface EjecucionGastosResponse {
  anio: number;
  mes: number;
  periodos_disponibles: PeriodoDisponibleGastos[];
  categorias: FilaGastoCategoria[];
  fila_total_ejecutado: FilaGastoCategoria;
  fila_presupuesto: FilaGastoCategoria;
  fila_ejecucion: FilaGastoCategoria;
  tarjetas: TarjetaResumenGasto[];
}

// --- Presupuestos: Ejecución vs presupuesto (mensual / acumulado) --------

export interface FilaPresupuesto {
  categoria: string;
  presupuesto: number;
  ejecutado: number;
  diferencia: number;
  diferencia_pct: number;
  negrita: boolean;
}

export interface EjecucionVsPresupuestoResponse {
  anio: number;
  mes: number;
  periodos_disponibles: PeriodoDisponibleGastos[];
  filas: FilaPresupuesto[];
  fila_total: FilaPresupuesto;
}

// --- Presupuestos: Comparativo ejecutado (año-1 vs año, acumulado) -------

export interface FilaComparativoEjecutado {
  categoria: string;
  anio_anterior: number;
  anio_actual: number;
  variacion: number;
  variacion_pct: number;
  negrita: boolean;
}

export interface ComparativoEjecutadoResponse {
  anio: number;
  mes: number;
  anio_anterior: number;
  periodos_disponibles: PeriodoDisponibleGastos[];
  filas: FilaComparativoEjecutado[];
  fila_total: FilaComparativoEjecutado;
}

// --- Conciliación bancaria -----------------------------------------------

export interface FilaConciliacionBanco {
  descripcion: string;
  saldo_banco: number | null;
  saldo_contabilidad: number | null;
  negrita: boolean;
}

export interface BancoConciliacion {
  nombre: string;
  color: string;
  filas: FilaConciliacionBanco[];
}

export interface ConciliacionBancariaResponse {
  anio: number;
  mes: number;
  periodos_disponibles: PeriodoDisponibleGastos[];
  bancos: BancoConciliacion[];
}

// --- Flujo de caja ---------------------------------------------------------

export type TipoFilaFlujoCaja =
  | "TITULO_BANCOS"
  | "CAJA"
  | "BANCO"
  | "TOTAL_BANCOS"
  | "TITULO_CHEQUES"
  | "CHEQUE"
  | "TOTAL_CHEQUES"
  | "DISPONIBILIDAD"
  | "INVERSION"
  | "TOTAL_FINAL";

export interface FilaFlujoCaja {
  tipo: TipoFilaFlujoCaja;
  descripcion: string;
  saldos: number | null;
  disponibilidad: number | null;
}

export interface BarraFlujoCaja {
  etiqueta: string;
  valor: number;
  color: string;
}

export interface FlujoCajaResponse {
  anio: number;
  mes: number;
  periodos_disponibles: PeriodoDisponibleGastos[];
  filas: FilaFlujoCaja[];
  grafica: BarraFlujoCaja[];
}

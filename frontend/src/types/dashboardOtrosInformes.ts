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
  periodos_disponibles: number[];
  kpis: KpisCuotasAsociados;
  tipos: TipoCuotaAsociados[];
}

export interface PeriodoDisponibleGastos {
  anio: number;
  mes: number;
}

export interface FilaCentroCosto {
  centro: string;
  nombre: string;
  peso_porcentaje: number;
  presupuesto: number;
  ejecutado: number;
  diferencia: number;
}

export interface GrupoCentrosCosto {
  grupo: string;
  filas: FilaCentroCosto[];
  total_presupuesto: number;
  total_ejecutado: number;
  total_diferencia: number;
}

export interface KpisEjecucionGastos {
  presupuesto: number;
  ejecutado: number;
  diferencia: number;
}

export interface EjecucionGastosResponse {
  anio: number;
  mes: number;
  periodos_disponibles: PeriodoDisponibleGastos[];
  kpis: KpisEjecucionGastos;
  grupos: GrupoCentrosCosto[];
}

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

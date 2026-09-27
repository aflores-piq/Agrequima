// Tipos de "Otros ingresos generados" -- 1:1 con
// backend/app/schemas/dashboard_otro_ingreso.py.

export interface FilaOtroIngreso {
  concepto: string;
  ejecutado_anio_anterior: number;
  presupuesto_anio: number;
  ejecutado_anio: number;
  porcentaje_ejecucion: number;
}

export interface OtroIngresoResponse {
  anio: number;
  anio_anterior: number;
  anios_disponibles: number[];
  filas: FilaOtroIngreso[];
  total: FilaOtroIngreso;
}

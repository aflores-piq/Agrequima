// Tipos de "Otros ingresos generados" -- 1:1 con
// backend/app/schemas/dashboard_otro_ingreso.py.

export interface FilaOtroIngreso {
  concepto: string;
  ejecutado_anio_anterior: number;
  presupuesto_anio: number;
  ejecutado_anio: number;
  porcentaje_ejecucion: number;
}

export interface FilaResumenIngresos {
  concepto: string;
  monto: number;
  porcentaje: number;
}

// Cuadro "Total ingresos" (cuotas de asociados + 4.5 por millar + otros ingresos),
// acumulado del año hasta `mes_corte`.
export interface ResumenIngresos {
  anio: number;
  mes_corte: number;
  filas: FilaResumenIngresos[];
  total: FilaResumenIngresos;
}

export interface OtroIngresoResponse {
  anio: number;
  anio_anterior: number;
  anio_anterior_sin_datos: boolean;
  anios_disponibles: number[];
  filas: FilaOtroIngreso[];
  total: FilaOtroIngreso;
  resumen_ingresos: ResumenIngresos | null;
}

// Tipos de "Importaciones" DENTRO del módulo Financiero -- 1:1 con
// backend/app/schemas/dashboard_importaciones_financiero.py. Distinto
// del dashboard "Importaciones" (Plaguicidas/Nutrientes).
import type { PeriodoDisponibleGastos } from "./dashboardOtrosInformes";

export interface FilaCIFMes {
  mes: string;
  cif_anio_anterior: number | null;
  pct_anio_anterior: number | null;
  cif_anio_actual: number;
  pct_anio_actual: number;
  variacion: number | null;
  variacion_pct: number | null;
  negrita: boolean;
}

export interface PuntoCIFMes {
  mes: string;
  cif_anio_anterior: number | null;
  cif_anio_actual: number;
}

export interface PuntoPrecioMes {
  mes: string;
  agrequima: number;
  gremiagro: number;
  total: number;
}

// --- 1. Ingresos por importación ------------------------------------------

export interface IngresosImportacionResponse {
  anio: number;
  anio_anterior: number;
  anio_anterior_sin_datos: boolean;
  anios_disponibles: number[];
  ultimo_mes_con_datos: number;
  filas: FilaCIFMes[];
  fila_total: FilaCIFMes;
  grafico_cif: PuntoCIFMes[];
  grafico_precio: PuntoPrecioMes[];
}

// --- 2. Ingresos por importación comparativo ------------------------------

export interface BloqueComparativoInstitucion {
  institucion: string;
  titulo: string;
  anio_anterior_sin_datos: boolean;
  filas: FilaCIFMes[];
  fila_total: FilaCIFMes;
  grafico: PuntoCIFMes[];
}

export interface ImportacionComparativoResponse {
  anio: number;
  anio_anterior: number;
  anios_disponibles: number[];
  bloques: BloqueComparativoInstitucion[];
}

// --- 3. Comparación importaciones Kilolitros ------------------------------

export interface TarjetaCambioCantidad {
  etiqueta: string;
  mensaje: string;
}

export interface FilaPrecioKilolitro {
  etiqueta: string;
  precio_anio_anterior: number | null;
  precio_anio_actual: number | null;
  variacion_pct: number | null;
  negrita: boolean;
}

export interface KilolitrosResponse {
  anio: number;
  mes: number;
  anio_anterior: number;
  periodos_disponibles: PeriodoDisponibleGastos[];
  tarjetas: TarjetaCambioCantidad[];
  filas_precio: FilaPrecioKilolitro[];
}

// --- 4. Ingresos por contribución 4.5 por millar --------------------------

export interface PuntoContribucionMes {
  mes: string;
  anio_anterior: number;
  presupuesto: number;
  anio_actual: number;
}

export interface TarjetaResumenContribucion {
  presupuesto: number;
  realizado: number;
  porcentaje_ejecucion: number | null;
}

export interface ContribucionMillarResponse {
  anio: number;
  mes: number;
  periodos_disponibles: PeriodoDisponibleGastos[];
  grafico: PuntoContribucionMes[];
  tarjeta_mes: TarjetaResumenContribucion;
  tarjeta_acumulada: TarjetaResumenContribucion;
}

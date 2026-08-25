export interface ResumenExcepcionPlaguicida {
  ingrediente_key: string;
  ingrediente_ejemplo: string | null;
  transacciones: number;
  cantidad_total: number;
  cif_usd_total: number;
  posible_error_captura: boolean;
}

export interface DetalleExcepcionPlaguicida {
  recibointerno: string | null;
  ingrediente_act: string | null;
  ingrediente_key: string | null;
  producto: string | null;
}

export interface PaginaDetalleExcepcionesPlaguicidas {
  total: number;
  pagina: number;
  tamano_pagina: number;
  filas: DetalleExcepcionPlaguicida[];
}

export interface ExcepcionesPlaguicidasResponse {
  resumen: ResumenExcepcionPlaguicida[];
  detalle: PaginaDetalleExcepcionesPlaguicidas;
}

export interface ResumenExcepcionNutriente {
  nombre_key: string;
  nombre_ejemplo: string | null;
  transacciones: number;
  cif_dolares_total: number;
  posible_error_captura: boolean;
}

export interface DetalleExcepcionNutriente {
  no_licencia: string | null;
  nombre_comercial: string | null;
  nombre_key: string | null;
}

export interface PaginaDetalleExcepcionesNutrientes {
  total: number;
  pagina: number;
  tamano_pagina: number;
  filas: DetalleExcepcionNutriente[];
}

export interface ExcepcionesNutrientesResponse {
  resumen: ResumenExcepcionNutriente[];
  detalle: PaginaDetalleExcepcionesNutrientes;
}

export interface ActualizarAgrupadorResponse {
  filas_actualizadas: number;
}

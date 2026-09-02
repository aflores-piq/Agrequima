export interface NomenclaturaPlaguicidaItem {
  ingrediente_key: string;
  agrupador: string | null;
  codigo: string | null;
  fecha_mod: string | null;
}

export interface PaginaNomenclaturaPlaguicidas {
  total: number;
  pagina: number;
  tamano_pagina: number;
  filas: NomenclaturaPlaguicidaItem[];
}

export interface AgrupadorNutrienteItem {
  nombre_key: string;
  producto_agrupado: string | null;
  codigo: string | null;
  fecha_mod: string | null;
}

export interface PaginaAgrupadorNutrientes {
  total: number;
  pagina: number;
  tamano_pagina: number;
  filas: AgrupadorNutrienteItem[];
}

// --- Sección "sin agrupador" (ex pantalla de Excepciones) ---

export interface ResumenSinAgrupadorPlaguicida {
  ingrediente_key: string;
  ingrediente_ejemplo: string | null;
  transacciones: number;
  cantidad_total: number;
  cif_usd_total: number;
  posible_error_captura: boolean;
}

export interface DetalleSinAgrupadorPlaguicida {
  recibointerno: string | null;
  ingrediente_act: string | null;
  ingrediente_key: string | null;
  producto: string | null;
}

export interface PaginaDetalleSinAgrupadorPlaguicidas {
  total: number;
  pagina: number;
  tamano_pagina: number;
  filas: DetalleSinAgrupadorPlaguicida[];
}

export interface SinAgrupadorPlaguicidasResponse {
  resumen: ResumenSinAgrupadorPlaguicida[];
  detalle: PaginaDetalleSinAgrupadorPlaguicidas;
}

export interface ResumenSinAgrupadorNutriente {
  nombre_key: string;
  nombre_ejemplo: string | null;
  transacciones: number;
  cif_dolares_total: number;
  posible_error_captura: boolean;
}

export interface DetalleSinAgrupadorNutriente {
  no_licencia: string | null;
  nombre_comercial: string | null;
  nombre_key: string | null;
}

export interface PaginaDetalleSinAgrupadorNutrientes {
  total: number;
  pagina: number;
  tamano_pagina: number;
  filas: DetalleSinAgrupadorNutriente[];
}

export interface SinAgrupadorNutrientesResponse {
  resumen: ResumenSinAgrupadorNutriente[];
  detalle: PaginaDetalleSinAgrupadorNutrientes;
}

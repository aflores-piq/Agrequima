export interface RankingItem {
  etiqueta: string;
  cif_usd: number;
}

export interface ResumenItem {
  etiqueta: string;
  transacciones: number;
  cif_usd: number;
  porcentaje_del_total: number;
}

export interface ComparacionMensual {
  mes: number;
  cif_usd_actual: number;
  cif_usd_anterior: number;
}

export interface ComparacionAcumuladaMensual {
  mes: number;
  cif_usd_actual_acumulado: number;
  cif_usd_anterior_acumulado: number;
}

export interface PuntoAcumuladoAnual {
  mes: number;
  cif_usd_acumulado: number;
}

export interface SerieAcumuladoAnual {
  anio: number;
  puntos: PuntoAcumuladoAnual[];
}

export interface KpisPlaguicidas {
  cif_total_usd: number;
  cif_total_q: number;
  registros: number;
  ingredientes_activos: number;
}

export interface DetalleTransaccionPlaguicida {
  fecha: string | null;
  recibointerno: string | null;
  aplicacion: string | null;
  importador: string | null;
  producto: string | null;
  ingrediente_act: string | null;
  exportador: string | null;
  origen: string | null;
  institucion: string | null;
}

export interface PaginaDetallePlaguicidas {
  total: number;
  pagina: number;
  tamano_pagina: number;
  filas: DetalleTransaccionPlaguicida[];
}

export interface NombreComercialItem {
  producto: string;
  grupo: string | null;
  aplicacion: string | null;
  importador: string | null;
  origen: string | null;
  cantidad: number;
  unidad_medida: string | null;
  cif_usd: number;
  cif_q: number;
}

export interface GrupoItem {
  grupo: string;
  porcentaje_del_total: number;
  aplicacion_principal: string | null;
  cantidad: number;
  unidad_medida: string | null;
  cif_usd: number;
  cif_q: number;
}

export interface DashboardPlaguicidasResponse {
  anio_actual: number;
  anio_anterior: number;
  mes_seleccionado: number;
  mes_maximo: number;
  kpis: KpisPlaguicidas;
  comparacion_acumulada_mensual: ComparacionAcumuladaMensual[];
  comparacion_mensual: ComparacionMensual[];
  comparativo_acumulado_multianual: SerieAcumuladoAnual[];
  diversificacion_aplicacion: RankingItem[];
  top_ingredientes: RankingItem[];
  top_importadores: RankingItem[];
  top_origenes: ResumenItem[];
  tabla_resumen_importadores: ResumenItem[];
  tabla_nombres_comerciales: NombreComercialItem[];
  tabla_grupos: GrupoItem[];
  detalle: PaginaDetallePlaguicidas;
}

export interface KpisNutrientes {
  cif_total_usd: number;
  cif_total_q: number;
  registros: number;
  empresas: number;
}

export interface DetalleLicenciaNutriente {
  aduana: string | null;
  no_licencia: string | null;
  no_registro: string | null;
  nombre_comercial: string | null;
  empresa_importadora: string | null;
  fecha_emision: string | null;
  unidad: string | null;
}

export interface PaginaDetalleNutrientes {
  total: number;
  pagina: number;
  tamano_pagina: number;
  filas: DetalleLicenciaNutriente[];
}

export interface DashboardNutrientesResponse {
  anio_actual: number;
  anio_anterior: number;
  mes_seleccionado: number;
  mes_maximo: number;
  kpis: KpisNutrientes;
  comparacion_acumulada_mensual: ComparacionAcumuladaMensual[];
  comparacion_mensual: ComparacionMensual[];
  comparativo_acumulado_multianual: SerieAcumuladoAnual[];
  top_formulas: RankingItem[];
  top_paises_origen: ResumenItem[];
  top_aduanas: RankingItem[];
  tabla_resumen_formulas: ResumenItem[];
  detalle: PaginaDetalleNutrientes;
}

export interface DashboardFiltrosPlaguicidas {
  anio?: number;
  mes?: number;
  origen?: string[];
  ingredienteAct?: string[];
  aplicacion?: string[];
  producto?: string[];
  pagina?: number;
  tamanoPagina?: number;
}

export interface DashboardFiltrosNutrientes {
  anio?: number;
  mes?: number;
  nombreComercial?: string[];
  origen?: string[];
  componente?: string[];
  pagina?: number;
  tamanoPagina?: number;
}

export interface OpcionesFiltroPlaguicidas {
  anios: number[];
  origenes: string[];
  aplicaciones: string[];
  ingredientes_activos: string[];
  productos: string[];
}

export interface OpcionesFiltroNutrientes {
  anios: number[];
  paises_origen: string[];
  componentes: string[];
  nombres_comerciales: string[];
}

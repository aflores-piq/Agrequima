export interface ResumenCargaPlaguicidas {
  filas_cargadas: number;
  anios: number[];
  filas_descartadas: number;
  filas_truncadas: number;
  combos_porcentaje: number;
  porcentajes_no_parseables: number;
  filas_sin_agrupador: number;
  nomenclatura_actualizada: boolean;
  claves_nomenclatura_nuevas: number | null;
  estado: "OK" | "ConExcepciones" | "Error";
}

export interface ResumenCargaNutrientes {
  filas_cargadas: number;
  anios: number[];
  filas_truncadas: number;
  filas_descartadas_sin_f: number;
  filas_sin_agrupador: number;
  agrupador_actualizado: boolean;
  claves_agrupador_nuevas: number | null;
  estado: "OK" | "ConExcepciones" | "Error";
}

export interface AuditoriaCargaItem {
  carga_id: number;
  tipo_carga: string;
  nombre_archivo: string | null;
  usuario: string | null;
  fecha_carga: string;
  filas_procesadas: number | null;
  filas_con_excepcion: number | null;
  estado: string;
  mensaje_error: string | null;
}

export interface PaginaAuditoriaCargas {
  total: number;
  pagina: number;
  tamano_pagina: number;
  filas: AuditoriaCargaItem[];
}

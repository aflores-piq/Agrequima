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

export type TipoNombres = "plaguicidas" | "nutrientes";

export interface VarianteNombre {
  clave: string;
  nombre_original: string;
  filas: number;
  cif_usd: number;
}

export interface GrupoNombre {
  nombre_homologado: string;
  confirmada: boolean;
  claves: string[];
  filas: number;
  cif_usd: number;
  puede_separar: boolean;
  fecha_mod: string | null;
  usuario_mod: string | null;
  variantes: VarianteNombre[];
}

export interface PaginaGruposNombres {
  total: number;
  pagina: number;
  tamano_pagina: number;
  pendientes_en_filtro: number;
  total_pendientes: number;
  total_confirmadas: number;
  grupos: GrupoNombre[];
}

export interface NombreNuevo {
  clave: string;
  nombre_ejemplo: string;
  filas: number;
  cif_usd: number;
  variantes: VarianteNombre[];
}

export interface NuevosSinHomologarNombres {
  total: number;
  pagina: number;
  tamano_pagina: number;
  nombres: NombreNuevo[];
}

export interface ResultadoNombres {
  mensaje: string;
  nombre_oficial: string | null;
  claves_afectadas: number;
  grupos_afectados: number;
  filas_sincronizadas: number;
}

export interface FilaExcelNombres {
  fila: number;
  nombre: string;
  nombre_estandar: string;
  clave: string | null;
  estado: string;
  motivo: string | null;
  nombre_actual: string | null;
}

export interface ResultadoExcelNombres {
  aplicado: boolean;
  mensaje: string;
  filas_leidas: number;
  se_uniran: number;
  nuevos: number;
  sin_cambio: number;
  conflictos: number;
  repetidas: number;
  filas_sincronizadas: number;
  detalle: FilaExcelNombres[];
}

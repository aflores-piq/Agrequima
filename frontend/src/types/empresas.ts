export interface OrigenMonto {
  filas: number;
  cif_usd: number;
}

export interface VarianteEmpresa {
  clave: string;
  nombre_original: string;
  plaguicidas: OrigenMonto;
  nutrientes: OrigenMonto;
  cif_total_usd: number;
}

export type OrigenGrupo = "P" | "N" | "ambas" | "";

export interface GrupoEmpresa {
  nombre_homologado: string;
  confirmada: boolean;
  origen: OrigenGrupo;
  claves: string[];
  plaguicidas: OrigenMonto;
  nutrientes: OrigenMonto;
  cif_total_usd: number;
  puede_separar: boolean;
  fecha_mod: string | null;
  usuario_mod: string | null;
  variantes: VarianteEmpresa[];
}

export interface PaginaGruposEmpresas {
  total: number;
  pagina: number;
  tamano_pagina: number;
  pendientes_en_filtro: number;
  total_pendientes: number;
  total_confirmadas: number;
  grupos: GrupoEmpresa[];
}

export interface EmpresaNueva {
  clave: string;
  nombre_ejemplo: string;
  origenes: string[];
  plaguicidas: OrigenMonto;
  nutrientes: OrigenMonto;
  cif_total_usd: number;
  ultima_carga: string | null;
}

export interface NuevasSinHomologarResponse {
  total: number;
  empresas: EmpresaNueva[];
}

export interface ResultadoHomologacion {
  mensaje: string;
  nombre_oficial: string | null;
  claves_afectadas: number;
  grupos_afectados: number;
  filas_sincronizadas: number;
}

export type FiltroEstado = "todas" | "pendientes" | "confirmadas";
export type FiltroOrigen = "todas" | "P" | "N" | "ambas";

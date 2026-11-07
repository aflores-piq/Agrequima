import { apiClient } from "./client";
import type { FiltroEstado } from "../types/empresas";
import type {
  NuevosSinHomologarNombres,
  PaginaGruposNombres,
  ResultadoExcelNombres,
  ResultadoNombres,
  TipoNombres,
} from "../types/nombresComerciales";

const base = (tipo: TipoNombres) => `/admin/nombres-comerciales/${tipo}`;

export async function listarGruposNombres(
  tipo: TipoNombres,
  busqueda: string,
  estado: FiltroEstado,
  pagina = 1,
  tamanoPagina = 25
): Promise<PaginaGruposNombres> {
  const { data } = await apiClient.get<PaginaGruposNombres>(`${base(tipo)}/grupos`, {
    params: { busqueda: busqueda || undefined, estado, pagina, tamano_pagina: tamanoPagina },
  });
  return data;
}

export async function listarNuevosNombres(
  tipo: TipoNombres,
  busqueda: string,
  pagina = 1,
  tamanoPagina = 25
): Promise<NuevosSinHomologarNombres> {
  const { data } = await apiClient.get<NuevosSinHomologarNombres>(`${base(tipo)}/nuevos-sin-homologar`, {
    params: { busqueda: busqueda || undefined, pagina, tamano_pagina: tamanoPagina },
  });
  return data;
}

export async function unirNombres(tipo: TipoNombres, claves: string[], nombreOficial: string): Promise<ResultadoNombres> {
  const { data } = await apiClient.post<ResultadoNombres>(`${base(tipo)}/unir`, { claves, nombre_oficial: nombreOficial });
  return data;
}

export async function renombrarNombre(tipo: TipoNombres, nombreActual: string, nombreNuevo: string): Promise<ResultadoNombres> {
  const { data } = await apiClient.put<ResultadoNombres>(`${base(tipo)}/renombrar`, {
    nombre_actual: nombreActual,
    nombre_nuevo: nombreNuevo,
  });
  return data;
}

export async function separarNombre(tipo: TipoNombres, clave: string): Promise<ResultadoNombres> {
  const { data } = await apiClient.post<ResultadoNombres>(`${base(tipo)}/separar`, { clave });
  return data;
}

export async function confirmarNombres(tipo: TipoNombres, nombres: string[]): Promise<ResultadoNombres> {
  const { data } = await apiClient.post<ResultadoNombres>(`${base(tipo)}/confirmar`, { nombres });
  return data;
}

export async function confirmarPendientesNombres(tipo: TipoNombres, busqueda: string): Promise<ResultadoNombres> {
  const { data } = await apiClient.post<ResultadoNombres>(`${base(tipo)}/confirmar-pendientes`, { busqueda: busqueda || null });
  return data;
}

export async function asignarNombresNuevos(
  tipo: TipoNombres,
  claves: string[],
  nombreGrupo: string,
  grupoNuevo: boolean
): Promise<ResultadoNombres> {
  const { data } = await apiClient.post<ResultadoNombres>(`${base(tipo)}/nuevos-sin-homologar/asignar`, {
    claves,
    nombre_grupo: nombreGrupo,
    grupo_nuevo: grupoNuevo,
  });
  return data;
}

export async function cargarExcelNombres(tipo: TipoNombres, archivo: File, aplicar: boolean): Promise<ResultadoExcelNombres> {
  const form = new FormData();
  form.append("archivo", archivo);
  const { data } = await apiClient.post<ResultadoExcelNombres>(`${base(tipo)}/excel`, form, { params: { aplicar } });
  return data;
}

import { apiClient } from "./client";
import type {
  FiltroEstado,
  FiltroOrigen,
  NuevasSinHomologarResponse,
  PaginaGruposEmpresas,
  ResultadoHomologacion,
} from "../types/empresas";

export async function listarGruposEmpresas(
  busqueda: string,
  estado: FiltroEstado,
  origen: FiltroOrigen,
  pagina = 1,
  tamanoPagina = 25
): Promise<PaginaGruposEmpresas> {
  const { data } = await apiClient.get<PaginaGruposEmpresas>("/admin/empresas/grupos", {
    params: { busqueda: busqueda || undefined, estado, origen, pagina, tamano_pagina: tamanoPagina },
  });
  return data;
}

export async function obtenerNuevasSinHomologar(): Promise<NuevasSinHomologarResponse> {
  const { data } = await apiClient.get<NuevasSinHomologarResponse>("/admin/empresas/nuevas-sin-homologar");
  return data;
}

export async function unirEmpresas(claves: string[], nombreOficial: string): Promise<ResultadoHomologacion> {
  const { data } = await apiClient.post<ResultadoHomologacion>("/admin/empresas/unir", {
    claves,
    nombre_oficial: nombreOficial,
  });
  return data;
}

export async function renombrarGrupoEmpresa(nombreActual: string, nombreNuevo: string): Promise<ResultadoHomologacion> {
  const { data } = await apiClient.put<ResultadoHomologacion>("/admin/empresas/renombrar", {
    nombre_actual: nombreActual,
    nombre_nuevo: nombreNuevo,
  });
  return data;
}

export async function separarVariante(clave: string): Promise<ResultadoHomologacion> {
  const { data } = await apiClient.post<ResultadoHomologacion>("/admin/empresas/separar", { clave });
  return data;
}

export async function confirmarGrupos(nombres: string[]): Promise<ResultadoHomologacion> {
  const { data } = await apiClient.post<ResultadoHomologacion>("/admin/empresas/confirmar", { nombres });
  return data;
}

export async function confirmarPendientes(busqueda: string, origen: FiltroOrigen): Promise<ResultadoHomologacion> {
  const { data } = await apiClient.post<ResultadoHomologacion>("/admin/empresas/confirmar-pendientes", {
    busqueda: busqueda || null,
    origen,
  });
  return data;
}

export async function asignarNuevas(
  claves: string[],
  nombreGrupo: string,
  grupoNuevo: boolean
): Promise<ResultadoHomologacion> {
  const { data } = await apiClient.post<ResultadoHomologacion>("/admin/empresas/nuevas-sin-homologar/asignar", {
    claves,
    nombre_grupo: nombreGrupo,
    grupo_nuevo: grupoNuevo,
  });
  return data;
}

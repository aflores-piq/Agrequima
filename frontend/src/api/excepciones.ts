import { apiClient } from "./client";
import type {
  ActualizarAgrupadorResponse,
  ExcepcionesNutrientesResponse,
  ExcepcionesPlaguicidasResponse,
} from "../types/excepciones";

export async function obtenerExcepcionesPlaguicidas(
  pagina = 1,
  tamanoPagina = 50
): Promise<ExcepcionesPlaguicidasResponse> {
  const { data } = await apiClient.get<ExcepcionesPlaguicidasResponse>(
    "/admin/excepciones/plaguicidas",
    { params: { pagina, tamano_pagina: tamanoPagina } }
  );
  return data;
}

export async function obtenerExcepcionesNutrientes(
  pagina = 1,
  tamanoPagina = 50
): Promise<ExcepcionesNutrientesResponse> {
  const { data } = await apiClient.get<ExcepcionesNutrientesResponse>(
    "/admin/excepciones/nutrientes",
    { params: { pagina, tamano_pagina: tamanoPagina } }
  );
  return data;
}

export async function actualizarAgrupadorPlaguicidas(
  ingredienteKey: string,
  agrupador: string
): Promise<ActualizarAgrupadorResponse> {
  const { data } = await apiClient.patch<ActualizarAgrupadorResponse>(
    "/admin/excepciones/plaguicidas/agrupador",
    { ingrediente_key: ingredienteKey, agrupador }
  );
  return data;
}

export async function actualizarAgrupadorNutrientes(
  nombreKey: string,
  agrupador: string
): Promise<ActualizarAgrupadorResponse> {
  const { data } = await apiClient.patch<ActualizarAgrupadorResponse>(
    "/admin/excepciones/nutrientes/agrupador",
    { nombre_key: nombreKey, agrupador }
  );
  return data;
}

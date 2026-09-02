import { apiClient } from "./client";
import type {
  AgrupadorNutrienteItem,
  PaginaAgrupadorNutrientes,
  PaginaNomenclaturaPlaguicidas,
  SinAgrupadorNutrientesResponse,
  SinAgrupadorPlaguicidasResponse,
} from "../types/nomenclatura";

export async function listarNomenclaturaPlaguicidas(
  busqueda: string,
  pagina = 1,
  tamanoPagina = 50
): Promise<PaginaNomenclaturaPlaguicidas> {
  const { data } = await apiClient.get<PaginaNomenclaturaPlaguicidas>(
    "/admin/nomenclatura/plaguicidas",
    { params: { busqueda: busqueda || undefined, pagina, tamano_pagina: tamanoPagina } }
  );
  return data;
}

export async function obtenerSinAgrupadorPlaguicidas(
  pagina = 1,
  tamanoPagina = 50
): Promise<SinAgrupadorPlaguicidasResponse> {
  const { data } = await apiClient.get<SinAgrupadorPlaguicidasResponse>(
    "/admin/nomenclatura/plaguicidas/sin-agrupador",
    { params: { pagina, tamano_pagina: tamanoPagina } }
  );
  return data;
}

export async function actualizarNomenclaturaPlaguicida(
  ingredienteKey: string,
  agrupador: string,
  codigo: string | null
) {
  const { data } = await apiClient.put(
    `/admin/nomenclatura/plaguicidas/${encodeURIComponent(ingredienteKey)}`,
    { agrupador, codigo }
  );
  return data;
}

export async function listarAgrupadorNutrientes(
  busqueda: string,
  pagina = 1,
  tamanoPagina = 50
): Promise<PaginaAgrupadorNutrientes> {
  const { data } = await apiClient.get<PaginaAgrupadorNutrientes>("/admin/nomenclatura/nutrientes", {
    params: { busqueda: busqueda || undefined, pagina, tamano_pagina: tamanoPagina },
  });
  return data;
}

export async function obtenerSinAgrupadorNutrientes(
  pagina = 1,
  tamanoPagina = 50
): Promise<SinAgrupadorNutrientesResponse> {
  const { data } = await apiClient.get<SinAgrupadorNutrientesResponse>(
    "/admin/nomenclatura/nutrientes/sin-agrupador",
    { params: { pagina, tamano_pagina: tamanoPagina } }
  );
  return data;
}

export async function actualizarAgrupadorNutriente(
  nombreKey: string,
  productoAgrupado: string,
  codigo: string | null
): Promise<AgrupadorNutrienteItem> {
  const { data } = await apiClient.put<AgrupadorNutrienteItem>(
    `/admin/nomenclatura/nutrientes/${encodeURIComponent(nombreKey)}`,
    { producto_agrupado: productoAgrupado, codigo }
  );
  return data;
}

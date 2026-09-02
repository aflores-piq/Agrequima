import { apiClient } from "./client";
import type {
  DashboardFiltrosNutrientes,
  DashboardFiltrosPlaguicidas,
  DashboardNutrientesResponse,
  DashboardPlaguicidasResponse,
  OpcionesFiltroNutrientes,
  OpcionesFiltroPlaguicidas,
} from "../types/dashboard";

export async function obtenerOpcionesPlaguicidas(): Promise<OpcionesFiltroPlaguicidas> {
  const { data } = await apiClient.get<OpcionesFiltroPlaguicidas>("/dashboard/plaguicidas/opciones");
  return data;
}

export async function obtenerOpcionesNutrientes(): Promise<OpcionesFiltroNutrientes> {
  const { data } = await apiClient.get<OpcionesFiltroNutrientes>("/dashboard/nutrientes/opciones");
  return data;
}

export async function obtenerDashboardPlaguicidas(
  filtros: DashboardFiltrosPlaguicidas
): Promise<DashboardPlaguicidasResponse> {
  const { data } = await apiClient.get<DashboardPlaguicidasResponse>("/dashboard/plaguicidas", {
    params: {
      anio: filtros.anio,
      mes: filtros.mes,
      origen: filtros.origen?.length ? filtros.origen : undefined,
      ingrediente_act: filtros.ingredienteAct?.length ? filtros.ingredienteAct : undefined,
      aplicacion: filtros.aplicacion?.length ? filtros.aplicacion : undefined,
      producto: filtros.producto?.length ? filtros.producto : undefined,
      pagina: filtros.pagina ?? 1,
      tamano_pagina: filtros.tamanoPagina ?? 50,
    },
  });
  return data;
}

export async function obtenerDashboardNutrientes(
  filtros: DashboardFiltrosNutrientes
): Promise<DashboardNutrientesResponse> {
  const { data } = await apiClient.get<DashboardNutrientesResponse>("/dashboard/nutrientes", {
    params: {
      anio: filtros.anio,
      mes: filtros.mes,
      nombre_comercial: filtros.nombreComercial?.length ? filtros.nombreComercial : undefined,
      nombre_comercial_raw: filtros.nombreComercialRaw?.length ? filtros.nombreComercialRaw : undefined,
      origen: filtros.origen?.length ? filtros.origen : undefined,
      componente: filtros.componente?.length ? filtros.componente : undefined,
      pagina: filtros.pagina ?? 1,
      tamano_pagina: filtros.tamanoPagina ?? 50,
    },
  });
  return data;
}

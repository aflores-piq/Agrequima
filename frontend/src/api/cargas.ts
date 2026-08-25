import { apiClient } from "./client";
import type {
  PaginaAuditoriaCargas,
  ResumenCargaNutrientes,
  ResumenCargaPlaguicidas,
} from "../types/cargas";

export async function cargarPlaguicidas(archivoImportaciones: File): Promise<ResumenCargaPlaguicidas> {
  const formData = new FormData();
  formData.append("archivo_importaciones", archivoImportaciones);
  const { data } = await apiClient.post<ResumenCargaPlaguicidas>(
    "/admin/cargas/plaguicidas",
    formData
  );
  return data;
}

export async function cargarNutrientes(archivoNutrientes: File): Promise<ResumenCargaNutrientes> {
  const formData = new FormData();
  formData.append("archivo_nutrientes", archivoNutrientes);
  const { data } = await apiClient.post<ResumenCargaNutrientes>(
    "/admin/cargas/nutrientes",
    formData
  );
  return data;
}

export async function obtenerHistorialCargas(
  tipo?: string,
  pagina = 1,
  tamanoPagina = 20
): Promise<PaginaAuditoriaCargas> {
  const { data } = await apiClient.get<PaginaAuditoriaCargas>("/admin/cargas/historial", {
    params: { tipo, pagina, tamano_pagina: tamanoPagina },
  });
  return data;
}

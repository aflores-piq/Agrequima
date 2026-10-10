import { apiClient } from "./client";
import type { BitacoraIngresosResponse } from "../types/bitacora";

export async function obtenerBitacoraIngresos(empresa?: string, usuario?: string): Promise<BitacoraIngresosResponse> {
  const { data } = await apiClient.get<BitacoraIngresosResponse>("/admin/bitacora-ingresos", {
    params: { empresa, usuario },
  });
  return data;
}

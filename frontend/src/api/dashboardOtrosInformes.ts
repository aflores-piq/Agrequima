import { apiClient } from "./client";
import type { CuotasAsociadosResponse } from "../types/dashboardOtrosInformes";

export async function obtenerCuotasAsociados(anio?: number): Promise<CuotasAsociadosResponse> {
  const { data } = await apiClient.get<CuotasAsociadosResponse>(
    "/dashboard/financiero/cuotas-asociados",
    { params: { anio } }
  );
  return data;
}

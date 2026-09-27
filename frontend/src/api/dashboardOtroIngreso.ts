import { apiClient } from "./client";
import type { OtroIngresoResponse } from "../types/dashboardOtroIngreso";

export async function obtenerOtroIngreso(anio?: number): Promise<OtroIngresoResponse> {
  const { data } = await apiClient.get<OtroIngresoResponse>("/dashboard/financiero/otros-ingresos", {
    params: { anio },
  });
  return data;
}

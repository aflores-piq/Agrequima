import { apiClient } from "./client";
import type { DashboardFinancieroResponse } from "../types/dashboardFinanciero";

export async function obtenerDashboardFinanciero(
  anio?: number,
  mes?: number
): Promise<DashboardFinancieroResponse> {
  const { data } = await apiClient.get<DashboardFinancieroResponse>(
    "/dashboard/financiero/estados-financieros",
    { params: { anio, mes } }
  );
  return data;
}

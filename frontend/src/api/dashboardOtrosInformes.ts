import { apiClient } from "./client";
import type { CuotasAsociadosResponse, EjecucionGastosResponse } from "../types/dashboardOtrosInformes";

export async function obtenerCuotasAsociados(anio?: number, mes?: number): Promise<CuotasAsociadosResponse> {
  const { data } = await apiClient.get<CuotasAsociadosResponse>(
    "/dashboard/financiero/cuotas-asociados",
    { params: { anio, mes } }
  );
  return data;
}

export async function obtenerEjecucionGastosMes(anio?: number, mes?: number): Promise<EjecucionGastosResponse> {
  const { data } = await apiClient.get<EjecucionGastosResponse>(
    "/dashboard/financiero/ejecucion-gastos-mes",
    { params: { anio, mes } }
  );
  return data;
}

export async function obtenerEjecucionGastosAcumulado(anio?: number, mes?: number): Promise<EjecucionGastosResponse> {
  const { data } = await apiClient.get<EjecucionGastosResponse>(
    "/dashboard/financiero/ejecucion-gastos-acumulado",
    { params: { anio, mes } }
  );
  return data;
}

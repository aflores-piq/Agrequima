import { apiClient } from "./client";
import type {
  ConciliacionBancariaResponse,
  CuotasAsociadosResponse,
  EjecucionGastosResponse,
  FlujoCajaResponse,
} from "../types/dashboardOtrosInformes";

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

export async function obtenerConciliacionBancaria(anio?: number, mes?: number): Promise<ConciliacionBancariaResponse> {
  const { data } = await apiClient.get<ConciliacionBancariaResponse>(
    "/dashboard/financiero/conciliacion-bancaria",
    { params: { anio, mes } }
  );
  return data;
}

export async function obtenerFlujoCaja(anio?: number, mes?: number): Promise<FlujoCajaResponse> {
  const { data } = await apiClient.get<FlujoCajaResponse>("/dashboard/financiero/flujo-caja", { params: { anio, mes } });
  return data;
}

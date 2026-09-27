import { apiClient } from "./client";
import type {
  ComparativoEjecutadoResponse,
  ConciliacionBancariaResponse,
  CuotasAsociadosResponse,
  EjecucionGastosResponse,
  EjecucionVsPresupuestoResponse,
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

export async function obtenerEjecucionVsPresupuesto(anio?: number, mes?: number): Promise<EjecucionVsPresupuestoResponse> {
  const { data } = await apiClient.get<EjecucionVsPresupuestoResponse>(
    "/dashboard/financiero/ejecucion-vs-presupuesto",
    { params: { anio, mes } }
  );
  return data;
}

export async function obtenerEjecucionVsPresupuestoAcumulado(anio?: number, mes?: number): Promise<EjecucionVsPresupuestoResponse> {
  const { data } = await apiClient.get<EjecucionVsPresupuestoResponse>(
    "/dashboard/financiero/ejecucion-vs-presupuesto-acumulado",
    { params: { anio, mes } }
  );
  return data;
}

export async function obtenerComparativoEjecutado(anio?: number, mes?: number): Promise<ComparativoEjecutadoResponse> {
  const { data } = await apiClient.get<ComparativoEjecutadoResponse>(
    "/dashboard/financiero/comparativo-ejecutado",
    { params: { anio, mes } }
  );
  return data;
}

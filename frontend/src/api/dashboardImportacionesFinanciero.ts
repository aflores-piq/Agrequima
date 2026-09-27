import { apiClient } from "./client";
import type {
  ContribucionMillarResponse,
  ImportacionComparativoResponse,
  IngresosImportacionResponse,
  KilolitrosResponse,
} from "../types/dashboardImportacionesFinanciero";

export async function obtenerIngresosImportacion(anio?: number): Promise<IngresosImportacionResponse> {
  const { data } = await apiClient.get<IngresosImportacionResponse>("/dashboard/financiero/importaciones/ingresos", {
    params: { anio },
  });
  return data;
}

export async function obtenerIngresosImportacionComparativo(anio?: number): Promise<ImportacionComparativoResponse> {
  const { data } = await apiClient.get<ImportacionComparativoResponse>(
    "/dashboard/financiero/importaciones/comparativo",
    { params: { anio } }
  );
  return data;
}

export async function obtenerKilolitros(anio?: number, mes?: number): Promise<KilolitrosResponse> {
  const { data } = await apiClient.get<KilolitrosResponse>("/dashboard/financiero/importaciones/kilolitros", {
    params: { anio, mes },
  });
  return data;
}

export async function obtenerContribucionMillar(anio?: number, mes?: number): Promise<ContribucionMillarResponse> {
  const { data } = await apiClient.get<ContribucionMillarResponse>(
    "/dashboard/financiero/importaciones/contribucion-millar",
    { params: { anio, mes } }
  );
  return data;
}

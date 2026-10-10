import { apiClient } from "./client";

export interface UltimaActualizacionResponse {
  /** Hora de Guatemala, sin zona ("2026-10-10T02:05:00"); null = todavía no hay ninguna sincronización registrada. */
  ultima_actualizacion: string | null;
}

export async function obtenerUltimaActualizacion(): Promise<UltimaActualizacionResponse> {
  const { data } = await apiClient.get<UltimaActualizacionResponse>("/sistema/ultima-actualizacion");
  return data;
}

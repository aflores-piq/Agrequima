import { apiClient } from "./client";
import type { ListaAvisos, ResultadoLeer } from "../types/avisos";

export async function obtenerAvisos(): Promise<ListaAvisos> {
  const { data } = await apiClient.get<ListaAvisos>("/avisos");
  return data;
}

export async function marcarAvisoLeido(avisoId: number): Promise<ResultadoLeer> {
  const { data } = await apiClient.post<ResultadoLeer>(`/avisos/${avisoId}/leido`);
  return data;
}

export async function marcarTodosLeidos(): Promise<ResultadoLeer> {
  const { data } = await apiClient.post<ResultadoLeer>("/avisos/leer-todos");
  return data;
}

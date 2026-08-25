import { apiClient } from "./client";
import type { PreferenciasResponse, Tema, TokenResponse } from "../types/auth";

export async function login(nombreUsuario: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", {
    nombre_usuario: nombreUsuario,
    password,
  });
  return data;
}

export async function actualizarPreferencia(tema: Tema): Promise<PreferenciasResponse> {
  const { data } = await apiClient.patch<PreferenciasResponse>("/auth/preferencias", { tema });
  return data;
}

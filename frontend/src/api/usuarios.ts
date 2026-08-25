import { apiClient } from "./client";
import type { UsuarioCreate, UsuarioOut, UsuarioUpdate } from "../types/usuarios";

export async function listarUsuarios(): Promise<UsuarioOut[]> {
  const { data } = await apiClient.get<UsuarioOut[]>("/admin/usuarios");
  return data;
}

export async function crearUsuario(payload: UsuarioCreate): Promise<UsuarioOut> {
  const { data } = await apiClient.post<UsuarioOut>("/admin/usuarios", payload);
  return data;
}

export async function actualizarUsuario(
  usuarioId: number,
  payload: UsuarioUpdate
): Promise<UsuarioOut> {
  const { data } = await apiClient.patch<UsuarioOut>(`/admin/usuarios/${usuarioId}`, payload);
  return data;
}

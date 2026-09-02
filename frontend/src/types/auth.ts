export type Rol = "Administrador" | "Usuario" | "Administrador de Usuarios";
export type Tema = "Claro" | "Oscuro";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  rol: Rol;
  puede_exportar: boolean;
  tema: Tema;
}

export interface PreferenciasResponse {
  tema: Tema;
}

export interface UsuarioSesion {
  usuarioId: number;
  nombreUsuario: string;
  rol: Rol;
}

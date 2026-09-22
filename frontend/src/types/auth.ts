export type Rol = "Administrador" | "Usuario" | "Administrador de Usuarios";
export type Tema = "Claro" | "Oscuro";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  rol: Rol;
  puede_exportar: boolean;
  tema: Tema;
  acceso_importaciones: boolean;
  acceso_financiero: boolean;
  acceso_indicadores: boolean;
  aviso_legal_aceptado: boolean;
}

export interface PreferenciasResponse {
  tema: Tema;
}

export interface AvisoLegalResponse {
  aceptado: boolean;
  fecha_aceptacion: string | null;
}

export interface UsuarioSesion {
  usuarioId: number;
  nombreUsuario: string;
  rol: Rol;
}

import type { Rol } from "./auth";

export interface UsuarioOut {
  usuario_id: number;
  nombre_usuario: string;
  nombre_completo: string | null;
  email: string | null;
  rol: Rol;
  activo: boolean;
  puede_exportar: boolean;
  fecha_creacion: string | null;
  ultimo_login: string | null;
}

export interface UsuarioCreate {
  nombre_usuario: string;
  password: string;
  nombre_completo?: string;
  email?: string;
  rol: Rol;
  puede_exportar?: boolean;
}

export interface UsuarioUpdate {
  rol?: Rol;
  activo?: boolean;
  puede_exportar?: boolean;
}

export interface CambiarPasswordRequest {
  password: string;
}

import axios from "axios";

// Relativo al dominio actual por defecto (sin localhost fijo) -- así el
// mismo build sirve para cualquier dominio donde se despliegue la app;
// en desarrollo, VITE_API_URL (.env del frontend) apunta directo al
// backend en :8001/api, ya que Vite y el backend corren en puertos
// distintos.
const API_URL = import.meta.env.VITE_API_URL ?? "/api";

// Serializador de params propio: axios por defecto manda los arreglos
// como "clave[]=a&clave[]=b" (bracket), pero FastAPI espera la clave
// repetida sin corchetes ("clave=a&clave=b") para poblar un
// `list[str] = Query(None)` — necesario para los filtros de selección
// múltiple del dashboard.
export const apiClient = axios.create({
  baseURL: API_URL,
  paramsSerializer: {
    serialize: (params: Record<string, unknown>) => {
      const usp = new URLSearchParams();
      Object.entries(params).forEach(([clave, valor]) => {
        if (valor === undefined || valor === null) return;
        if (Array.isArray(valor)) {
          valor.forEach((v) => {
            if (v !== undefined && v !== null) usp.append(clave, String(v));
          });
        } else {
          usp.append(clave, String(valor));
        }
      });
      return usp.toString();
    },
  },
});

const TOKEN_STORAGE_KEY = "agrequima_token";

interface JwtPayload {
  sub: string;
  username: string;
  rol: string;
  puede_exportar: boolean;
  nombre_completo: string | null;
  email: string | null;
  exp: number;
}

function decodificarToken(token: string): JwtPayload | null {
  try {
    const [, payload] = token.split(".");
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

export function guardarSesion(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export interface Sesion {
  token: string;
  usuarioId: number;
  nombreUsuario: string;
  nombreCompleto: string | null;
  email: string | null;
  rol: string;
  puedeExportar: boolean;
}

export function leerSesion(): Sesion | null {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (!token) return null;

  const payload = decodificarToken(token);
  if (!payload) return null;

  if (payload.exp * 1000 < Date.now()) {
    borrarSesion();
    return null;
  }

  return {
    token,
    usuarioId: Number(payload.sub),
    nombreUsuario: payload.username,
    nombreCompleto: payload.nombre_completo,
    email: payload.email,
    rol: payload.rol,
    puedeExportar: payload.puede_exportar,
  };
}

export function borrarSesion(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

apiClient.interceptors.request.use((config) => {
  const sesion = leerSesion();
  if (sesion) {
    config.headers.Authorization = `Bearer ${sesion.token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      borrarSesion();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function mensajeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detalle = error.response?.data?.detail;
    if (typeof detalle === "string") return detalle;
    if (Array.isArray(detalle)) {
      return detalle.map((d) => d.msg ?? JSON.stringify(d)).join("; ");
    }
    if (error.message) return error.message;
  }
  return "Ocurrió un error inesperado.";
}

import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

// A dónde mandar a alguien que no tiene permiso para ver la ruta actual
// (o que recién inició sesión) — cada rol tiene una "home" distinta.
export function destinoPorRol(rol: string): string {
  if (rol === "Administrador") return "/admin";
  if (rol === "Administrador de Usuarios") return "/admin/usuarios";
  return "/app";
}

export function RequireRole({ roles, children }: { roles: string[]; children: ReactNode }) {
  const { sesion } = useAuth();
  const location = useLocation();

  if (!sesion) {
    return <Navigate to="/login" state={{ desde: location.pathname }} replace />;
  }

  if (!roles.includes(sesion.rol)) {
    return <Navigate to={destinoPorRol(sesion.rol)} replace />;
  }

  return <>{children}</>;
}

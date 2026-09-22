import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { AvisoLegalOverlay } from "../components/AvisoLegalOverlay";

// A dónde mandar a alguien que no tiene permiso para ver la ruta actual
// (o que recién inició sesión) — cada rol tiene una "home" distinta.
export function destinoPorRol(rol: string): string {
  if (rol === "Administrador") return "/admin";
  if (rol === "Administrador de Usuarios") return "/admin/usuarios";
  return "/app";
}

export function RequireRole({ roles, children }: { roles: string[]; children: ReactNode }) {
  const { sesion, avisoLegalPendiente } = useAuth();
  const location = useLocation();

  if (!sesion) {
    return <Navigate to="/login" state={{ desde: location.pathname }} replace />;
  }

  if (!roles.includes(sesion.rol)) {
    return <Navigate to={destinoPorRol(sesion.rol)} replace />;
  }

  // Bloquea CUALQUIER ruta protegida (dashboards y /admin por igual)
  // hasta que el usuario acepta el aviso legal -- una sola vez por
  // usuario, ver AvisoLegalOverlay/AuthContext.
  if (avisoLegalPendiente) {
    return <AvisoLegalOverlay />;
  }

  return <>{children}</>;
}

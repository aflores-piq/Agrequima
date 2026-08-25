import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function RequireRole({ roles, children }: { roles: string[]; children: ReactNode }) {
  const { sesion } = useAuth();
  const location = useLocation();

  if (!sesion) {
    return <Navigate to="/login" state={{ desde: location.pathname }} replace />;
  }

  if (!roles.includes(sesion.rol)) {
    const destino = sesion.rol === "Administrador" ? "/admin" : "/app";
    return <Navigate to={destino} replace />;
  }

  return <>{children}</>;
}

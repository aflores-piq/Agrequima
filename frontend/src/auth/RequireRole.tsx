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
  // hasta que el usuario acepta el aviso legal -- en cada inicio de
  // sesión, ver AvisoLegalOverlay/AuthContext.
  if (avisoLegalPendiente) {
    return <AvisoLegalOverlay />;
  }

  return <>{children}</>;
}

/** Igual que RequireRole pero por MÓDULO (accesoImportaciones/
 * accesoFinanciero/accesoIndicadores) en vez de por rol -- el rol ya
 * decide si se puede entrar a /app en general, esto decide si se puede
 * entrar a la pantalla de UN sistema puntual dentro de /app. Se anida
 * DENTRO de cada <Route> de ese sistema (no reemplaza a RequireRole,
 * que sigue envolviendo todo /app para rol + aviso legal).
 *
 * Si el usuario no tiene el acceso, redirige a /app SIN montar la
 * página hija -- ésta nunca se renderiza, así que nunca corre su
 * `useEffect` ni pide datos al backend -- y sin mostrar ningún texto
 * que nombre el módulo (un <Navigate> no renderiza nada visible). Un
 * usuario sin el módulo no tiene forma de enterarse, ni por URL directa
 * ni por mensaje de error, de que ese módulo existe. */
export function RequireModulo({
  modulo,
  children,
}: {
  modulo: "importaciones" | "financiero" | "indicadores";
  children: ReactNode;
}) {
  const { sesion } = useAuth();

  if (!sesion) {
    return <Navigate to="/login" replace />;
  }

  const tieneAcceso =
    modulo === "importaciones"
      ? sesion.accesoImportaciones
      : modulo === "financiero"
        ? sesion.accesoFinanciero
        : sesion.accesoIndicadores;

  if (!tieneAcceso) {
    return <Navigate to="/app" replace />;
  }

  return <>{children}</>;
}

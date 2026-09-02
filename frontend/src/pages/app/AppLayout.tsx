import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Header } from "../../components/layout/Header";

const linkBase =
  "rounded-tremor-small px-3 py-1.5 text-sm font-medium transition-colors";

export function AppLayout() {
  const { sesion } = useAuth();

  return (
    <div className="min-h-screen bg-app">
      <Header
        nav={
          <nav className="flex items-center gap-1">
            <NavLink
              to="/app/plaguicidas"
              className={({ isActive }) =>
                `${linkBase} ${isActive ? "bg-teal-500/15 text-teal-600 dark:text-teal-300" : "text-ink-muted hover:text-ink"}`
              }
            >
              Plaguicidas
            </NavLink>
            <NavLink
              to="/app/nutrientes"
              className={({ isActive }) =>
                `${linkBase} ${isActive ? "bg-orange-500/15 text-orange-600 dark:text-orange-300" : "text-ink-muted hover:text-ink"}`
              }
            >
              Nutrientes
            </NavLink>
            {(sesion?.rol === "Administrador" || sesion?.rol === "Administrador de Usuarios") && (
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  `${linkBase} ${isActive ? "bg-accent-subtle text-accent-emphasis" : "text-ink-muted hover:text-ink"}`
                }
              >
                Administración
              </NavLink>
            )}
          </nav>
        }
      />
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

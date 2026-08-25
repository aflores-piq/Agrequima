import { NavLink, Outlet } from "react-router-dom";
import { Header } from "../../components/layout/Header";

const items = [
  { to: "/admin/cargas/plaguicidas", label: "Carga de plaguicidas" },
  { to: "/admin/cargas/nutrientes", label: "Carga de nutrientes" },
  { to: "/admin/nomenclatura/plaguicidas", label: "Nomenclatura plaguicidas" },
  { to: "/admin/nomenclatura/nutrientes", label: "Agrupador nutrientes" },
  { to: "/admin/excepciones", label: "Excepciones" },
  { to: "/admin/usuarios", label: "Usuarios" },
];

export function AdminLayout() {
  return (
    <div className="min-h-screen bg-app">
      <Header />
      <div className="flex">
        <aside className="hidden w-64 shrink-0 border-r border-line bg-surface p-4 sm:block">
          <div className="mb-6 px-2">
            <p className="text-sm font-semibold tracking-wide text-ink">AGREQUIMA</p>
            <p className="text-xs text-ink-faint">Administración</p>
          </div>
          <nav className="space-y-1">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `block rounded-tremor-small px-3 py-2 text-sm transition-colors ${
                    isActive
                      ? "bg-accent-subtle text-accent-emphasis"
                      : "text-ink-muted hover:bg-surface-hover hover:text-ink"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-6 border-t border-line pt-4">
            <NavLink to="/app" className="block px-3 py-2 text-sm text-ink-muted hover:text-ink">
              Ver dashboards →
            </NavLink>
          </div>
        </aside>

        <div className="flex-1">
          <nav className="flex gap-1 overflow-x-auto border-b border-line bg-surface px-4 py-2 sm:hidden">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `shrink-0 rounded-tremor-small px-3 py-1.5 text-xs transition-colors ${
                    isActive ? "bg-accent-subtle text-accent-emphasis" : "text-ink-muted"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <main className="p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

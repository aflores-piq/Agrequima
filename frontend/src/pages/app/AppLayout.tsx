import { Outlet, useLocation } from "react-router-dom";
import { Header } from "../../components/layout/Header";
import { Sidebar } from "../../components/layout/Sidebar";

/** Financiero e Importaciones (Plaguicidas/Nutrientes) comparten este
 * layout -- antes navegaban por un nav superior (Plaguicidas/
 * Nutrientes/Financiero/Administración), reemplazado por el sidebar
 * estilo Power BI (ver Sidebar.tsx), que decide qué secciones mostrar
 * con los mismos flags de sesión (accesoFinanciero/accesoImportaciones/
 * rol) que ya usaba el nav superior -- ningún sistema de permisos nuevo.
 *
 * Financiero usa un `max-w` más ancho (1658px, medido del .pbix) que
 * Plaguicidas/Nutrientes (1280px, sin tocar) -- ver DashboardFinancieroPage,
 * que ya NO se "escapa" de este contenedor por su cuenta (como hacía
 * antes con un truco de viewport): ahora que existe un sidebar real,
 * calcular el ancho relativo al viewport crudo quedaba mal (el sidebar
 * cambia de ancho al hacer hover, y ese truco no lo tenía en cuenta) --
 * `main` ya excluye el sidebar automáticamente por ser hermanos flex,
 * así que centrar ACÁ, relativo al espacio real que le queda a `main`,
 * es correcto sin importar si el sidebar está expandido o no.
 *
 * Financiero también tiene su propio fondo (--color-financiero-app, ver
 * index.css): gris neutro fijo #1c1c1c en oscuro (medido de la captura
 * real de Power BI, distinto del slate-950 general de la app), igual
 * que bg-app en claro -- Plaguicidas/Nutrientes siguen con bg-app sin
 * cambios. */
export function AppLayout() {
  const location = useLocation();
  const esFinanciero = location.pathname.startsWith("/app/financiero");

  return (
    <div
      className={`flex min-h-screen ${esFinanciero ? "" : "bg-app"}`}
      style={esFinanciero ? { backgroundColor: "rgb(var(--color-financiero-app))" } : undefined}
    >
      <Sidebar />
      <div className="min-w-0 flex-1">
        <Header />
        <main className={`mx-auto px-4 py-6 ${esFinanciero ? "max-w-[1658px]" : "max-w-7xl"}`}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

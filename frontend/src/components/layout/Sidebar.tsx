import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

interface NodoMenu {
  id: string;
  titulo: string;
  /** Con hijos = colapsable (sección/subsección). Sin hijos = ítem
   * final: con href navega a una página real, sin href todavía no
   * existe esa página en la app (ver captura de referencia del menú
   * real de Power BI, docs/legacy/Financiero_capturas/) -- se muestra
   * en la estructura para que se vea completa, pero no navega a nada
   * inventado. */
  href?: string;
  hijos?: NodoMenu[];
}

// Financiero e Importaciones son HERMANAS de primer nivel -- antes
// estaban las 4 categorías de Financiero mezcladas al mismo nivel que
// Importaciones, incorrecto. Estados financieros/Otros informes
// financieros/Presupuestos/Otros ingresos son sub-secciones DENTRO de
// Financiero, cada una colapsable por separado.
const MENU_FINANCIERO: NodoMenu = {
  id: "financiero",
  titulo: "Financiero",
  hijos: [
    {
      id: "estados-financieros",
      titulo: "Estados financieros",
      hijos: [
        { id: "ef-mensual", titulo: "Estado de ingresos y desembolsos mensual", href: "/app/financiero?vista=mensual" },
        { id: "ef-acumulado", titulo: "Estado de ingresos y desembolsos acumulado", href: "/app/financiero?vista=acumulado" },
        { id: "ef-balance-mensual", titulo: "Balance general acumulado mensual", href: "/app/financiero?vista=balance-mensual" },
        { id: "ef-balance-comparativo", titulo: "Balance general acumulado comparativo", href: "/app/financiero?vista=balance-comparativo" },
      ],
    },
    {
      id: "otros-informes-financieros",
      titulo: "Otros informes financieros",
      hijos: [
        { id: "oif-cuotas", titulo: "Cuotas asociados" },
        { id: "oif-conciliacion", titulo: "Conciliación bancaria" },
        { id: "oif-flujo", titulo: "Flujo de caja" },
        { id: "oif-gastos-mes", titulo: "Ejecución gastos por mes" },
        { id: "oif-gastos-acum", titulo: "Ejecución gastos acumulado" },
      ],
    },
    {
      id: "presupuestos",
      titulo: "Presupuestos",
      hijos: [
        { id: "pr-ejecucion", titulo: "Ejecución vs presupuesto" },
        { id: "pr-ejecucion-acum", titulo: "Ejecución vs presupuesto acumulado" },
        { id: "pr-comparativo", titulo: "Comparativo ejecutado" },
      ],
    },
    {
      id: "otros-ingresos",
      titulo: "Otros ingresos",
      hijos: [{ id: "oi-generados", titulo: "Otros ingresos generados" }],
    },
  ],
};

// Items reales -- los mismos 2 que ya existían como enlaces en el nav
// superior de AppLayout (/app/plaguicidas, /app/nutrientes).
const MENU_IMPORTACIONES: NodoMenu = {
  id: "importaciones",
  titulo: "Importaciones",
  hijos: [
    { id: "imp-plaguicidas", titulo: "Plaguicidas", href: "/app/plaguicidas" },
    { id: "imp-nutrientes", titulo: "Nutrientes", href: "/app/nutrientes" },
  ],
};

function estaActivo(location: ReturnType<typeof useLocation>, href: string): boolean {
  const [path, query] = href.split("?");
  if (location.pathname !== path) return false;
  if (!query) return true;
  return new URLSearchParams(location.search).get("vista") === new URLSearchParams(query).get("vista");
}

function NodoView({
  nodo,
  nivel,
  abiertos,
  alternar,
  location,
}: {
  nodo: NodoMenu;
  nivel: number;
  abiertos: Set<string>;
  alternar: (id: string) => void;
  location: ReturnType<typeof useLocation>;
}) {
  const esHoja = !nodo.hijos || nodo.hijos.length === 0;

  if (esHoja) {
    const claseBase = "block rounded px-2 py-1.5 text-xs leading-snug transition-colors";
    if (nodo.href) {
      return (
        <Link
          to={nodo.href}
          className={`${claseBase} ${
            estaActivo(location, nodo.href) ? "bg-sky-500/20 text-sky-300" : "text-sky-400 hover:bg-white/5 hover:text-sky-300"
          }`}
        >
          {nodo.titulo}
        </Link>
      );
    }
    return (
      <span className={`${claseBase} text-sky-400/40`} title="Todavía no implementado">
        {nodo.titulo}
      </span>
    );
  }

  const abierta = abiertos.has(nodo.id);
  const esNivelSuperior = nivel === 0;

  return (
    <div>
      <button
        type="button"
        onClick={() => alternar(nodo.id)}
        className={`flex w-full items-center justify-between gap-2 rounded px-2 py-2 text-left transition-colors hover:bg-white/5 ${
          esNivelSuperior ? "text-sm font-bold text-white" : "text-xs font-semibold text-white/85"
        }`}
        title={nodo.titulo}
      >
        <span className="leading-tight">{nodo.titulo}</span>
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
          className={`h-4 w-4 shrink-0 transition-transform ${abierta ? "rotate-180" : ""}`}
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.19l3.71-3.96a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>
      {abierta && (
        <ul className="mb-1 mt-0.5 space-y-0.5 pl-3">
          {nodo.hijos!.map((hijo) => (
            <li key={hijo.id}>
              <NodoView nodo={hijo} nivel={nivel + 1} abiertos={abiertos} alternar={alternar} location={location} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Menú lateral estilo Power BI: colapsado a una franja angosta por
 * defecto, se expande al pasar el mouse. Financiero e Importaciones son
 * hermanas de primer nivel (ver MENU_FINANCIERO/MENU_IMPORTACIONES);
 * cada una se muestra/oculta según los mismos flags de sesión que ya
 * usaba el nav superior (sesion.accesoFinanciero/accesoImportaciones)
 * -- ningún sistema de permisos nuevo. */
export function Sidebar() {
  const { sesion } = useAuth();
  const location = useLocation();
  const [expandido, setExpandido] = useState(false);
  const [seccionesAbiertas, setSeccionesAbiertas] = useState<Set<string>>(
    () => new Set(["financiero", "estados-financieros"])
  );

  function alternarSeccion(id: string) {
    setSeccionesAbiertas((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(id)) siguiente.delete(id);
      else siguiente.add(id);
      return siguiente;
    });
  }

  const nodosRaiz: NodoMenu[] = [
    ...(sesion?.accesoFinanciero ? [MENU_FINANCIERO] : []),
    ...(sesion?.accesoImportaciones ? [MENU_IMPORTACIONES] : []),
  ];

  const puedeVerAdministracion = sesion?.rol === "Administrador" || sesion?.rol === "Administrador de Usuarios";

  return (
    <aside
      onMouseEnter={() => setExpandido(true)}
      onMouseLeave={() => setExpandido(false)}
      className={`sticky top-0 flex h-screen shrink-0 flex-col overflow-x-hidden bg-[#444444] transition-[width] duration-150 ${
        expandido ? "w-[262px]" : "w-14"
      }`}
    >
      <div className="flex shrink-0 items-center justify-center border-b border-white/10 px-2 py-4">
        <span className="text-xs font-bold uppercase tracking-wide text-white">{expandido ? "Menu" : "M"}</span>
      </div>

      {expandido ? (
        <nav className="flex-1 space-y-1 overflow-y-auto overflow-x-hidden px-2 py-3">
          {nodosRaiz.map((nodo) => (
            <NodoView key={nodo.id} nodo={nodo} nivel={0} abiertos={seccionesAbiertas} alternar={alternarSeccion} location={location} />
          ))}
        </nav>
      ) : (
        <nav className="flex-1 space-y-2 overflow-hidden px-2 py-3 text-center" aria-hidden="true">
          {nodosRaiz.map((nodo) => (
            <div key={nodo.id} className="text-white/60">
              •
            </div>
          ))}
        </nav>
      )}

      {puedeVerAdministracion && (
        <div className="shrink-0 border-t border-white/10 px-2 py-3">
          <Link
            to="/admin"
            className="flex items-center gap-2 rounded px-2 py-2 text-sm font-semibold text-white hover:bg-white/5"
          >
            <span aria-hidden="true">⚙</span>
            {expandido && <span>Administración</span>}
          </Link>
        </div>
      )}
    </aside>
  );
}

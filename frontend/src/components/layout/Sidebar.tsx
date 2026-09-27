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
        { id: "oif-cuotas", titulo: "Cuotas asociados", href: "/app/financiero/otros-informes?vista=cuotas-asociados" },
        { id: "oif-conciliacion", titulo: "Conciliación bancaria", href: "/app/financiero/otros-informes?vista=conciliacion-bancaria" },
        { id: "oif-flujo", titulo: "Flujo de caja", href: "/app/financiero/otros-informes?vista=flujo-caja" },
        { id: "oif-gastos-mes", titulo: "Ejecución gastos por mes", href: "/app/financiero/otros-informes?vista=gastos-mes" },
        { id: "oif-gastos-acum", titulo: "Ejecución gastos acumulado", href: "/app/financiero/otros-informes?vista=gastos-acumulado" },
      ],
    },
    {
      id: "presupuestos",
      titulo: "Presupuestos",
      hijos: [
        { id: "pr-ejecucion", titulo: "Ejecución vs presupuesto", href: "/app/financiero/presupuestos?vista=ejecucion-vs-presupuesto" },
        {
          id: "pr-ejecucion-acum",
          titulo: "Ejecución vs presupuesto acumulado",
          href: "/app/financiero/presupuestos?vista=ejecucion-vs-presupuesto-acumulado",
        },
        { id: "pr-comparativo", titulo: "Comparativo ejecutado", href: "/app/financiero/presupuestos?vista=comparativo-ejecutado" },
      ],
    },
    {
      // Distinto del sistema hermano "Importaciones" (Plaguicidas/
      // Nutrientes, MENU_IMPORTACIONES más abajo): esta es la sección de
      // ingresos de la gremial por importaciones dentro del propio
      // Financiero (fuentes vw_piq_* de CONTACC), páginas reales del
      // .pbix "Ingresos por importación", "Ingresos por Importación
      // Gremiagro", "Comparación importaciones Kilolitros" e "Ingresos
      // por contribución 4.5 por millar" -- todavía sin construir, por
      // eso sin href (mismo patrón usado antes con Conciliación/Flujo).
      id: "importaciones-financiero",
      titulo: "Importaciones",
      hijos: [
        { id: "if-ingresos", titulo: "Ingresos por importación", href: "/app/financiero/importaciones?vista=ingresos" },
        {
          id: "if-ingresos-comparativo",
          titulo: "Ingresos por importación comparativo",
          href: "/app/financiero/importaciones?vista=comparativo",
        },
        {
          id: "if-kilolitros",
          titulo: "Comparación importaciones kilolitros y precio kilolitro",
          href: "/app/financiero/importaciones?vista=kilolitros",
        },
        {
          id: "if-contribucion",
          titulo: "Ingresos por contribución 4.5 por millar",
          href: "/app/financiero/importaciones?vista=contribucion-millar",
        },
      ],
    },
    {
      id: "otros-ingresos",
      titulo: "Otros ingresos",
      hijos: [{ id: "oi-generados", titulo: "Otros ingresos generados", href: "/app/financiero/otros-ingresos" }],
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

// Color de acento distinto por sistema (opción "A + C" del diagnóstico
// de menú): Importaciones conserva el sky que ya tenía (sin cambio
// visual para quien ya lo conocía); Financiero pasa a ámbar, para que
// ambos bloques se distingan de un vistazo sin cambiar la navegación.
interface TemaSistema {
  activo: string;
  inactivo: string;
  deshabilitado: string;
}

const TEMA_FINANCIERO: TemaSistema = {
  activo: "bg-amber-500/20 text-amber-300",
  inactivo: "text-amber-400 hover:bg-white/5 hover:text-amber-300",
  deshabilitado: "text-amber-400/40",
};

const TEMA_IMPORTACIONES: TemaSistema = {
  activo: "bg-sky-500/20 text-sky-300",
  inactivo: "text-sky-400 hover:bg-white/5 hover:text-sky-300",
  deshabilitado: "text-sky-400/40",
};

function estaActivo(location: ReturnType<typeof useLocation>, href: string): boolean {
  const [path, query] = href.split("?");
  if (location.pathname !== path) return false;
  if (!query) return true;
  return new URLSearchParams(location.search).get("vista") === new URLSearchParams(query).get("vista");
}

/** IDs de todas las secciones colapsables que hay que dejar abiertas para
 * que la pantalla activa (según la ruta actual) quede visible sin tocar
 * nada a mano -- recorre el árbol y devuelve el camino completo (sistema
 * + sub-secciones anidadas) hasta la hoja con href activo. Si ninguna
 * hoja de este árbol está activa (parado en una pantalla fuera de él,
 * ej. Plaguicidas mientras se recorre MENU_FINANCIERO), devuelve un Set
 * vacío -- ese árbol queda completamente colapsado. */
function idsHastaActivo(nodos: NodoMenu[], location: ReturnType<typeof useLocation>): Set<string> {
  for (const nodo of nodos) {
    if (!nodo.hijos || nodo.hijos.length === 0) continue;
    if (nodo.hijos.some((hijo) => hijo.href && estaActivo(location, hijo.href))) {
      return new Set([nodo.id]);
    }
    const idsAnidados = idsHastaActivo(nodo.hijos, location);
    if (idsAnidados.size > 0) {
      return new Set([nodo.id, ...idsAnidados]);
    }
  }
  return new Set();
}

function NodoView({
  nodo,
  nivel,
  abiertos,
  alternar,
  location,
  tema,
  icono,
}: {
  nodo: NodoMenu;
  nivel: number;
  abiertos: Set<string>;
  alternar: (id: string) => void;
  location: ReturnType<typeof useLocation>;
  tema: TemaSistema;
  icono?: string;
}) {
  const esHoja = !nodo.hijos || nodo.hijos.length === 0;

  if (esHoja) {
    const claseBase = "block rounded px-2 py-1.5 text-xs leading-snug transition-colors";
    if (nodo.href) {
      return (
        <Link
          to={nodo.href}
          className={`${claseBase} ${estaActivo(location, nodo.href) ? tema.activo : tema.inactivo}`}
        >
          {nodo.titulo}
        </Link>
      );
    }
    return (
      <span className={`${claseBase} ${tema.deshabilitado}`} title="Todavía no implementado">
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
        <span className="leading-tight">
          {esNivelSuperior && icono ? <span aria-hidden="true">{icono} </span> : null}
          {nodo.titulo}
        </span>
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
              <NodoView nodo={hijo} nivel={nivel + 1} abiertos={abiertos} alternar={alternar} location={location} tema={tema} />
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

  // Un sistema por bloque de primer nivel -- encabezado no clicable +
  // ícono + tema de color propios (opciones A+C del diagnóstico de
  // menú), respetando los mismos flags de acceso que ya decidían si el
  // bloque se muestra o no.
  const sistemas = [
    { nodo: MENU_FINANCIERO, encabezado: "Dashboard Financiero", icono: "💰", tema: TEMA_FINANCIERO, visible: !!sesion?.accesoFinanciero },
    { nodo: MENU_IMPORTACIONES, encabezado: "Dashboard Importaciones", icono: "📦", tema: TEMA_IMPORTACIONES, visible: !!sesion?.accesoImportaciones },
  ].filter((s) => s.visible);

  // Set inicial de secciones abiertas: SOLO el sistema y la(s)
  // sub-sección(es) que contienen la pantalla activa según la ruta
  // actual (antes hardcodeado siempre a "financiero"+"estados-
  // financieros", sin importar dónde estuviera parado el usuario). Se
  // calcula una sola vez al montar el Sidebar (lazy initializer) -- a
  // partir de ahí el usuario abre/cierra secciones a mano sin que se
  // le vuelvan a forzar. Si la ruta activa no está en ningún árbol
  // (ej. una pantalla fuera de Financiero/Importaciones), todo queda
  // colapsado.
  const [seccionesAbiertas, setSeccionesAbiertas] = useState<Set<string>>(() =>
    idsHastaActivo(sistemas.map((s) => s.nodo), location)
  );

  function alternarSeccion(id: string) {
    setSeccionesAbiertas((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(id)) siguiente.delete(id);
      else siguiente.add(id);
      return siguiente;
    });
  }

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
          {sistemas.map((sistema, indice) => (
            <div key={sistema.nodo.id}>
              {indice > 0 && <div className="mb-1 mt-2 border-t border-white/10" />}
              {/* Encabezado no clicable por sistema -- deja claro que
                  "Financiero" e "Importaciones" son 2 dashboards
                  distintos, no 2 secciones del mismo. Sin cambiar la
                  navegación: el botón colapsable de abajo sigue igual. */}
              <div className="px-2 pb-1 pt-1 text-[10px] font-bold uppercase tracking-wide text-white/40">
                {sistema.encabezado}
              </div>
              <NodoView
                nodo={sistema.nodo}
                nivel={0}
                abiertos={seccionesAbiertas}
                alternar={alternarSeccion}
                location={location}
                tema={sistema.tema}
                icono={sistema.icono}
              />
            </div>
          ))}
        </nav>
      ) : (
        <nav className="flex-1 space-y-2 overflow-hidden px-2 py-3 text-center" aria-hidden="true">
          {sistemas.map((sistema) => (
            <div key={sistema.nodo.id} className="text-base leading-none">
              {sistema.icono}
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

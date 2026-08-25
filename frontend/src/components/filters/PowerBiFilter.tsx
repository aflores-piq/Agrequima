import { useEffect, useRef, useState, type ChangeEvent } from "react";

/** Estilo de filtro calcado del reporte original de Power BI (ver
 * docs/legacy/referencia-dashboards/): cabecera de color sólido con el
 * nombre del filtro, y debajo un control oscuro con borde gris.
 * Plaguicidas usa el teal original; Nutrientes usa naranja para combinar
 * con el acento propio de sus gráficos (antes ambos dashboards
 * compartían el mismo teal en la fila de filtros). */
export type FilterTheme = "teal" | "orange";

const TEMAS: Record<FilterTheme, { wrapper: string; header: string }> = {
  teal: {
    wrapper: "overflow-hidden rounded-sm bg-teal-900",
    header: "px-2 pt-1 pb-1 text-[10px] font-semibold uppercase tracking-wide text-teal-300",
  },
  orange: {
    wrapper: "overflow-hidden rounded-sm bg-orange-900",
    header: "px-2 pt-1 pb-1 text-[10px] font-semibold uppercase tracking-wide text-orange-300",
  },
};

const VALUE_WRAPPER_CLASS = "relative px-1.5 pb-1.5";
// El "chip" de cabecera (TEMAS, arriba) es un color fijo por dashboard y
// no responde al tema — pero el control en sí (input, flecha, dropdown,
// checkboxes) sí debe verse bien en claro y oscuro, así que usa los
// tokens semánticos (bg-app/bg-surface/text-ink, ver index.css) en vez
// de colores slate fijos.
const CONTROL_CLASS =
  "w-full appearance-none rounded-[2px] border border-line-strong bg-app px-2 py-1 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:ring-1 focus:ring-line-strong";

function Chevron() {
  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none absolute right-2.5 top-1/2 h-3 w-3 -translate-y-1/2 text-ink-faint"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M5.23 7.21a.75.75 0 011.06.02L10 11.19l3.71-3.96a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
        clipRule="evenodd"
      />
    </svg>
  );
}

/** Año y "hasta el mes" como UN solo filtro visual (igual que "2026 +
 * Julio" en Power BI): una sola cabecera y una sola caja con borde, con
 * dos <select> anidados adentro en vez de dos cajas independientes una
 * junto a la otra. */
export function FilterYearMonth({
  label = "Año",
  anio,
  mes,
  onChangeAnio,
  onChangeMes,
  aniosOpciones,
  mesesOpciones,
  theme = "teal",
}: {
  label?: string;
  anio: string;
  mes: string;
  onChangeAnio: (v: string) => void;
  onChangeMes: (v: string) => void;
  aniosOpciones: string[];
  mesesOpciones: { value: string; label: string }[];
  theme?: FilterTheme;
}) {
  const { wrapper, header } = TEMAS[theme];
  return (
    <div className={wrapper}>
      <div className={header}>{label}</div>
      <div className="flex items-center gap-1 px-1.5 pb-1.5">
        <div className="relative min-w-0 flex-1">
          <select
            value={anio}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => onChangeAnio(e.target.value)}
            className={CONTROL_CLASS}
            aria-label="Año"
          >
            {aniosOpciones.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <Chevron />
        </div>
        <span className="text-xs text-ink-faint">+</span>
        <div className="relative min-w-0 flex-[1.4]">
          <select
            value={mes}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => onChangeMes(e.target.value)}
            className={CONTROL_CLASS}
            aria-label="Hasta el mes"
          >
            {mesesOpciones.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
          <Chevron />
        </div>
      </div>
    </div>
  );
}

function Checkbox({ marcado }: { marcado: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-sm border ${
        marcado ? "border-ink bg-ink" : "border-line-strong"
      }`}
    >
      {marcado && (
        <svg viewBox="0 0 12 12" className="h-2.5 w-2.5 text-app" fill="currentColor">
          <path d="M4.7 8.3 2.1 5.7l.9-.9 1.7 1.7 4.3-4.3.9.9z" />
        </svg>
      )}
    </span>
  );
}

/** Combobox con búsqueda y selección múltiple (dropdown + campo de texto
 * integrado + casillas), igual al buscador de los slicers de Power BI
 * pero permitiendo marcar varios valores a la vez (semántica OR en el
 * backend — ver _filtro_grupo/_filtro_producto_agrupado y los `.in_()`
 * en dashboard_plaguicidas.py / dashboard_nutrientes.py). Al escribir,
 * filtra la lista desplegada por coincidencia parcial en cualquier parte
 * del texto (sin distinguir mayúsculas/minúsculas). Marcar/desmarcar una
 * opción no cierra el dropdown, para poder seguir marcando más; "Todos"
 * desmarca todo. */
export function FilterMultiCombobox({
  label,
  values,
  onChange,
  options,
  placeholder = "Todos",
  theme = "teal",
}: {
  label: string;
  values: string[];
  onChange: (v: string[]) => void;
  options: string[];
  placeholder?: string;
  theme?: FilterTheme;
}) {
  const { wrapper, header } = TEMAS[theme];
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const contenedorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickFuera(e: MouseEvent) {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target as Node)) {
        setAbierto(false);
        setBusqueda("");
      }
    }
    document.addEventListener("mousedown", onClickFuera);
    return () => document.removeEventListener("mousedown", onClickFuera);
  }, []);

  const filtradas = busqueda
    ? options.filter((o) => o.toLowerCase().includes(busqueda.toLowerCase()))
    : options;

  function alternar(v: string) {
    onChange(values.includes(v) ? values.filter((x) => x !== v) : [...values, v]);
  }

  function limpiarTodos() {
    onChange([]);
    setBusqueda("");
    setAbierto(false);
  }

  const textoValor =
    values.length === 0 ? "" : values.length === 1 ? values[0] : `${values.length} seleccionados`;

  return (
    <div className="relative" ref={contenedorRef}>
      <div className={wrapper}>
        <div className={header}>{label}</div>
        <div className={VALUE_WRAPPER_CLASS}>
          <input
            value={abierto ? busqueda : textoValor}
            onChange={(e) => setBusqueda(e.target.value)}
            onFocus={() => {
              setAbierto(true);
              setBusqueda("");
            }}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                setAbierto(false);
                setBusqueda("");
              } else if (e.key === "Enter" && filtradas.length > 0) {
                alternar(filtradas[0]);
                setBusqueda("");
              }
            }}
            placeholder={placeholder}
            title={values.length > 1 ? values.join(", ") : undefined}
            className={CONTROL_CLASS}
            autoComplete="off"
          />
          <Chevron />
        </div>
      </div>
      {abierto && (
        <div className="absolute left-1.5 right-1.5 top-full z-20 mt-1 max-h-56 overflow-y-auto rounded-[2px] border border-line bg-surface shadow-lg">
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={limpiarTodos}
            className="block w-full px-2 py-1 text-left text-xs text-ink-muted hover:bg-surface-hover"
          >
            {placeholder}
          </button>
          {filtradas.length === 0 && <p className="px-2 py-1 text-xs text-ink-faint">Sin coincidencias</p>}
          {filtradas.map((o) => {
            const marcado = values.includes(o);
            return (
              <button
                key={o}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => alternar(o)}
                className={`flex w-full items-center gap-2 px-2 py-1 text-left text-xs hover:bg-surface-hover ${
                  marcado ? "bg-surface-hover text-ink" : "text-ink-muted"
                }`}
                title={o}
              >
                <Checkbox marcado={marcado} />
                <span className="truncate">{o}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

import type { ReactNode } from "react";

// Tooltip único para TODAS las gráficas del módulo Financiero.
//
// Problema que resuelve (reunión con la junta, 7-oct-2026): los tooltips por
// defecto de Recharts pintaban el TEXTO con el color de cada serie (verde
// azulado, celeste, ámbar...) sobre un fondo gris, y muchos no se
// distinguían. Ahora:
//  - fondo SÓLIDO de alto contraste: oscuro en modo oscuro y claro en modo
//    claro (variable --color-bg-surface), con borde sutil y sombra;
//  - texto en el color de alto contraste del tema (--color-ink: casi blanco
//    en oscuro, casi negro en claro), 13 px como mínimo, valor en negrita;
//  - el color de cada serie se conserva SOLO como marcador (círculo) al lado
//    del nombre, nunca como color del texto;
//  - z-index alto: siempre por encima de cualquier elemento de la gráfica.
// Referencia de estilo: los tooltips de Plaguicidas y Nutrientes (aprobados).

type ItemTooltip = {
  name?: string | number;
  value?: number | string;
  color?: string;
  fill?: string;
  stroke?: string;
  dataKey?: string | number;
  payload?: Record<string, unknown>;
};

export type OpcionesTooltipFinanciero = {
  /** Igual que el `formatter` de Recharts: devuelve el valor ya formateado, o [valor, nombre]. */
  formatter?: (valor: number, nombre: string, item: ItemTooltip) => ReactNode | [ReactNode, ReactNode];
  /** Texto del encabezado del tooltip (por defecto, la etiqueta del eje). */
  tituloDe?: (label: unknown, payload: ItemTooltip[]) => ReactNode;
  /** Nombre que se muestra al lado del valor (por defecto, `name` de la serie). */
  nombreDe?: (item: ItemTooltip) => ReactNode;
  /** Color del marcador (por defecto, el color de la serie o el relleno de la porción/barra). */
  colorDe?: (item: ItemTooltip) => string | undefined;
  /** Oculta series cuyo valor no se debe mostrar (p. ej. valores nulos). */
  mostrar?: (item: ItemTooltip) => boolean;
  /** Tipo de gráfica: define el cursor (barras = sombreado de la categoría, líneas = guía vertical, dona = ninguno). */
  tipo?: "barras" | "lineas" | "dona";
};

const ESTILO_CAJA = {
  background: "rgb(var(--color-bg-surface))",
  border: "1px solid rgb(var(--color-line-strong) / 0.7)",
  borderRadius: 8,
  boxShadow: "0 10px 28px rgba(0, 0, 0, 0.38), 0 2px 6px rgba(0, 0, 0, 0.25)",
  color: "rgb(var(--color-ink))",
  padding: "10px 14px",
  fontSize: 13,
  lineHeight: 1.35,
  minWidth: 150,
} as const;

export function TooltipFinanciero({
  active,
  payload,
  label,
  formatter,
  tituloDe,
  nombreDe,
  colorDe,
  mostrar,
}: OpcionesTooltipFinanciero & { active?: boolean; payload?: ItemTooltip[]; label?: unknown }) {
  if (!active || !payload || payload.length === 0) return null;
  const items = payload.filter((it) => (mostrar ? mostrar(it) : it.value !== undefined && it.value !== null));
  if (items.length === 0) return null;
  const titulo = (tituloDe ? tituloDe(label, payload) : label) as ReactNode;
  return (
    <div style={ESTILO_CAJA} data-testid="tooltip-financiero">
      {titulo !== undefined && titulo !== null && titulo !== "" && (
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, color: "rgb(var(--color-ink))" }}>{titulo}</div>
      )}
      <div style={{ display: "grid", gap: 4 }}>
        {items.map((it, i) => {
          const nombreBase = String(it.name ?? it.dataKey ?? "");
          let valor: ReactNode = it.value;
          let nombre: ReactNode = nombreDe ? nombreDe(it) : nombreBase;
          if (formatter && typeof it.value === "number") {
            const r = formatter(it.value, nombreBase, it);
            if (Array.isArray(r)) {
              valor = r[0];
              if (!nombreDe) nombre = r[1];
            } else {
              valor = r;
            }
          }
          const color = (colorDe ? colorDe(it) : undefined) ?? it.color ?? it.fill ?? it.stroke ?? (it.payload?.fill as string | undefined);
          return (
            <div key={`${nombreBase}-${i}`} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                aria-hidden="true"
                style={{ width: 10, height: 10, borderRadius: "50%", flexShrink: 0, background: color ?? "rgb(var(--color-ink-muted))", boxShadow: "0 0 0 1.5px rgb(var(--color-bg-surface)), 0 0 0 2.5px rgb(var(--color-line-strong) / 0.6)" }}
              />
              {nombre !== "" && nombre !== undefined && (
                <span style={{ color: "rgb(var(--color-ink))", fontSize: 13 }}>{nombre}</span>
              )}
              <span style={{ marginLeft: "auto", paddingLeft: 12, fontWeight: 700, fontSize: 13, color: "rgb(var(--color-ink))", whiteSpace: "nowrap" }}>{valor}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Props para `<Tooltip {...tooltipFinanciero({...})} />` de Recharts. */
export function tooltipFinanciero(opciones: OpcionesTooltipFinanciero = {}) {
  const tipo = opciones.tipo ?? "barras";
  const cursor =
    tipo === "barras"
      ? { fill: "rgb(var(--color-ink-faint) / 0.12)" }
      : tipo === "lineas"
        ? { stroke: "rgb(var(--color-ink-faint) / 0.7)", strokeWidth: 1, strokeDasharray: "4 3" }
        : false;
  return {
    content: <TooltipFinanciero {...opciones} />,
    cursor,
    isAnimationActive: false,
    // Siempre por encima de cualquier elemento de la gráfica (etiquetas, barras, capas superpuestas).
    wrapperStyle: { zIndex: 1000, outline: "none" },
  } as const;
}

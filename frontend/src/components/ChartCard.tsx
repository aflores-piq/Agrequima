import { useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Card, Title, Text } from "@tremor/react";
import type { DashboardTheme } from "../theme/colors";

// Color de la pastilla seleccionada del interruptor Gráfico/Tabla: usa
// el color de identidad FIJO del dashboard donde vive (teal en
// Plaguicidas, naranja en Nutrientes) — NUNCA el acento general de la
// interfaz, igual que ya se hizo con los filtros (ver PowerBiFilter.tsx
// y theme/colors.ts).
const COLOR_SELECCION: Record<DashboardTheme, string> = {
  plaguicidas: "bg-teal-600",
  nutrientes: "bg-orange-600",
  financiero: "bg-blue-600",
};

/** Tarjeta de gráfico con vista de tabla equivalente (accesibilidad):
 * todo gráfico del dashboard se envuelve en este componente. */
export function ChartCard({
  theme,
  title,
  subtitle,
  chart,
  table,
  exportar,
  estiloTarjeta,
  controlesExtra,
  colorSeleccionHex,
  tituloChico,
}: {
  theme: DashboardTheme;
  title: string;
  subtitle?: string;
  chart: ReactNode;
  table: ReactNode;
  exportar?: ReactNode;
  /** Override puntual del fondo de la tarjeta (ej. Financiero, que
   * necesita un gris más claro que bg-surface para distinguirse del
   * fondo general muy oscuro de la app) -- no afecta a Plaguicidas ni
   * Nutrientes, que no lo pasan y siguen usando bg-surface. */
  estiloTarjeta?: CSSProperties;
  // Slot opcional para un selector adicional en el encabezado (ej. la
  // métrica CIF USD/Kilolitros de "Top 20 moléculas plaguicidas"), junto
  // al selector Gráfico/Tabla -- no afecta ningún ChartCard existente
  // que no lo use.
  controlesExtra?: ReactNode;
  /** Override puntual del color de la pastilla seleccionada del
   * interruptor Gráfico/Tabla, como color hex (via inline style en vez
   * de la clase Tailwind de COLOR_SELECCION) -- para páginas como
   * "Cuotas Asociados" donde el azul fijo de `financiero` (bg-blue-600)
   * no forma parte de la paleta real del reporte (verde/azul/gris por
   * Tipo) y se ve como un acento azul de más. No pasar este prop no
   * cambia nada: sigue usando COLOR_SELECCION[theme] como siempre. */
  colorSeleccionHex?: string;
  /** El <Title> de Tremor por defecto es grande (pensado para tarjetas
   * completas) -- en tarjetas compactas (ej. los 3 gráficos de Cuotas
   * Asociados, de solo 190px de alto) se ve exageradamente grande en
   * proporción al resto del contenido, calcado del .pbix real que usa
   * un título chico y discreto. No pasar este prop no cambia nada:
   * sigue usando el <Title> de Tremor como siempre. */
  tituloChico?: boolean;
}) {
  const [vista, setVista] = useState<"grafico" | "tabla">("grafico");
  const colorSeleccion = COLOR_SELECCION[theme];

  return (
    <Card className="flex h-full flex-col bg-surface ring-1 ring-line" style={estiloTarjeta}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          {tituloChico ? (
            <p className="text-sm font-semibold text-ink">{title}</p>
          ) : (
            <Title className="text-ink">{title}</Title>
          )}
          {subtitle && <Text className="text-ink-muted">{subtitle}</Text>}
        </div>
        <div className="flex items-center gap-2">
          {exportar}
          {controlesExtra}
          <div
            role="group"
            aria-label={`Cambiar vista de ${title}`}
            className="flex rounded-tremor-small bg-surface-hover p-0.5 text-xs"
          >
            <button
              type="button"
              aria-pressed={vista === "grafico"}
              onClick={() => setVista("grafico")}
              className={`rounded-tremor-small px-2.5 py-1 transition-colors ${
                vista === "grafico" ? `${colorSeleccionHex ? "" : colorSeleccion} text-white` : "text-ink-muted hover:text-ink"
              }`}
              style={vista === "grafico" && colorSeleccionHex ? { backgroundColor: colorSeleccionHex } : undefined}
            >
              Gráfico
            </button>
            <button
              type="button"
              aria-pressed={vista === "tabla"}
              onClick={() => setVista("tabla")}
              className={`rounded-tremor-small px-2.5 py-1 transition-colors ${
                vista === "tabla" ? `${colorSeleccionHex ? "" : colorSeleccion} text-white` : "text-ink-muted hover:text-ink"
              }`}
              style={vista === "tabla" && colorSeleccionHex ? { backgroundColor: colorSeleccionHex } : undefined}
            >
              Tabla
            </button>
          </div>
        </div>
      </div>
      <div className="mt-4 min-h-0 flex-1">{vista === "grafico" ? chart : table}</div>
    </Card>
  );
}

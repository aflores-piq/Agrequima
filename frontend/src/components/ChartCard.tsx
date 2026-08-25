import { useState } from "react";
import type { ReactNode } from "react";
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
}: {
  theme: DashboardTheme;
  title: string;
  subtitle?: string;
  chart: ReactNode;
  table: ReactNode;
  exportar?: ReactNode;
}) {
  const [vista, setVista] = useState<"grafico" | "tabla">("grafico");
  const colorSeleccion = COLOR_SELECCION[theme];

  return (
    <Card className="flex h-full flex-col bg-surface ring-1 ring-line">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Title className="text-ink">{title}</Title>
          {subtitle && <Text className="text-ink-muted">{subtitle}</Text>}
        </div>
        <div className="flex items-center gap-2">
          {exportar}
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
                vista === "grafico" ? `${colorSeleccion} text-white` : "text-ink-muted hover:text-ink"
              }`}
            >
              Gráfico
            </button>
            <button
              type="button"
              aria-pressed={vista === "tabla"}
              onClick={() => setVista("tabla")}
              className={`rounded-tremor-small px-2.5 py-1 transition-colors ${
                vista === "tabla" ? `${colorSeleccion} text-white` : "text-ink-muted hover:text-ink"
              }`}
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

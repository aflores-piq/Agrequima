import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { formatQ } from "../../utils/format";
import { FINANCIERO_SURFACE } from "../TablaGrupoExpandible";
import type { DistribucionBalanceItem } from "../../types/dashboardFinanciero";

// Colores REALES leídos pixel a pixel de la captura del reporte viejo
// (docs/legacy/Financiero_capturas/), re-confirmados en esta ronda.
const COLOR_POR_ETIQUETA: Record<string, string> = {
  Patrimonio: "#375B7D",
  Pasivo: "#E87471",
  "Fondos por aplicar": "#35B0A2",
  Activo: "#3F6F6B",
};

// Orden fijo de la leyenda -- calcado de la captura real, no el orden
// en que llega el arreglo del backend.
const ORDEN_ETIQUETAS = ["Patrimonio", "Pasivo", "Fondos por aplicar", "Activo"];

/** Dona de distribución del balance -- 4 porciones: Patrimonio/Pasivo/
 * Fondos por aplicar/Activo. Activo = Pasivo + Patrimonio + Fondos por
 * aplicar (identidad contable) -- su porción mide EXACTAMENTE la mitad
 * del anillo sin forzar ningún ángulo, es una dona normal de 4
 * categorías donde una vale el doble de la suma de las otras 3
 * (confirmado contra la captura real: una sesión anterior había
 * especificado mal esto como "3 porciones + Activo aparte"). */
export function BalanceDonut({
  data,
  activoReferencia,
  altura = 200,
}: {
  data: DistribucionBalanceItem[];
  activoReferencia: number;
  /** Alto del panel completo -- debe coincidir con el que usan los
   * gráficos de barra de las otras páginas (mismo prop `altura` que
   * TresBarrasResultado/ComparativoAnioBarChart) para que los 4 paneles
   * de gráfico midan lo mismo. El anillo mismo mide ~84% de este alto
   * (medido en la captura real). */
  altura?: number;
}) {
  const conActivo: DistribucionBalanceItem[] = [
    ...data.filter((d) => d.monto !== 0),
    { etiqueta: "Activo", monto: activoReferencia, porcentaje: 100 },
  ];
  const ordenada = [...conActivo].sort(
    (a, b) => ORDEN_ETIQUETAS.indexOf(a.etiqueta) - ORDEN_ETIQUETAS.indexOf(b.etiqueta)
  );

  if (ordenada.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  // % de cada porción respecto al anillo completo (no el `porcentaje`
  // que manda el backend, que está calculado respecto a Activo=100% --
  // válido para la vista de tabla de la página, pero no para la
  // leyenda de ESTE anillo de 4 categorías donde el total es 2×Activo).
  const totalAnillo = ordenada.reduce((acc, d) => acc + Math.abs(d.monto), 0);

  const diametro = Math.round(altura * 0.84);

  return (
    <div className="flex h-full w-full flex-col" style={{ minHeight: altura }}>
      <div className="flex flex-1 items-center justify-center gap-4">
        <div className="relative shrink-0" style={{ width: diametro, height: diametro }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={ordenada}
                dataKey={(d: DistribucionBalanceItem) => Math.abs(d.monto)}
                nameKey="etiqueta"
                cx="50%"
                cy="50%"
                startAngle={90}
                endAngle={-270}
                innerRadius="70%"
                outerRadius="100%"
                stroke={FINANCIERO_SURFACE}
                strokeWidth={2}
                isAnimationActive={false}
              >
                {ordenada.map((item) => (
                  <Cell key={item.etiqueta} fill={COLOR_POR_ETIQUETA[item.etiqueta] ?? "#64748b"} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => formatQ(value)}
                contentStyle={{
                  background: FINANCIERO_SURFACE,
                  border: "1px solid rgb(var(--color-line))",
                  borderRadius: 8,
                }}
                labelStyle={{ color: "rgb(var(--color-ink))" }}
                itemStyle={{ color: "rgb(var(--color-ink))" }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[10px] text-ink-muted">Activo</span>
            <span className="text-sm font-bold text-ink">{formatQ(activoReferencia)}</span>
          </div>
        </div>
        {/* Leyenda compacta -- ancho al contenido (sin flex-1), para que
            no le sobre espacio horizontal vacío como antes. */}
        <ul className="shrink-0 space-y-4">
          {ordenada.map((item) => (
            <li key={item.etiqueta} className="flex items-center gap-2 text-sm">
              <span
                className="h-3 w-3 shrink-0 rounded-sm"
                style={{ backgroundColor: COLOR_POR_ETIQUETA[item.etiqueta] ?? "#64748b" }}
                aria-hidden="true"
              />
              <span className="text-ink">{item.etiqueta}</span>
              <span className="w-10 shrink-0 text-right font-semibold text-blue-400">
                {((Math.abs(item.monto) / totalAnillo) * 100).toFixed(1)}%
              </span>
              <span className="w-16 shrink-0 text-right text-ink-muted">{formatQ(item.monto)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

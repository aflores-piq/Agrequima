import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatUSD, formatUSDAbrev } from "../../utils/format";

// Tremor resuelve estos nombres de color a su escala "500"; se replican
// en hex porque este gráfico usa Recharts directamente (para poder
// agregar las etiquetas permanentes sobre cada barra).
const COLOR_HEX: Record<string, string> = {
  teal: "#14b8a6",
  orange: "#f97316",
  slate: "#64748b",
};

/** Comparación año actual vs. año anterior (mensual o por categoría).
 * Cada barra lleva su valor en CIF USD (formato abreviado) visible
 * permanentemente arriba, además del tooltip al pasar el mouse. */
export function ComparativeBarChart({
  data,
  index,
  categories,
  colors,
}: {
  data: Record<string, string | number>[];
  index: string;
  /** Orden de las barras/leyenda, de izquierda a derecha (Plaguicidas:
   * año anterior primero, como en Power BI; ver DashboardPlaguicidasPage). */
  categories: [string, string];
  /** Un color por posición en `categories` (no por año fijo) — el año
   * anterior siempre queda en gris neutro, el actual usa el acento del
   * dashboard, en la posición que le corresponda según `categories`. */
  colors: [string, string];
}) {
  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={288}>
      <RechartsBarChart data={data} margin={{ top: 24, right: 8, bottom: 4, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--color-line))" vertical={false} />
        <XAxis dataKey={index} stroke="rgb(var(--color-ink-faint))" fontSize={12} tickLine={false} />
        <YAxis
          tickFormatter={(v: number) => formatUSDAbrev(v)}
          stroke="rgb(var(--color-ink-faint))"
          fontSize={12}
          tickLine={false}
          width={70}
        />
        <Tooltip
          cursor={{ fill: "rgb(var(--color-ink-faint) / 0.08)" }}
          contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
          labelStyle={{ color: "rgb(var(--color-ink))" }}
          itemStyle={{ color: "rgb(var(--color-ink))" }}
          formatter={(value: number) => formatUSD(value)}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {categories.map((categoria, i) => (
          <Bar key={categoria} dataKey={categoria} fill={COLOR_HEX[colors[i]] ?? colors[i]} radius={[3, 3, 0, 0]}>
            <LabelList
              dataKey={categoria}
              position="top"
              formatter={(v: number) => formatUSDAbrev(v)}
              fill="rgb(var(--color-ink-muted))"
              fontSize={10}
            />
          </Bar>
        ))}
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}

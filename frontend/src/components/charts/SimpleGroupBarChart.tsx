import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatQ, formatQAbrev } from "../../utils/format";

/** Gráfico de barras agrupadas simple, una sola serie (grupo -> monto en
 * Quetzales). Reemplazo del visual libre (Deneb) de Power BI para las
 * cascadas de Ingresos/Egresos por grupo del dashboard Financiero -- ver
 * nota en el pedido original: "sin tipo estándar determinable, usá por
 * ahora un gráfico de barras agrupadas simple con la misma serie de
 * datos". */
export function SimpleGroupBarChart({ data, color = "#3b82f6" }: { data: { grupo: string; monto: number }[]; color?: string }) {
  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={288}>
      <RechartsBarChart data={data} margin={{ top: 24, right: 8, bottom: 4, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--color-line))" vertical={false} />
        <XAxis
          dataKey="grupo"
          stroke="rgb(var(--color-ink-faint))"
          fontSize={11}
          tickLine={false}
          interval={0}
          angle={-15}
          textAnchor="end"
          height={50}
        />
        <YAxis
          tickFormatter={(v: number) => formatQAbrev(v)}
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
          formatter={(value: number) => formatQ(value)}
        />
        <Bar dataKey="monto" fill={color} radius={[3, 3, 0, 0]}>
          <LabelList
            dataKey="monto"
            position="top"
            formatter={(v: number) => formatQAbrev(v)}
            fill="rgb(var(--color-ink-muted))"
            fontSize={10}
          />
        </Bar>
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}

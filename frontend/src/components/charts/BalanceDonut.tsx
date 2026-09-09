import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { formatQAbrev } from "../../utils/format";
import type { DistribucionBalanceItem } from "../../types/dashboardFinanciero";

const COLOR_POR_ETIQUETA: Record<string, string> = {
  Activo: "#3b82f6",
  Pasivo: "#f97316",
  Patrimonio: "#22c55e",
  "Fondos por aplicar": "#a78bfa",
};

/** Dona de distribución del balance (Activo/Pasivo/Patrimonio/Fondos por
 * aplicar) -- mismo criterio que CategoricalDonut (Recharts directo, no
 * <DonutChart> de Tremor, por el mismo problema de fill con colores
 * hex arbitrarios), pero con colores fijos por categoría en vez de por
 * posición de rank. */
export function BalanceDonut({ data }: { data: DistribucionBalanceItem[] }) {
  const conMonto = data.filter((d) => d.monto !== 0);
  if (conMonto.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  const total = conMonto.reduce((acc, d) => acc + Math.abs(d.monto), 0) || 1;

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-1 flex-col items-center justify-center gap-4 sm:flex-row">
        <div className="relative h-40 w-40 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={conMonto}
                dataKey={(d: DistribucionBalanceItem) => Math.abs(d.monto)}
                nameKey="etiqueta"
                cx="50%"
                cy="50%"
                startAngle={90}
                endAngle={-270}
                innerRadius="70%"
                outerRadius="100%"
                stroke="rgb(var(--color-bg-surface))"
                strokeWidth={2}
                isAnimationActive={false}
              >
                {conMonto.map((item) => (
                  <Cell key={item.etiqueta} fill={COLOR_POR_ETIQUETA[item.etiqueta] ?? "#64748b"} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => formatQAbrev(value)}
                contentStyle={{
                  background: "rgb(var(--color-bg-surface))",
                  border: "1px solid rgb(var(--color-line))",
                  borderRadius: 8,
                }}
                labelStyle={{ color: "rgb(var(--color-ink))" }}
                itemStyle={{ color: "rgb(var(--color-ink))" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <ul className="min-w-0 flex-1 space-y-6">
          {conMonto.map((item) => (
            <li key={item.etiqueta} className="flex items-center gap-2 text-sm">
              <span
                className="h-3 w-3 shrink-0 rounded-sm"
                style={{ backgroundColor: COLOR_POR_ETIQUETA[item.etiqueta] ?? "#64748b" }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-ink">
                {item.etiqueta}
              </span>
              <span className="w-10 shrink-0 text-right font-semibold text-blue-400">
                {Math.round((Math.abs(item.monto) / total) * 100)}%
              </span>
              <span className="w-16 shrink-0 text-right text-ink-muted">{formatQAbrev(item.monto)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

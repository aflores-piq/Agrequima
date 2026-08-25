import {
  CartesianGrid,
  Legend,
  Line,
  LineChart as RechartsLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardTheme } from "../../theme/colors";
import { colorIntensidad } from "../../theme/colors";
import { formatUSD, formatUSDAbrev, MESES } from "../../utils/format";
import type { SerieAcumuladoAnual } from "../../types/dashboard";

/** Forma de marcador por antigüedad (no por valor): el año seleccionado
 * siempre es círculo, el anterior siempre cuadrado, etc. — sirve tanto
 * para dibujar el punto en la línea como para el ícono en la leyenda
 * (Recharts usa el mismo nombre para `legendType`). */
type FormaMarcador = "circle" | "square" | "diamond" | "triangle" | "cross";
const FORMAS_POR_ANTIGUEDAD: FormaMarcador[] = ["circle", "square", "diamond", "triangle", "cross"];

function MarcadorForma({
  cx,
  cy,
  forma,
  color,
}: {
  cx: number;
  cy: number;
  forma: FormaMarcador;
  color: string;
}) {
  const r = 4;
  switch (forma) {
    case "circle":
      return <circle cx={cx} cy={cy} r={r} fill={color} />;
    case "square":
      return <rect x={cx - r} y={cy - r} width={r * 2} height={r * 2} fill={color} />;
    case "diamond":
      return (
        <polygon
          points={`${cx},${cy - r * 1.3} ${cx + r * 1.3},${cy} ${cx},${cy + r * 1.3} ${cx - r * 1.3},${cy}`}
          fill={color}
        />
      );
    case "triangle":
      return (
        <polygon
          points={`${cx},${cy - r * 1.3} ${cx + r * 1.2},${cy + r} ${cx - r * 1.2},${cy + r}`}
          fill={color}
        />
      );
    case "cross":
      return (
        <g stroke={color} strokeWidth={2} strokeLinecap="round">
          <line x1={cx - r} y1={cy - r} x2={cx + r} y2={cy + r} />
          <line x1={cx - r} y1={cy + r} x2={cx + r} y2={cy - r} />
        </g>
      );
  }
}

/** Comparativo acumulado de CIF USD por año: una línea por cada año de
 * la ventana (año seleccionado + hasta 4 anteriores) que tenga datos —
 * en una rampa de un solo tono, no colores categóricos: el año
 * seleccionado (primero en `series`, ver backend) en el tono más
 * fuerte, los anteriores progresivamente más claros. Cada línea además
 * lleva su propia forma de marcador (por antigüedad, no por valor) para
 * distinguirlas incluso si el color se percibe parecido. */
export function MultiAnnualLineChart({
  theme,
  series,
}: {
  theme: DashboardTheme;
  series: SerieAcumuladoAnual[];
}) {
  if (series.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  const totalMeses = series[0]?.puntos.length ?? 0;
  const data = Array.from({ length: totalMeses }, (_, i) => {
    const fila: Record<string, string | number | null> = { mes: MESES[i] };
    for (const serie of series) {
      fila[String(serie.anio)] = serie.puntos[i]?.cif_usd_acumulado ?? null;
    }
    return fila;
  });

  const n = series.length;

  return (
    <ResponsiveContainer width="100%" height={288}>
      <RechartsLineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--color-line))" />
        <XAxis dataKey="mes" stroke="rgb(var(--color-ink-faint))" fontSize={12} tickLine={false} />
        <YAxis
          tickFormatter={(v: number) => formatUSDAbrev(v)}
          stroke="rgb(var(--color-ink-faint))"
          fontSize={12}
          tickLine={false}
          width={70}
        />
        <Tooltip
          contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
          labelStyle={{ color: "rgb(var(--color-ink))" }}
          itemStyle={{ color: "rgb(var(--color-ink))" }}
          formatter={(value: number) => formatUSD(value)}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((serie, i) => {
          const color = colorIntensidad(theme, (n - i) / n);
          const forma = FORMAS_POR_ANTIGUEDAD[i] ?? "circle";
          return (
            <Line
              key={serie.anio}
              type="monotone"
              dataKey={String(serie.anio)}
              name={String(serie.anio)}
              stroke={color}
              strokeWidth={2}
              dot={(props: any) => (
                <MarcadorForma key={props.key ?? props.index} cx={props.cx} cy={props.cy} forma={forma} color={color} />
              )}
              activeDot={{ r: 5 }}
              legendType={forma}
              connectNulls={false}
              isAnimationActive={false}
            />
          );
        })}
      </RechartsLineChart>
    </ResponsiveContainer>
  );
}

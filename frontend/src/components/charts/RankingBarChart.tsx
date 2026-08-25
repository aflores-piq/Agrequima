import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardTheme } from "../../theme/colors";
import { colorIntensidad } from "../../theme/colors";
import { formatUSD, formatUSDAbrev } from "../../utils/format";
import type { RankingItem } from "../../types/dashboard";

const MAX_CHARS_POR_LINEA = 20;
const MAX_LINEAS = 2;

function envolverEtiqueta(texto: string): string[] {
  const palabras = texto.split(" ");
  const lineas: string[] = [];
  let actual = "";
  for (const palabra of palabras) {
    const candidata = actual ? `${actual} ${palabra}` : palabra;
    if (candidata.length > MAX_CHARS_POR_LINEA && actual) {
      lineas.push(actual);
      actual = palabra;
    } else {
      actual = candidata;
    }
  }
  if (actual) lineas.push(actual);

  if (lineas.length > MAX_LINEAS) {
    const visibles = lineas.slice(0, MAX_LINEAS);
    visibles[MAX_LINEAS - 1] = `${visibles[MAX_LINEAS - 1].slice(0, MAX_CHARS_POR_LINEA - 1)}…`;
    return visibles;
  }
  return lineas;
}

/** Tick de YAxis con wrapping manual (vía <tspan>): evita que los
 * nombres largos de empresa se corten o se superpongan entre barras. */
function TickEtiquetaEnvuelta({ x, y, payload }: any) {
  const lineas = envolverEtiqueta(String(payload.value));
  const alturaLinea = 12;
  const dyInicial = -((lineas.length - 1) * alturaLinea) / 2;
  return (
    <text x={x} y={y} textAnchor="end" fill="rgb(var(--color-ink-faint))" fontSize={11}>
      {lineas.map((linea, i) => (
        <tspan key={i} x={x} dy={i === 0 ? dyInicial : alturaLinea}>
          {linea}
        </tspan>
      ))}
    </text>
  );
}

/** Ranking de magnitud (top ingredientes/importadores/países/fórmulas):
 * un solo hue en escala de intensidad según el valor relativo de cada
 * barra, NO un color distinto por categoría. Tremor's BarChart no expone
 * color por barra individual, así que este caso puntual usa Recharts
 * directamente. */
export function RankingBarChart({ theme, data }: { theme: DashboardTheme; data: RankingItem[] }) {
  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  const max = Math.max(1, ...data.map((d) => d.cif_usd));

  return (
    // h-full deja que la tarjeta (ChartCard) estire el alto real de dibujo
    // cuando queda junto a una tabla más alta, en vez de dejar un hueco
    // vacío debajo de un alto fijo. minHeight en ResponsiveContainer (no
    // solo la clase CSS) es necesario: Recharts mide su propio contenedor
    // una sola vez al montar, y si en ese instante el alto heredado por
    // flexbox todavía no se resolvió, se queda con un SVG de 0px para
    // siempre (nunca hay un resize real que lo despierte). El prop aplica
    // un min-height real al div que Recharts observa, evitando esa carrera.
    <div className="h-full min-h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%" minHeight={320}>
        <RechartsBarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--color-line))" horizontal={false} />
          <XAxis
            type="number"
            tickFormatter={(v: number) => formatUSDAbrev(v)}
            stroke="rgb(var(--color-ink-faint))"
            fontSize={12}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="etiqueta"
            width={170}
            tick={<TickEtiquetaEnvuelta />}
            tickLine={false}
            interval={0}
          />
          <Tooltip
            cursor={{ fill: "rgb(var(--color-ink-faint) / 0.08)" }}
            contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
            labelStyle={{ color: "rgb(var(--color-ink))" }}
            itemStyle={{ color: "rgb(var(--color-ink))" }}
            formatter={(value: number) => [formatUSD(value), "CIF USD"]}
          />
          <Bar dataKey="cif_usd" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => (
              <Cell key={`${d.etiqueta}-${i}`} fill={colorIntensidad(theme, d.cif_usd / max)} />
            ))}
          </Bar>
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}

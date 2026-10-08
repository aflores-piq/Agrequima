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
import { tooltipFinanciero } from "./TooltipFinanciero";
import { DOMINIO_AUTO_SIN_RECORTAR_NEGATIVOS } from "../../utils/escalaEje";
import { formatQ } from "../../utils/format";

// Colores reales leídos de las capturas del reporte viejo (no los 3
// colores por categoría que se habían pedido en texto -- un gráfico de
// barras agrupadas por AÑO solo puede colorear por serie/año, no por
// categoría Y por año a la vez; la captura real confirma que así es:
// mismos 2 colores en las páginas 2 y 4, sin importar la categoría).
const COLOR_ANIO_ANTERIOR = "#5b7fae";
const COLOR_ANIO_ACTUAL = "#43b0a6";

/** Barras agrupadas, 2 series (año anterior / año actual) x 3
 * categorías -- páginas 2 y 4 del dashboard Financiero. */
export function ComparativoAnioBarChart({
  data,
  etiquetaAnioAnterior,
  etiquetaAnioActual,
  altura = 288,
}: {
  data: Record<string, string | number>[];
  etiquetaAnioAnterior: string;
  etiquetaAnioActual: string;
  altura?: number;
}) {
  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  return (
    // Envoltorio propio w-full/h-full: Recharts mide su contenedor
    // inmediato una sola vez al montar (ver RankingBarChart.tsx) -- sin
    // este div, si el ancho heredado por flex/grid todavía no se
    // resolvió en ese instante, el SVG puede quedar en 0px sin que un
    // resize posterior lo corrija.
    <div className="h-full w-full" style={{ minHeight: altura }}>
      <ResponsiveContainer width="100%" height="100%" minHeight={altura}>
        <RechartsBarChart data={data} margin={{ top: 28, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--color-line))" vertical={false} />
        <XAxis dataKey="categoria" stroke="rgb(var(--color-ink))" fontSize={12} tickLine={false} />
        <YAxis
          domain={DOMINIO_AUTO_SIN_RECORTAR_NEGATIVOS}
          tickFormatter={(v: number) => formatQ(v)}
          stroke="rgb(var(--color-ink))"
          fontSize={12}
          tickLine={false}
          width={95}
        />
        <Tooltip {...tooltipFinanciero({ formatter: (value) => formatQ(value) })} />
        <Legend wrapperStyle={{ fontSize: 12, color: "rgb(var(--color-ink))" }} />
        <Bar dataKey={etiquetaAnioAnterior} name={etiquetaAnioAnterior} fill={COLOR_ANIO_ANTERIOR} radius={[3, 3, 0, 0]}>
          <LabelList dataKey={etiquetaAnioAnterior} position="top" formatter={(v: number) => formatQ(v)} fill="rgb(var(--color-ink))" fontSize={13} fontWeight={600} />
        </Bar>
        <Bar dataKey={etiquetaAnioActual} name={etiquetaAnioActual} fill={COLOR_ANIO_ACTUAL} radius={[3, 3, 0, 0]}>
          <LabelList dataKey={etiquetaAnioActual} position="top" formatter={(v: number) => formatQ(v)} fill="rgb(var(--color-ink))" fontSize={13} fontWeight={600} />
        </Bar>
      </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}

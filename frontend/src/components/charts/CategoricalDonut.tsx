import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { formatUSDCorto } from "../../utils/format";
import type { RankingItem } from "../../types/dashboard";

// Paleta y formato calcados del spec exacto de Power BI para este
// gráfico puntual: a diferencia del resto de la app, aquí el color NO
// es fijo por categoría — se asigna por posición de rank (1er lugar
// por CIF siempre el primer color, etc.), porque el backend ya entrega
// como máximo 5 filas ordenadas desc por CIF (ver df_por_aplicacion).
//
// Se usa Recharts directamente (no <DonutChart> de Tremor): Tremor
// pinta cada arco con `fill: ""` y depende de una clase Tailwind
// generada a partir de un nombre de color CONOCIDO por Tremor
// (ver inputParser.js: getColorClassNames(color, ...).fillColor) — un
// hex arbitrario como "#1ED9B6" no matchea ningún color reconocido, no
// genera ninguna clase real, y el <path> queda sin fill efectivo (el
// navegador lo pinta negro por defecto). Mismo motivo que ya obligó a
// usar Recharts directo en RankingBarChart.tsx.
const PALETA_RANK = ["#1ED9B6", "#F59E0B", "#3B82F6", "#A78BFA", "#F87171"];

/** Dona de distribución por tipo de aplicación — Top 5 por CIF USD.
 * Centro con el conteo de categorías mostradas, leyenda a la derecha
 * con nombre + porcentaje + CIF USD, cada fila en una sola línea.
 *
 * `totalReal` es el CIF USD de TODAS las categorías de aplicación (las
 * 10 de clasificar_aplicacion), no la suma de las 5 que se muestran acá
 * — el backend ya lo expone como kpis.cif_total_usd (idéntico a
 * ctx.cif_total en dashboard_plaguicidas.py, verificado). El porcentaje
 * de estas 5 debe sumar MENOS de 100%, reflejando que hay categorías no
 * mostradas; dividir entre la suma de las 5 (como se hacía antes)
 * infla artificialmente el porcentaje de cada una hasta sumar 100%. */
export function CategoricalDonut({ data, totalReal }: { data: RankingItem[]; totalReal: number }) {
  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  const total = totalReal || 1;

  return (
    // h-full: esta tarjeta comparte fila de grid con "Top 20 moléculas"
    // (RankingBarChart), que fuerza su propio alto según su cantidad de
    // filas (ver ALTO_POR_FILA en RankingBarChart.tsx) — el grid por
    // defecto (align-items: stretch) iguala el alto de ambas tarjetas,
    // así que ésta debe llenar ese mismo alto con su propio contenido
    // (anillo y espaciado de leyenda más grandes) en vez de calcular su
    // propio alto — igual que ya se decidió para "Top importadores"/
    // "Top países de origen" en su fila.
    <div className="flex h-full flex-col">
      {/* min-w-0 en el <ul>: sin esto, un flex item nunca se encoge más
          allá del ancho mínimo de su contenido (min-width:auto es el
          default), así que el renglón total (anillo + leyenda) podía medir
          más que el ancho real de la tarjeta y desbordarse — el anillo
          hacia la izquierda, la leyenda hacia la derecha (esto SÍ pasaba,
          ver getBoundingClientRect en la verificación). shrink-0 en el
          anillo + flex-1 min-w-0 en la leyenda garantiza que la suma de
          ambos SIEMPRE sea exactamente el ancho disponible, nunca más. */}
      <div className="flex flex-1 flex-col items-center justify-center gap-4 sm:flex-row">
        <div className="relative h-40 w-40 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="cif_usd"
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
                {data.map((item, i) => (
                  <Cell key={item.etiqueta} fill={PALETA_RANK[i % PALETA_RANK.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => formatUSDCorto(value)}
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
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-bold text-ink">{data.length}</span>
            <span className="text-[10px] text-ink-faint">tipos</span>
          </div>
        </div>
        <ul className="min-w-0 flex-1 space-y-6">
          {data.map((item, i) => (
            <li key={item.etiqueta} className="flex items-center gap-2 text-sm">
              <span
                className="h-3 w-3 shrink-0 rounded-sm"
                style={{ backgroundColor: PALETA_RANK[i % PALETA_RANK.length] }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-ink" title={item.etiqueta}>
                {item.etiqueta}
              </span>
              <span className="w-10 shrink-0 text-right font-semibold text-teal-400">
                {Math.round((item.cif_usd / total) * 100)}%
              </span>
              <span className="w-14 shrink-0 text-right text-ink-muted">{formatUSDCorto(item.cif_usd)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

import { useMemo } from "react";
import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardTheme } from "../../theme/colors";
import { colorIntensidad } from "../../theme/colors";
import { formatUSD, formatUSDAbrev, formatUSDCorto } from "../../utils/format";
import type { RankingItem } from "../../types/dashboard";

// Tope del ancho del nombre: 190 - 6 px de espacio número/nombre, para que el
// eje (y por lo tanto el largo de las barras) no crezca más que antes en los
// rankings con nombres largos; esos nombres se cortan con "…" 6 px antes.
const ANCHO_ETIQUETA_MAX = 184;
const FUENTE_TICK = "10px sans-serif";
const MARGEN_DERECHO_MINIMO = 8;
const ALTO_TICK = 18;
// Columna del número de posición (1..20), pegada al borde izquierdo del eje,
// de ancho fijo y alineada a la derecha para que los dígitos queden uno debajo
// del otro (igual que la columna "#" de las tablas Top N). Entre el número y
// el nombre hay un espacio mínimo fijo (~2-3 espacios): si el nombre es corto
// y sobra lugar, la separación es mayor (el nombre sigue alineado a la derecha).
const ANCHO_CAJA_NUMERO = 20;
const ESPACIO_NUMERO_NOMBRE = 8;
const ANCHO_COLUMNA_NUMERO = ANCHO_CAJA_NUMERO + ESPACIO_NUMERO_NOMBRE;
// Alto mínimo por fila para que el texto en una sola línea no se
// encimice con la barra vecina — con 20 elementos esto hace que la
// tarjeta sea más alta que un gráfico simple, a propósito (ver
// DashboardPlaguicidasPage: los rankings de 20 elementos no comparten
// el alto estándar de 400px de los demás gráficos).
const ALTO_POR_FILA = 24;
const ALTO_MARGENES = 48; // CartesianGrid/XAxis/márgenes del BarChart
const ALTO_MINIMO = 288; // piso para rankings con pocos elementos

let canvasMedicion: HTMLCanvasElement | null = null;

/** Ancho real (px) que ocupa un texto con la misma fuente del tick, vía
 * un <canvas> descartable — no hay forma de medir texto sin tocar el DOM
 * o el canvas; esto evita crear/montar nodos reales solo para medir. */
function medirAnchoTexto(texto: string): number {
  if (!canvasMedicion) canvasMedicion = document.createElement("canvas");
  const ctx = canvasMedicion.getContext("2d")!;
  ctx.font = FUENTE_TICK;
  return ctx.measureText(texto).width;
}

/** Etiqueta de valor en una columna FIJA (misma x para las 20 filas),
 * no pegada al final de cada barra — igual que la referencia de Power
 * BI. Recharts inyecta x/width con la geometría real de ESTA barra (el
 * layout vertical siempre arranca las barras en el mismo x, sólo cambia
 * `width` según el valor); como el dominio del eje es [0, max], para
 * CUALQUIER fila `x + width * (max / value)` da exactamente el borde
 * derecho de la barra más larga — la misma x para las 20, sin necesidad
 * de leer el scale interno de Recharts. */
function EtiquetaValorFija({ x, y, width, height, value, max }: any) {
  const escala = value > 0 ? max / value : 1;
  const xColumna = x + width * escala;
  return (
    <text
      x={xColumna + 4}
      y={y + height / 2}
      dy={3.5}
      textAnchor="start"
      fontSize={10}
      fill="rgb(var(--color-ink-faint))"
    >
      {formatUSDCorto(value)}
    </text>
  );
}

/** Tick de YAxis de UNA sola línea, truncado con "…" si no cabe en el
 * ancho fijo (foreignObject + CSS real: white-space/overflow/text-
 * overflow, no tspans partidos a mano) — así es imposible que el texto
 * se encimice con la barra de al lado sin importar el largo del
 * nombre. El nombre completo queda disponible en el tooltip nativo del
 * <div> (title) y en el tooltip del gráfico al pasar sobre la barra. */
function TickEtiquetaTruncada({ x, y, payload, anchoEtiqueta, index }: any) {
  const texto = String(payload.value);
  // El número va en su propia caja, de ancho fijo, justo a la izquierda de la
  // caja del nombre (que queda como siempre: alineada a la derecha, truncada
  // con "…"), o sea pegada al borde izquierdo de la gráfica. Así el número
  // nunca se recorta por un nombre largo y los dígitos quedan alineados.
  const xBordeIzquierdoEje = x - anchoEtiqueta - 4 - ANCHO_COLUMNA_NUMERO;
  return (
    <>
      <foreignObject x={xBordeIzquierdoEje} y={y - ALTO_TICK / 2} width={ANCHO_CAJA_NUMERO} height={ALTO_TICK}>
        <div
          style={{
            textAlign: "right",
            fontSize: "10px",
            lineHeight: `${ALTO_TICK}px`,
            fontVariantNumeric: "tabular-nums",
            color: "rgb(var(--color-ink-faint))",
          }}
        >
          {(index ?? 0) + 1}
        </div>
      </foreignObject>
      <foreignObject x={x - anchoEtiqueta - 4} y={y - ALTO_TICK / 2} width={anchoEtiqueta} height={ALTO_TICK}>
        <div
          title={texto}
          style={{
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            textAlign: "right",
            fontSize: "10px",
            lineHeight: `${ALTO_TICK}px`,
            color: "rgb(var(--color-ink-faint))",
          }}
        >
          {texto}
        </div>
      </foreignObject>
    </>
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
  const alto = Math.max(ALTO_MINIMO, data.length * ALTO_POR_FILA + ALTO_MARGENES);
  // Ancho de la columna de etiquetas ajustado al nombre MÁS LARGO de
  // ESTE gráfico en particular (no un valor fijo compartido entre
  // gráficos): "Top 20 moléculas" tiene nombres cortos y no debe reservar
  // el mismo espacio que "Top 20 importadores", que sí tiene razones
  // sociales largas — un ancho fijo dejaba un hueco vacío entre el texto
  // y el inicio de la barra en el gráfico de nombres cortos. Tope máximo
  // en ANCHO_ETIQUETA_MAX: los pocos nombres extremos de cada gráfico se
  // siguen truncando con "…" en vez de deformar el layout.
  const anchoEtiqueta = useMemo(() => {
    const anchoMaximoNecesario = Math.max(...data.map((d) => medirAnchoTexto(d.etiqueta)));
    return Math.min(ANCHO_ETIQUETA_MAX, Math.ceil(anchoMaximoNecesario) + 2);
  }, [data]);
  // Margen derecho ajustado al valor MÁS ANCHO de este gráfico (ej.
  // "$13.8M" ~7 caracteres) — igual que anchoEtiqueta, no un valor fijo:
  // solo reserva el espacio real que la etiqueta de valor necesita para
  // no recortarse contra el borde del SVG, sin quitarle más espacio del
  // necesario a las barras.
  const margenDerecho = useMemo(() => {
    const anchoValorMasAncho = Math.max(...data.map((d) => medirAnchoTexto(formatUSDCorto(d.cif_usd))));
    return Math.max(MARGEN_DERECHO_MINIMO, Math.ceil(anchoValorMasAncho) + 4);
  }, [data]);

  return (
    // h-full deja que la tarjeta (ChartCard) estire el alto real de dibujo
    // cuando queda junto a una tabla más alta, en vez de dejar un hueco
    // vacío debajo de un alto fijo. minHeight en ResponsiveContainer (no
    // solo la clase CSS) es necesario: Recharts mide su propio contenedor
    // una sola vez al montar, y si en ese instante el alto heredado por
    // flexbox todavía no se resolvió, se queda con un SVG de 0px para
    // siempre (nunca hay un resize real que lo despierte). El prop aplica
    // un min-height real al div que Recharts observa, evitando esa carrera.
    // `alto` depende de la cantidad de filas (no un valor fijo): con 20
    // elementos necesita más espacio que el alto estándar de 400px de un
    // gráfico simple para que cada fila tenga suficiente alto y el texto
    // en una sola línea no se encimice con la barra vecina — no se
    // comprime de vuelta al estándar a costa de la legibilidad.
    <div className="h-full w-full" style={{ minHeight: alto }}>
      <ResponsiveContainer width="100%" height="100%" minHeight={alto}>
        <RechartsBarChart data={data} layout="vertical" margin={{ top: 4, right: margenDerecho, bottom: 4, left: 6 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--color-line))" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, "dataMax"]}
            tickFormatter={(v: number) => formatUSDAbrev(v)}
            stroke="rgb(var(--color-ink-faint))"
            fontSize={12}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="etiqueta"
            width={anchoEtiqueta + 6 + ANCHO_COLUMNA_NUMERO}
            tick={<TickEtiquetaTruncada anchoEtiqueta={anchoEtiqueta} />}
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
            <LabelList dataKey="cif_usd" content={<EtiquetaValorFija max={max} />} />
          </Bar>
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}

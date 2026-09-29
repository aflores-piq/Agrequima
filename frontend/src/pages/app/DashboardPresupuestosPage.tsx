import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Title } from "@tremor/react";
import { Bar, BarChart, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  obtenerComparativoEjecutado,
  obtenerEjecucionVsPresupuesto,
  obtenerEjecucionVsPresupuestoAcumulado,
} from "../../api/dashboardOtrosInformes";
import { mensajeError } from "../../api/client";
import { useFinancieroFilterGrupo1 } from "../../financiero/FinancieroFilterContext";
import { FilterYearMonth } from "../../components/filters/PowerBiFilter";
import { EncabezadoOrdenable } from "../../components/EncabezadoOrdenable";
import { useTablaOrdenable, type ColumnaOrdenable } from "../../hooks/useTablaOrdenable";
import { FINANCIERO_SURFACE, VERDE_ENCABEZADO } from "../../components/TablaGrupoExpandible";
import { COLOR_EJECUTADO, COLOR_PRESUPUESTO, ultimoDiaDelMes } from "./DashboardOtrosInformesPage";
import { formatPercent, formatPercent2, formatQ, MESES_LARGOS } from "../../utils/format";
import type {
  ComparativoEjecutadoResponse,
  EjecucionVsPresupuestoResponse,
  FilaComparativoEjecutado,
  FilaPresupuesto,
} from "../../types/dashboardOtrosInformes";

// Ancho de barra ~12% del ancho de la tarjeta (calcado del "size":125 en
// un visual Deneb de 1062px del .pbix real, ≈12%) -- NO se puede lograr
// con `barCategoryGap`/`barGap` en porcentaje: con una sola categoría
// falsa (1 fila de datos), el algoritmo de bandas de Recharts/d3 se
// comporta de forma no lineal y hasta no monótona con esos props
// (calibrado a mano probando varios valores, confirmado con
// getBoundingClientRect real en el navegador -- 40%→8.5%, 49%→0.6%,
// 76%→22.8%, 87%→32.4% del ancho del SVG, sin relación lineal ni
// monótona). En cambio, se mide el ancho real de la tarjeta con
// ResizeObserver y se pasa `barSize` (píxeles) calculado como el 12% de
// ese ancho medido -- exacto y estable a cualquier tamaño de pantalla.
function useAnchoElemento<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [ancho, setAncho] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setAncho(entry.contentRect.width);
    });
    observer.observe(el);
    setAncho(el.getBoundingClientRect().width);
    return () => observer.disconnect();
  }, []);
  return [ref, ancho] as const;
}

// Leyenda propia (NO el <Legend> de Recharts): el componente de Recharts
// centra su leyenda respecto del ancho TOTAL del SVG, pero acá el eje Y
// solo ocupa espacio a la izquierda (no hay eje derecho que lo
// espeje) -- eso deja al PAR DE BARRAS centrado en un área más angosta
// que el SVG completo, corrida hacia la derecha, mientras el <Legend>
// de Recharts queda centrado en el SVG completo, sin coincidir con las
// barras (confirmado midiendo con getBoundingClientRect: desfasaje de
// hasta 56px, la mitad del ancho del eje Y). En vez de pelear con el
// algoritmo interno de Recharts, se calcula a mano el centro real del
// par de barras (mismo cálculo de gutters que usa el propio BarChart:
// `margin.left + anchoEjeY` a la izquierda, `margin.right` a la
// derecha) y se posiciona esta leyenda ahí mismo con
// `left: centro; transform: translateX(-50%)`.
function LeyendaCentrada({
  anchoTarjeta,
  gutterIzquierdo,
  gutterDerecho,
  items,
}: {
  anchoTarjeta: number;
  gutterIzquierdo: number;
  gutterDerecho: number;
  items: { etiqueta: string; color: string }[];
}) {
  const centro = gutterIzquierdo + (anchoTarjeta - gutterIzquierdo - gutterDerecho) / 2;
  return (
    <div className="relative h-7">
      <div
        data-testid="leyenda-centrada"
        className="absolute top-0 flex items-center gap-4 whitespace-nowrap text-base font-bold text-ink"
        style={{ left: centro, transform: "translateX(-50%)" }}
      >
        {items.map((it) => (
          <span key={it.etiqueta} className="flex items-center gap-1.5">
            <span aria-hidden="true" className="inline-block h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: it.color }} />
            {it.etiqueta}
          </span>
        ))}
      </div>
    </div>
  );
}

// Verde real de las diferencias negativas en "Ejecucion vs Presupuesto"
// (mensual) -- confirmado en el Layout.json real: una regla de formato
// condicional `Diferencia < 0 -> '#4BD72C'` en el objeto `values` de la
// tabla. "Ejecucion vs Presupuesto Acumulado" NO tiene ese objeto en su
// Layout.json -- confirmado que las negativas van en blanco ahí, no es
// una omisión.
const COLOR_DIFERENCIA_NEGATIVA = "#4BD72C";

// Anchos reales medidos del .pbix (Report/Layout: tableEx/
// clusteredColumnChart, canvas 1920px, menú 262px, área de contenido
// 1658px). Mensual: tabla y gráfica miden EXACTAMENTE lo mismo (w=1050px
// las 2) -- acumulado casi lo mismo pero no idéntico (w=1046 tabla /
// w=1048 gráfica, confirmado con 2 columnWidth reales distintos), así
// que cada uno tiene su propio %.
const ANCHO_MENSUAL = "63.3%"; // 1050/1658, tabla Y gráfica
const ANCHO_TABLA_ACUMULADO = "63.1%"; // 1046/1658
const ANCHO_GRAFICA_ACUMULADO = "63.2%"; // 1048/1658

// Separación tabla-gráfica real del .pbix (Report/Layout, distancia en Y
// entre el final del tableEx y el inicio del clusteredColumnChart/deneb
// de cada página), expresada como % del ancho del área de contenido --
// NO como % de una altura, a propósito: un margin-top/bottom en % de
// CSS se resuelve siempre contra el ANCHO del contenedor (una regla real
// de CSS, no un error), así que un valor como "3.0%" en `marginTop` ya
// da exactamente lo pedido sin ningún cálculo en JS.
// Mensual: 50px de 1658px = 3.0%. Acumulado: 56px = 3.4%.
// Comparativo: 45px = 2.7%.
const MARGEN_TABLA_GRAFICA_MENSUAL = "3.0%";
const MARGEN_TABLA_GRAFICA_ACUMULADO = "3.4%";
const MARGEN_TABLA_GRAFICA_COMPARATIVO = "2.7%";

// Relación alto/ancho de CADA TARJETA completa (recuadro gris con
// título+gráfica+leyenda, no solo el SVG): 0.38 -- decisión de diseño
// propia pedida por el usuario (ya no la proporción real del .pbix, que
// era ~0.47/0.48).
//
// El `aspect` de ResponsiveContainer solo controla el alto del <svg> --
// el título (pt-2 de la tarjeta + line-height de text-base, ~32px) y la
// leyenda propia (h-7, 28px) suman una altura EXTRA fija encima de eso,
// así que fijar `aspect` a un valor constante (1/0.38) NO da 0.38 en la
// tarjeta completa (medido: daba ~0.445, no 0.38 -- confirmado con
// getBoundingClientRect). Por eso el aspecto del <svg> se calcula acá
// mismo, DESPEJANDO la altura extra: si se quiere
// altoTarjeta = 0.38 * anchoTarjeta, y altoTarjeta = altoSvg + EXTRA,
// entonces altoSvg = 0.38*anchoTarjeta - EXTRA, y
// aspecto = anchoTarjeta / altoSvg.
const PROPORCION_ALTO_ANCHO_TARJETA = 0.38;
const ALTO_EXTRA_TITULO_LEYENDA = 60; // px: ~32 (título) + 28 (leyenda)

function calcularAspectoSvg(anchoTarjeta: number): number {
  if (!anchoTarjeta) return 1 / PROPORCION_ALTO_ANCHO_TARJETA;
  const altoSvgDeseado = PROPORCION_ALTO_ANCHO_TARJETA * anchoTarjeta - ALTO_EXTRA_TITULO_LEYENDA;
  return anchoTarjeta / Math.max(altoSvgDeseado, 1);
}

// Eje Y fijo por página -- valores dados directamente por el usuario
// (no son medidas DAX extraíbles del Layout.json, que solo trae texto/
// posición, no el dominio real del eje de un clusteredColumnChart).
const ESCALA_EJE_Y_PRESUPUESTO_MENSUAL = { max: 800_000, ticks: [0, 200_000, 400_000, 600_000, 800_000] };
const ESCALA_EJE_Y_PRESUPUESTO_ACUMULADO = { max: 8_000_000, ticks: [0, 2_000_000, 4_000_000, 6_000_000, 8_000_000] };

// Anchos de columna reales (Report/Layout, columnWidth en px, convertidos
// a % de la tabla): Gastos ~44%, el resto ~14% cada uno -- casi idénticos
// entre "Ejecucion vs Presupuesto" y su versión Acumulado (confirmado
// comparando los 2 columnWidth reales), así que comparten un solo array.
// Orden pedido por el usuario (Gastos | Presupuesto | Ejecutado |
// Diferencia Q. | Diferencia %), no el orden de Select del Layout (que
// no refleja el orden visual real de las columnas).
const ANCHOS_COLUMNA_PRESUPUESTO = ["44%", "15%", "14%", "13.5%", "13.5%"];

function ColgroupPresupuesto() {
  return (
    <colgroup>
      {ANCHOS_COLUMNA_PRESUPUESTO.map((ancho, i) => (
        <col key={i} style={{ width: ancho }} />
      ))}
    </colgroup>
  );
}

function FilaTablaPresupuesto({ fila, coloreVerdeNegativo }: { fila: FilaPresupuesto; coloreVerdeNegativo: boolean }) {
  const claseCelda = `px-2 py-1.5 text-sm text-ink ${fila.negrita ? "font-bold" : ""}`;
  const usaVerde = coloreVerdeNegativo && fila.diferencia < 0 && !fila.negrita;
  return (
    <tr style={{ backgroundColor: FINANCIERO_SURFACE }} className={fila.negrita ? "border-t border-line" : undefined}>
      <td className={claseCelda}>{fila.categoria}</td>
      <td className={`${claseCelda} text-right`}>{formatQ(fila.presupuesto)}</td>
      {/* Ejecutado vacío cuando es 0 (categorías con presupuesto pero sin
          movimiento ese período) -- Presupuesto SÍ muestra "Q0" literal,
          a diferencia de Ejecutado -- así lo pidió el usuario. */}
      <td className={`${claseCelda} text-right`}>{fila.ejecutado === 0 && !fila.negrita ? "" : formatQ(fila.ejecutado)}</td>
      <td className={`${claseCelda} text-right`} style={usaVerde ? { color: COLOR_DIFERENCIA_NEGATIVA } : undefined}>
        {formatQ(fila.diferencia)}
      </td>
      <td className={`${claseCelda} text-right`}>{formatPercent(fila.diferencia_pct)}</td>
    </tr>
  );
}

// Ejecutado===0 se muestra vacío (ver comentario en FilaTablaPresupuesto)
// -- para el orden se trata como vacío (null), igual que en pantalla.
const COLUMNAS_ORDENABLES_PRESUPUESTO: ColumnaOrdenable<FilaPresupuesto>[] = [
  { clave: "categoria", tipo: "texto", valor: (f) => f.categoria },
  { clave: "presupuesto", tipo: "numero", valor: (f) => f.presupuesto },
  { clave: "ejecutado", tipo: "numero", valor: (f) => (f.ejecutado === 0 ? null : f.ejecutado) },
  { clave: "diferencia", tipo: "numero", valor: (f) => f.diferencia },
  { clave: "diferencia_pct", tipo: "numero", valor: (f) => f.diferencia_pct },
];

function TablaPresupuesto({
  filas,
  filaTotal,
  coloreVerdeNegativo,
}: {
  filas: FilaPresupuesto[];
  filaTotal: FilaPresupuesto;
  coloreVerdeNegativo: boolean;
}) {
  const { filas: filasOrdenadas, alClickEncabezado, flechaColumna } = useTablaOrdenable(filas, COLUMNAS_ORDENABLES_PRESUPUESTO);
  // Encabezado alineado con su columna (texto a la izquierda, números a
  // la derecha, mismo padding que las celdas) -- antes todos centrados,
  // desalineados de los valores reales debajo.
  const claseHeaderTexto = "px-2 py-1.5 text-left text-white font-normal";
  const claseHeaderNumero = "px-2 py-1.5 text-right text-white font-normal";
  return (
    <div className="overflow-hidden rounded-tremor-default ring-1 ring-line">
      <table className="w-full text-sm">
        <ColgroupPresupuesto />
        <thead>
          <tr style={{ backgroundColor: VERDE_ENCABEZADO }}>
            <EncabezadoOrdenable className={claseHeaderTexto} flecha={flechaColumna("categoria")} onClick={() => alClickEncabezado("categoria")}>
              Gastos
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("presupuesto")} onClick={() => alClickEncabezado("presupuesto")}>
              Presupuesto
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("ejecutado")} onClick={() => alClickEncabezado("ejecutado")}>
              Ejecutado
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("diferencia")} onClick={() => alClickEncabezado("diferencia")}>
              Diferencia Q.
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("diferencia_pct")} onClick={() => alClickEncabezado("diferencia_pct")}>
              Diferencia %
            </EncabezadoOrdenable>
          </tr>
        </thead>
        <tbody>
          {filasOrdenadas.map((f) => (
            <FilaTablaPresupuesto key={f.categoria} fila={f} coloreVerdeNegativo={coloreVerdeNegativo} />
          ))}
          <FilaTablaPresupuesto fila={filaTotal} coloreVerdeNegativo={coloreVerdeNegativo} />
        </tbody>
      </table>
    </div>
  );
}

// Gráfica Presupuesto vs Ejecutado (1 categoría, 2 series juntas y
// centradas) -- a propósito NO reusa GraficoColumnasGrupoEjecucion
// (DashboardOtrosInformesPage.tsx, usada por las 3 mini-gráficas de
// Ejecución de Gastos): esa es una pantalla ya aprobada con su propio
// tamaño de fuente/ancho de barra calibrado, y esta pantalla necesita
// valores DISTINTOS (fuente de etiqueta 14px aquí vs 11px en Acumulado,
// barras ~12% del ancho en vez de barSize fijo) -- tocar el componente
// compartido arriesgaba romper Ejecución de Gastos, ya aprobada.
//
// Ancho de barra: SIN barSize fijo (no escala con el contenedor) --
// en cambio barCategoryGap (calibrado empíricamente, midiendo con
// getBoundingClientRect en el navegador real) deja el resto del ancho
// del área de la gráfica para las 2 barras + el gap entre ellas,
// resultando en ~12% de ancho por barra (calcado del "size":125 en un
// visual Deneb de 1062px ≈ 12% del spec real de "Comparativo
// ejecutado", mismo criterio aplicado acá), con un espacio mínimo
// (barGap) entre ambas.
function GraficoPresupuestoEjecutado({
  titulo,
  presupuesto,
  ejecutado,
  escalaMax,
  escalaTicks,
  fontSizeEtiqueta,
  fontSizeEje,
}: {
  titulo: string;
  presupuesto: number;
  ejecutado: number;
  escalaMax: number;
  escalaTicks: number[];
  fontSizeEtiqueta: number;
  fontSizeEje: number;
}) {
  const fila = [{ presupuesto, ejecutado }];
  const estiloEtiquetaEje = { fontSize: fontSizeEje, fontWeight: 700, fill: "rgb(var(--color-ink))" };
  const [refTarjeta, anchoTarjeta] = useAnchoElemento<HTMLDivElement>();
  const barSize = anchoTarjeta ? Math.round(anchoTarjeta * 0.12) : undefined;
  const aspecto = calcularAspectoSvg(anchoTarjeta);
  // Gutters reales del BarChart (margin + ancho del eje Y, que solo
  // ocupa espacio a la izquierda) -- usados para centrar la leyenda
  // propia sobre el par de barras (ver LeyendaCentrada arriba).
  const anchoEjeY = Math.max(60, 12 + Math.max(...escalaTicks.map((v) => formatQ(v).length)) * (fontSizeEje / 1.6));
  const gutterIzquierdo = 16 + anchoEjeY;
  const gutterDerecho = 16;
  return (
    <div
      ref={refTarjeta}
      className="overflow-hidden rounded-tremor-default pt-2 ring-1 ring-line"
      style={{ backgroundColor: FINANCIERO_SURFACE }}
    >
      {/* Título DENTRO del recuadro de la gráfica (parte superior,
          centrado, negrita, 16px) -- calcado del .pbix real, donde el
          título es parte del propio visual, no un elemento aparte
          arriba de la tarjeta. El padding-top va en la TARJETA (no en
          el <p>): el padding de un elemento no mueve su propio borde
          superior, así que ponerlo en el <p> no separaba visualmente su
          borde del borde de la tarjeta (medían el mismo `top` en
          getBoundingClientRect, aunque el texto en sí sí se viera
          separado por el padding). */}
      <p className="text-center text-base font-bold text-ink">{titulo}</p>
      <ResponsiveContainer width="100%" aspect={aspecto}>
        <BarChart data={fila} margin={{ top: 24, right: gutterDerecho, bottom: 4, left: 16 }} barGap={4}>
          <XAxis dataKey={() => ""} tick={false} axisLine={false} tickLine={false} />
          <YAxis
            type="number"
            domain={[0, escalaMax]}
            ticks={escalaTicks}
            tickFormatter={(v: number) => formatQ(v)}
            tick={estiloEtiquetaEje}
            axisLine={false}
            tickLine={false}
            width={anchoEjeY}
          />
          <Tooltip
            cursor={{ fill: "rgb(var(--color-ink-faint) / 0.08)" }}
            formatter={(v: number) => formatQ(v)}
            contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
            labelStyle={{ color: "rgb(var(--color-ink))" }}
            itemStyle={{ color: "rgb(var(--color-ink))" }}
          />
          <Bar dataKey="presupuesto" fill={COLOR_PRESUPUESTO} radius={[4, 4, 0, 0]} isAnimationActive={false} barSize={barSize}>
            <LabelList
              dataKey="presupuesto"
              position="top"
              formatter={(v: number) => formatQ(v)}
              fontSize={fontSizeEtiqueta}
              fontWeight={700}
              fill="rgb(var(--color-ink))"
              fillOpacity={1}
            />
          </Bar>
          <Bar dataKey="ejecutado" fill={COLOR_EJECUTADO} radius={[4, 4, 0, 0]} isAnimationActive={false} barSize={barSize}>
            <LabelList
              dataKey="ejecutado"
              position="top"
              formatter={(v: number) => formatQ(v)}
              fontSize={fontSizeEtiqueta}
              fontWeight={700}
              fill="rgb(var(--color-ink))"
              fillOpacity={1}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {/* Leyenda propia centrada sobre el par de barras (position
          BottomCenter real del .pbix, negrita, 16px, círculos) -- ver
          LeyendaCentrada arriba. */}
      <LeyendaCentrada
        anchoTarjeta={anchoTarjeta}
        gutterIzquierdo={gutterIzquierdo}
        gutterDerecho={gutterDerecho}
        items={[
          { etiqueta: "Presupuesto", color: COLOR_PRESUPUESTO },
          { etiqueta: "Ejecutado", color: COLOR_EJECUTADO },
        ]}
      />
    </div>
  );
}

function PaginaEjecucionVsPresupuesto({ acumulado }: { acumulado: boolean }) {
  const [data, setData] = useState<EjecucionVsPresupuestoResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Año+Mes sincronizado con el resto del Grupo 1 (Estados financieros,
  // Otros informes financieros) -- ver FinancieroFilterContext.
  const { anio, mes, cambiarAnio, cambiarMes, setAnioMes } = useFinancieroFilterGrupo1(data?.periodos_disponibles ?? []);

  const obtener = acumulado ? obtenerEjecucionVsPresupuestoAcumulado : obtenerEjecucionVsPresupuesto;

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtener(anio ? Number(anio) : undefined, mes ? Number(mes) : undefined)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        if (!anio || !mes) setAnioMes(String(res.anio), String(res.mes));
      })
      .catch((err) => {
        if (!cancelado) setError(mensajeError(err));
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anio, mes, acumulado]);

  if (error) {
    return <p className="rounded-tremor-small bg-danger-surface px-4 py-3 text-sm text-danger">{error}</p>;
  }

  const periodos = data?.periodos_disponibles ?? [];
  const aniosDisponibles = Array.from(new Set(periodos.map((p) => p.anio))).sort((a, b) => a - b);
  const mesesDelAnio = periodos
    .filter((p) => String(p.anio) === anio)
    .map((p) => p.mes)
    .sort((a, b) => a - b);

  // Títulos reales confirmados con pbixray: "Ejecución Consolidados vs.
  // Presupuesto {Mes} {Año}" (medida `Texto comp_presupuesto`) y
  // "Detalle de Ejecución Gastos vs. Presupuesto al {día} de {Mes} de
  // {Año}" (medida `Texto ctros_costoAcumulado` -- el .pbix real reusa
  // la MISMA medida de título que ya usa "Ejecución Gastos Acumulado").
  const tituloPagina = data
    ? acumulado
      ? `Detalle de Ejecución Gastos vs. Presupuesto al ${ultimoDiaDelMes(data.anio, data.mes)} de ${MESES_LARGOS[data.mes - 1]} de ${data.anio}`
      : `Ejecución Consolidados vs. Presupuesto ${MESES_LARGOS[data.mes - 1]} ${data.anio}`
    : `Ejecución vs Presupuesto${acumulado ? " Acumulado" : ""}`;

  const escala = acumulado ? ESCALA_EJE_Y_PRESUPUESTO_ACUMULADO : ESCALA_EJE_Y_PRESUPUESTO_MENSUAL;
  const anchoTabla = acumulado ? ANCHO_TABLA_ACUMULADO : ANCHO_MENSUAL;
  const anchoGrafica = acumulado ? ANCHO_GRAFICA_ACUMULADO : ANCHO_MENSUAL;
  const margenTablaGrafica = acumulado ? MARGEN_TABLA_GRAFICA_ACUMULADO : MARGEN_TABLA_GRAFICA_MENSUAL;
  // Labels: 14px en mensual, 11px en acumulado (fontSize real de
  // `labels.properties` en el Layout.json de cada página). Eje Y: 14px
  // en las 2 (mismo valor real en ambos Layout.json).
  const fontSizeEtiqueta = acumulado ? 11 : 14;

  return (
    <div className="space-y-3">
      <div className="relative flex min-h-[40px] items-center justify-center">
        <Title className="px-4 text-center text-2xl font-bold text-ink">{tituloPagina}</Title>
        <div className="absolute right-0 top-0">
          <FilterYearMonth
            label="Año y Mes"
            anio={anio}
            mes={mes}
            onChangeAnio={cambiarAnio}
            onChangeMes={cambiarMes}
            aniosOpciones={aniosDisponibles.map(String)}
            mesesOpciones={mesesDelAnio.map((m) => ({ value: String(m), label: MESES_LARGOS[m - 1] }))}
            theme="gris"
          />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          <div className="mx-auto" style={{ width: anchoTabla }}>
            <TablaPresupuesto filas={data.filas} filaTotal={data.fila_total} coloreVerdeNegativo={!acumulado} />
          </div>

          <div className="mx-auto" style={{ width: anchoGrafica, marginTop: margenTablaGrafica }}>
            <GraficoPresupuestoEjecutado
              titulo={tituloPagina}
              presupuesto={data.fila_total.presupuesto}
              ejecutado={data.fila_total.ejecutado}
              escalaMax={escala.max}
              escalaTicks={escala.ticks}
              fontSizeEtiqueta={fontSizeEtiqueta}
              fontSizeEje={14}
            />
          </div>
        </>
      )}
    </div>
  );
}

// --- Comparativo ejecutado (año-1 vs año, acumulado) ----------------------

const ANCHO_TABLA_COMPARATIVO = "70.2%"; // 1164/1658
const ANCHO_GRAFICA_COMPARATIVO = "64.1%"; // 1062/1658 -- NO el mismo ancho que la tabla, así es en el .pbix real
const ESCALA_EJE_Y_COMPARATIVO = { max: 8_000_000, ticks: [0, 2_000_000, 4_000_000, 6_000_000, 8_000_000] };

// Colores exactos del spec Deneb real ("Comparativo ejecutado" en el
// .pbix): scale.range=["#5B7FAE","#43B0A6"] con TipoDinamicoEjecutado
// ordenado ascendente -- el año MENOR (2025) cae en el primer color
// (azul), el año MAYOR (2026) en el segundo (teal).
const COLOR_ANIO_ANTERIOR = "#5B7FAE";
const COLOR_ANIO_ACTUAL = "#43B0A6";

const ANCHOS_COLUMNA_COMPARATIVO = ["52%", "13.5%", "12.5%", "13%", "9%"];

function ColgroupComparativo() {
  return (
    <colgroup>
      {ANCHOS_COLUMNA_COMPARATIVO.map((ancho, i) => (
        <col key={i} style={{ width: ancho }} />
      ))}
    </colgroup>
  );
}

function FilaTablaComparativo({ fila }: { fila: FilaComparativoEjecutado }) {
  const claseCelda = `px-2 py-1.5 text-sm text-ink ${fila.negrita ? "font-bold" : ""}`;
  return (
    <tr style={{ backgroundColor: FINANCIERO_SURFACE }} className={fila.negrita ? "border-t border-line" : undefined}>
      <td className={claseCelda}>{fila.categoria}</td>
      <td className={`${claseCelda} text-right`}>{formatQ(fila.anio_anterior)}</td>
      <td className={`${claseCelda} text-right`}>{formatQ(fila.anio_actual)}</td>
      <td className={`${claseCelda} text-right`}>{formatQ(fila.variacion)}</td>
      <td className={`${claseCelda} text-right`}>{formatPercent2(fila.variacion_pct)}</td>
    </tr>
  );
}

const COLUMNAS_ORDENABLES_COMPARATIVO: ColumnaOrdenable<FilaComparativoEjecutado>[] = [
  { clave: "categoria", tipo: "texto", valor: (f) => f.categoria },
  { clave: "anio_anterior", tipo: "numero", valor: (f) => f.anio_anterior },
  { clave: "anio_actual", tipo: "numero", valor: (f) => f.anio_actual },
  { clave: "variacion", tipo: "numero", valor: (f) => f.variacion },
  { clave: "variacion_pct", tipo: "numero", valor: (f) => f.variacion_pct },
];

function TablaComparativo({ data }: { data: ComparativoEjecutadoResponse }) {
  const { filas, alClickEncabezado, flechaColumna } = useTablaOrdenable(data.filas, COLUMNAS_ORDENABLES_COMPARATIVO);
  const claseHeaderTexto = "px-2 py-1.5 text-left text-white font-normal";
  const claseHeaderNumero = "px-2 py-1.5 text-right text-white font-normal";
  return (
    <div className="overflow-hidden rounded-tremor-default ring-1 ring-line">
      <table className="w-full text-sm">
        <ColgroupComparativo />
        <thead>
          <tr style={{ backgroundColor: VERDE_ENCABEZADO }}>
            <EncabezadoOrdenable className={claseHeaderTexto} flecha={flechaColumna("categoria")} onClick={() => alClickEncabezado("categoria")}>
              Gastos
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("anio_anterior")} onClick={() => alClickEncabezado("anio_anterior")}>
              {data.anio_anterior}
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("anio_actual")} onClick={() => alClickEncabezado("anio_actual")}>
              {data.anio}
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("variacion")} onClick={() => alClickEncabezado("variacion")}>
              Variación Q.
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("variacion_pct")} onClick={() => alClickEncabezado("variacion_pct")}>
              Variación %
            </EncabezadoOrdenable>
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => (
            <FilaTablaComparativo key={f.categoria} fila={f} />
          ))}
          <FilaTablaComparativo fila={data.fila_total} />
        </tbody>
      </table>
    </div>
  );
}

// Gráfica de columnas 2025 vs 2026 -- misma estructura que
// GraficoPresupuestoEjecutado (1 categoría, 2 series juntas y
// centradas, barras ~12% vía barCategoryGap, sin barSize fijo), pero con
// los colores/tamaños de fuente del spec Deneb real (16px en vez de
// 14px/11px, exclusivo de esta pantalla).
function GraficoComparativoEjecutado({
  titulo,
  anioAnterior,
  anioActual,
  valorAnterior,
  valorActual,
  escalaMax,
  escalaTicks,
}: {
  titulo: string;
  anioAnterior: number;
  anioActual: number;
  valorAnterior: number;
  valorActual: number;
  escalaMax: number;
  escalaTicks: number[];
}) {
  const fila = [{ anterior: valorAnterior, actual: valorActual }];
  // 16px en negrita -- labelFontSize:16/labelFontWeight:"bold" del spec
  // Deneb real, tanto en el eje Y como en la leyenda y las etiquetas de
  // valor (fontSize del mark "text" también 16 bold).
  const estiloEtiquetaEje = { fontSize: 16, fontWeight: 700, fill: "rgb(var(--color-ink))" };
  const [refTarjeta, anchoTarjeta] = useAnchoElemento<HTMLDivElement>();
  const barSize = anchoTarjeta ? Math.round(anchoTarjeta * 0.12) : undefined;
  // Gutters reales del BarChart -- ver comentario igual en
  // GraficoPresupuestoEjecutado (leyenda propia centrada sobre el par
  // de barras, no el <Legend> de Recharts).
  const anchoEjeY = Math.max(60, 12 + Math.max(...escalaTicks.map((v) => formatQ(v).length)) * 10);
  const gutterIzquierdo = 16 + anchoEjeY;
  const gutterDerecho = 16;
  const aspecto = calcularAspectoSvg(anchoTarjeta);
  return (
    <div
      ref={refTarjeta}
      className="overflow-hidden rounded-tremor-default pt-2 ring-1 ring-line"
      style={{ backgroundColor: FINANCIERO_SURFACE }}
    >
      {/* Título DENTRO del recuadro de la gráfica, igual que
          GraficoPresupuestoEjecutado (padding-top en la tarjeta, no en
          el <p>). */}
      <p className="text-center text-base font-bold text-ink">{titulo}</p>
      <ResponsiveContainer width="100%" aspect={aspecto}>
        <BarChart data={fila} margin={{ top: 24, right: gutterDerecho, bottom: 4, left: 16 }} barGap={4}>
          <XAxis dataKey={() => ""} tick={false} axisLine={false} tickLine={false} />
          <YAxis
            type="number"
            domain={[0, escalaMax]}
            ticks={escalaTicks}
            tickFormatter={(v: number) => formatQ(v)}
            tick={estiloEtiquetaEje}
            axisLine={false}
            tickLine={false}
            width={anchoEjeY}
          />
          <Tooltip
            cursor={{ fill: "rgb(var(--color-ink-faint) / 0.08)" }}
            formatter={(v: number) => formatQ(v)}
            contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
            labelStyle={{ color: "rgb(var(--color-ink))" }}
            itemStyle={{ color: "rgb(var(--color-ink))" }}
          />
          <Bar dataKey="anterior" fill={COLOR_ANIO_ANTERIOR} radius={[4, 4, 0, 0]} isAnimationActive={false} barSize={barSize}>
            <LabelList
              dataKey="anterior"
              position="top"
              formatter={(v: number) => formatQ(v)}
              fontSize={16}
              fontWeight={700}
              fill="rgb(var(--color-ink))"
              fillOpacity={1}
            />
          </Bar>
          <Bar dataKey="actual" fill={COLOR_ANIO_ACTUAL} radius={[4, 4, 0, 0]} isAnimationActive={false} barSize={barSize}>
            <LabelList
              dataKey="actual"
              position="top"
              formatter={(v: number) => formatQ(v)}
              fontSize={16}
              fontWeight={700}
              fill="rgb(var(--color-ink))"
              fillOpacity={1}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <LeyendaCentrada
        anchoTarjeta={anchoTarjeta}
        gutterIzquierdo={gutterIzquierdo}
        gutterDerecho={gutterDerecho}
        items={[
          { etiqueta: String(anioAnterior), color: COLOR_ANIO_ANTERIOR },
          { etiqueta: String(anioActual), color: COLOR_ANIO_ACTUAL },
        ]}
      />
    </div>
  );
}

function PaginaComparativoEjecutado() {
  const [data, setData] = useState<ComparativoEjecutadoResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { anio, mes, cambiarAnio, cambiarMes, setAnioMes } = useFinancieroFilterGrupo1(data?.periodos_disponibles ?? []);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerComparativoEjecutado(anio ? Number(anio) : undefined, mes ? Number(mes) : undefined)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        if (!anio || !mes) setAnioMes(String(res.anio), String(res.mes));
      })
      .catch((err) => {
        if (!cancelado) setError(mensajeError(err));
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anio, mes]);

  if (error) {
    return <p className="rounded-tremor-small bg-danger-surface px-4 py-3 text-sm text-danger">{error}</p>;
  }

  const periodos = data?.periodos_disponibles ?? [];
  const aniosDisponibles = Array.from(new Set(periodos.map((p) => p.anio))).sort((a, b) => a - b);
  const mesesDelAnio = periodos
    .filter((p) => String(p.anio) === anio)
    .map((p) => p.mes)
    .sort((a, b) => a - b);

  // Título real (medida DAX TituloEjecutadoComparativo): "Comparativo
  // Ejecutado {Año-1} vs {Año} Acumulado al {día} de {Mes}" -- SIN el
  // año repetido al final (confirmado con pbixray, la medida real no lo
  // repite ahí).
  const tituloPagina = data
    ? `Comparativo Ejecutado ${data.anio_anterior} vs ${data.anio} Acumulado al ${ultimoDiaDelMes(data.anio, data.mes)} de ${MESES_LARGOS[data.mes - 1]}`
    : "Comparativo Ejecutado";

  return (
    <div className="space-y-3">
      <div className="relative flex min-h-[40px] items-center justify-center">
        <Title className="px-4 text-center text-2xl font-bold text-ink">{tituloPagina}</Title>
        <div className="absolute right-0 top-0">
          <FilterYearMonth
            label="Año y Mes"
            anio={anio}
            mes={mes}
            onChangeAnio={cambiarAnio}
            onChangeMes={cambiarMes}
            aniosOpciones={aniosDisponibles.map(String)}
            mesesOpciones={mesesDelAnio.map((m) => ({ value: String(m), label: MESES_LARGOS[m - 1] }))}
            theme="gris"
          />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          <div className="mx-auto" style={{ width: ANCHO_TABLA_COMPARATIVO }}>
            <TablaComparativo data={data} />
          </div>

          <div className="mx-auto" style={{ width: ANCHO_GRAFICA_COMPARATIVO, marginTop: MARGEN_TABLA_GRAFICA_COMPARATIVO }}>
            <GraficoComparativoEjecutado
              titulo={tituloPagina}
              anioAnterior={data.anio_anterior}
              anioActual={data.anio}
              valorAnterior={data.fila_total.anio_anterior}
              valorActual={data.fila_total.anio_actual}
              escalaMax={ESCALA_EJE_Y_COMPARATIVO.max}
              escalaTicks={ESCALA_EJE_Y_COMPARATIVO.ticks}
            />
          </div>
        </>
      )}
    </div>
  );
}

// --- Router de la sección "Presupuestos" ----------------------------------

const VISTAS = ["ejecucion-vs-presupuesto", "ejecucion-vs-presupuesto-acumulado", "comparativo-ejecutado"] as const;

export function DashboardPresupuestosPage() {
  const [searchParams] = useSearchParams();
  const vistaParam = searchParams.get("vista") ?? "ejecucion-vs-presupuesto";
  const vista = VISTAS.includes(vistaParam as (typeof VISTAS)[number])
    ? (vistaParam as (typeof VISTAS)[number])
    : "ejecucion-vs-presupuesto";

  if (vista === "ejecucion-vs-presupuesto-acumulado") {
    return <PaginaEjecucionVsPresupuesto acumulado={true} />;
  }
  if (vista === "comparativo-ejecutado") {
    return <PaginaComparativoEjecutado />;
  }
  return <PaginaEjecucionVsPresupuesto acumulado={false} />;
}

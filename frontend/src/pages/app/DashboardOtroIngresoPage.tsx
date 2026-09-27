import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Title } from "@tremor/react";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { obtenerOtroIngreso } from "../../api/dashboardOtroIngreso";
import { mensajeError } from "../../api/client";
import { FilterYear } from "../../components/filters/PowerBiFilter";
import { FINANCIERO_SURFACE } from "../../components/TablaGrupoExpandible";
import { formatPercentEntero, formatQ } from "../../utils/format";
import type { FilaOtroIngreso, OtroIngresoResponse } from "../../types/dashboardOtroIngreso";

// Ancho real medido del ancho de la tarjeta -- mismo patrón ya usado en
// Importaciones/Presupuestos.
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

// El `aspect` de ResponsiveContainer solo controla el <svg>, no la
// tarjeta completa (que además tiene título+leyenda arriba/abajo) --
// mismo mecanismo que Importaciones/Presupuestos: se despeja el alto del
// <svg> para que la TARJETA COMPLETA dé la proporción pedida.
function calcularAspectoSvg(anchoTarjeta: number, proporcion: number, altoExtra: number): number {
  if (!anchoTarjeta) return 1 / proporcion;
  const altoSvgDeseado = proporcion * anchoTarjeta - altoExtra;
  return anchoTarjeta / Math.max(altoSvgDeseado, 1);
}

// Ancho del eje Y en px, a partir del texto MÁS LARGO (los nombres de
// concepto van completos, sin cortar -- ver GraficoBarrasOtrosIngresos).
function calcularAnchoEjeYTexto(textos: string[], fontSize = 12): number {
  const masLargo = Math.max(0, ...textos.map((t) => t.length));
  return Math.max(80, masLargo * (fontSize * 0.62) + 16);
}

const ANCHO_GRAFICA = "93.4%"; // 1904/2038 (canvas 2300px, menú 262px, contenido 2038px)
const ANCHO_TABLA = "93.4%";
const PROPORCION_BARRAS = 0.4;
const PROPORCION_TOTALES = 0.13;
const ALTO_EXTRA_TITULO_LEYENDA = 60; // ~32 (título) + 28 (leyenda)
const GAP_TITULO_CONTENIDO = "4.6%"; // 76px/1658 -- misma regla general que las demás pantallas
// Separación entre la gráfica de barras y la de totales: el Layout real
// de esta página trae 2 visuales superpuestos entre sí en esa zona (la
// versión "Nueva" del .pbix parece tener un resabio de una edición
// anterior, sin limpiar) -- no hay un valor limpio que copiar ahí, así
// que se usa una separación chica razonable, decisión propia.
const GAP_ENTRE_GRAFICAS = "1.2%";

const COLOR_EJECUTADO_ANTERIOR = "#9FB6C3";
const COLOR_PRESUPUESTO_ANIO = "#2F8C83";
const COLOR_EJECUTADO_ANIO = "#00A6B8";
const COLOR_CHIP_PORCENTAJE = "#147CC1";

// --- 1. Gráfica de barras horizontales agrupadas ---------------------

function GraficoBarrasOtrosIngresos({
  titulo,
  filas,
  anioAnterior,
  anio,
}: {
  titulo: string;
  filas: FilaOtroIngreso[];
  anioAnterior: number;
  anio: number;
}) {
  // Conceptos ordenados por su valor MÁXIMO entre las 3 series, descendente.
  const ordenadas = [...filas].sort(
    (a, b) =>
      Math.max(b.ejecutado_anio_anterior, b.presupuesto_anio, b.ejecutado_anio) -
      Math.max(a.ejecutado_anio_anterior, a.presupuesto_anio, a.ejecutado_anio)
  );
  const [refTarjeta, anchoTarjeta] = useAnchoElemento<HTMLDivElement>();
  const aspecto = calcularAspectoSvg(anchoTarjeta, PROPORCION_BARRAS, ALTO_EXTRA_TITULO_LEYENDA);
  const anchoEjeY = calcularAnchoEjeYTexto(ordenadas.map((f) => f.concepto));
  return (
    <div
      ref={refTarjeta}
      className="overflow-hidden rounded-tremor-default pt-2 ring-1 ring-line"
      style={{ backgroundColor: FINANCIERO_SURFACE }}
    >
      <p className="text-center text-base font-bold text-ink">{titulo}</p>
      <ResponsiveContainer width="100%" aspect={aspecto}>
        <BarChart data={ordenadas} layout="vertical" margin={{ top: 8, right: 24, bottom: 4, left: 8 }} barGap={0}>
          <CartesianGrid horizontal={false} vertical stroke="#666666" strokeOpacity={0.3} />
          <XAxis
            type="number"
            tickFormatter={(v: number) => formatQ(v)}
            tick={{ fontSize: 12, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="concepto"
            width={anchoEjeY}
            tick={{ fontSize: 12, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(v: number) => formatQ(v)}
            contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
            labelStyle={{ color: "rgb(var(--color-ink))" }}
          />
          {/* Sin etiquetas de valor (como en Power BI). */}
          <Bar dataKey="ejecutado_anio_anterior" fill={COLOR_EJECUTADO_ANTERIOR} barSize={13} isAnimationActive={false} />
          <Bar dataKey="presupuesto_anio" fill={COLOR_PRESUPUESTO_ANIO} barSize={13} isAnimationActive={false} />
          <Bar dataKey="ejecutado_anio" fill={COLOR_EJECUTADO_ANIO} barSize={13} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
      {/* Leyenda con las etiquetas CORRECTAS (en Power BI está mal
          etiquetada: dice "Ejecutado 2026 / Ejecutado 2025 / Presupuesto
          2026" para estos mismos 3 colores en ese orden -- acá dice lo
          correcto según el color). */}
      <div className="flex items-center justify-center gap-6 pb-2 pt-1 text-sm font-bold text-ink">
        {[
          { color: COLOR_EJECUTADO_ANTERIOR, etiqueta: `Ejecutado ${anioAnterior}` },
          { color: COLOR_PRESUPUESTO_ANIO, etiqueta: `Presupuesto ${anio}` },
          { color: COLOR_EJECUTADO_ANIO, etiqueta: `Ejecutado ${anio}` },
        ].map((it) => (
          <span key={it.etiqueta} className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: it.color }} />
            {it.etiqueta}
          </span>
        ))}
      </div>
    </div>
  );
}

// --- 2. Gráfica de totales (3 barras horizontales, valor dentro) -----

function GraficoTotalesOtrosIngresos({ total }: { total: FilaOtroIngreso }) {
  const [refTarjeta, anchoTarjeta] = useAnchoElemento<HTMLDivElement>();
  // Sin título ni leyenda (como en Power BI) -- nada de alto extra que
  // despejar, el <svg> ocupa toda la tarjeta.
  const aspecto = calcularAspectoSvg(anchoTarjeta, PROPORCION_TOTALES, 0);
  const datos = [
    { serie: "ejecutado_anterior", valor: total.ejecutado_anio_anterior, color: COLOR_EJECUTADO_ANTERIOR },
    { serie: "presupuesto", valor: total.presupuesto_anio, color: COLOR_PRESUPUESTO_ANIO },
    { serie: "ejecutado_actual", valor: total.ejecutado_anio, color: COLOR_EJECUTADO_ANIO },
  ];
  // Dominio/ticks "nice" en vez de domain={[0,"dataMax"]} -- eso daba un
  // último tick pegado al valor exacto ("Q2,048,918" en vez de un número
  // redondo), Recharts no lo redondea solo cuando el máximo del dominio
  // coincide con el dato. Paso fijo de Q500,000 (calcado del ejemplo
  // dado, "Q0, Q500,000, Q1,000,000…").
  const maxValor = Math.max(total.ejecutado_anio_anterior, total.presupuesto_anio, total.ejecutado_anio, 1);
  const pasoTotales = 500_000;
  const dominioMax = Math.ceil(maxValor / pasoTotales) * pasoTotales;
  const ticksTotales: number[] = [];
  for (let v = 0; v <= dominioMax; v += pasoTotales) ticksTotales.push(v);
  return (
    <div ref={refTarjeta} className="overflow-hidden rounded-tremor-default ring-1 ring-line" style={{ backgroundColor: FINANCIERO_SURFACE }}>
      <ResponsiveContainer width="100%" aspect={aspecto}>
        <BarChart data={datos} layout="vertical" margin={{ top: 8, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} vertical stroke="#666666" strokeOpacity={0.3} />
          <XAxis
            type="number"
            domain={[0, dominioMax]}
            ticks={ticksTotales}
            tickFormatter={(v: number) => formatQ(v)}
            tick={{ fontSize: 12, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis type="category" dataKey="serie" hide />
          <Tooltip
            formatter={(v: number) => formatQ(v)}
            contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
          />
          <Bar dataKey="valor" isAnimationActive={false} barSize={28}>
            {datos.map((d) => (
              <Cell key={d.serie} fill={d.color} />
            ))}
            <LabelList dataKey="valor" position="center" formatter={(v: number) => formatQ(v)} fill="#FFFFFF" fontSize={13} fontWeight={700} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// --- 3. Tabla de detalle ---------------------------------------------

// Encabezados partidos en 2-3 renglones (mejor esfuerzo propio: el
// visual real del .pbix arma esta tabla con decenas de tarjetas
// individuales en vez de una tabla/Deneb con un spec de texto limpio
// para extraer -- se preserva el texto COMPLETO de cada concepto, solo
// partido en líneas más cortas para que la columna no se ensanche).
const ENCABEZADOS_TABLA: Record<string, string[]> = {
  "CropLife - Proyecto SPMF": ["CropLife -", "Proyecto SPMF"],
  Gremiagro: ["Gremiagro"],
  "Venta de Material Reciclable(Chatarra, cartón, metal, plástico)": [
    "Venta de Material",
    "Reciclable",
    "(Chatarra, cartón, metal, plástico)",
  ],
  "Aporte Industria Fertilizantes": ["Aporte Industria", "Fertilizantes"],
  "Aporte Fundación Hanns R. Neumann Stiftung": ["Aporte Fundación", "Hanns R. Neumann", "Stiftung"],
  "Intereses Bancarios e Inversión": ["Intereses Bancarios", "e Inversión"],
  "Carnet Aplicadores y Certificados, Cursos, Capacitaciones y Talleres y otras donaciones": [
    "Carnet Aplicadores y",
    "Certificados, Cursos,",
    "Capacitaciones y Talleres y otras donaciones",
  ],
  "Venta de Sellos": ["Venta de", "Sellos"],
  "Venta Minicentros de Plástico Reciclado": ["Venta Minicentros", "de Plástico", "Reciclado"],
  "Proyecto ATRACSI": ["Proyecto", "ATRACSI"],
  "Localg.a.p. Guatemala": ["Localg.a.p.", "Guatemala"],
  "Venta de Vehículos": ["Venta de", "Vehículos"],
};

function encabezadoConcepto(concepto: string): string[] {
  return ENCABEZADOS_TABLA[concepto] ?? concepto.split(" ").reduce<string[]>((lineas, palabra) => {
    const ultima = lineas[lineas.length - 1];
    if (ultima && (ultima + " " + palabra).length <= 18) {
      lineas[lineas.length - 1] = ultima + " " + palabra;
    } else {
      lineas.push(palabra);
    }
    return lineas;
  }, []);
}

const BORDE_CELDA = "#7E7E7E";

function ChipFila({ color, etiqueta }: { color: string; etiqueta: string }) {
  return (
    <span className="flex items-center justify-center gap-1.5 whitespace-nowrap px-2 py-1 text-xs font-bold text-ink">
      <span aria-hidden="true" className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: color }} />
      {etiqueta}
    </span>
  );
}

function TablaOtrosIngresos({ filas, total, anioAnterior, anio }: { filas: FilaOtroIngreso[]; total: FilaOtroIngreso; anioAnterior: number; anio: number }) {
  const claseCelda = "px-2 py-2 text-center text-sm text-ink";
  const claseBorde = { border: `1px solid ${BORDE_CELDA}` };
  return (
    <div className="overflow-x-auto rounded-tremor-default" style={{ backgroundColor: FINANCIERO_SURFACE, border: `1px solid ${BORDE_CELDA}` }}>
      <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th className="px-2 py-2" style={claseBorde} />
            {filas.map((f) => (
              <th key={f.concepto} className="px-1 py-2 text-center text-xs font-bold leading-tight text-ink" style={claseBorde} title={f.concepto}>
                {encabezadoConcepto(f.concepto).map((linea, i) => (
                  <div key={i}>{linea}</div>
                ))}
              </th>
            ))}
            <th className="px-2 py-2 text-center text-xs font-bold text-ink" style={claseBorde}>
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className={claseCelda} style={claseBorde}>
              <ChipFila color={COLOR_EJECUTADO_ANTERIOR} etiqueta={`Ejecutado ${anioAnterior}`} />
            </td>
            {filas.map((f) => (
              <td key={f.concepto} className={claseCelda} style={claseBorde}>
                {formatQ(f.ejecutado_anio_anterior)}
              </td>
            ))}
            <td className={`${claseCelda} font-bold`} style={claseBorde}>
              {formatQ(total.ejecutado_anio_anterior)}
            </td>
          </tr>
          <tr>
            <td className={claseCelda} style={claseBorde}>
              <ChipFila color={COLOR_PRESUPUESTO_ANIO} etiqueta={`Presupuesto ${anio}`} />
            </td>
            {filas.map((f) => (
              <td key={f.concepto} className={claseCelda} style={claseBorde}>
                {formatQ(f.presupuesto_anio)}
              </td>
            ))}
            <td className={`${claseCelda} font-bold`} style={claseBorde}>
              {formatQ(total.presupuesto_anio)}
            </td>
          </tr>
          <tr>
            <td className={claseCelda} style={claseBorde}>
              <ChipFila color={COLOR_EJECUTADO_ANIO} etiqueta={`Ejecutado ${anio}`} />
            </td>
            {filas.map((f) => (
              <td key={f.concepto} className={claseCelda} style={claseBorde}>
                {formatQ(f.ejecutado_anio)}
              </td>
            ))}
            <td className={`${claseCelda} font-bold`} style={claseBorde}>
              {formatQ(total.ejecutado_anio)}
            </td>
          </tr>
          <tr>
            <td className={claseCelda} style={claseBorde}>
              <ChipFila color={COLOR_CHIP_PORCENTAJE} etiqueta="% ejecutado" />
            </td>
            {filas.map((f) => (
              <td key={f.concepto} className={claseCelda} style={claseBorde}>
                {formatPercentEntero(f.porcentaje_ejecucion)}
              </td>
            ))}
            <td className={`${claseCelda} font-bold`} style={claseBorde}>
              {formatPercentEntero(total.porcentaje_ejecucion)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// --- Página -----------------------------------------------------------

export function DashboardOtroIngresoPage() {
  const [anio, setAnio] = useState("");
  const [data, setData] = useState<OtroIngresoResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerOtroIngreso(anio ? Number(anio) : undefined)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        if (!anio) setAnio(String(res.anio));
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
  }, [anio]);

  if (error) {
    return <p className="rounded-tremor-small bg-danger-surface px-4 py-3 text-sm text-danger">{error}</p>;
  }

  const anioOpciones = data?.anios_disponibles ?? [];
  const tituloPagina = data ? `Otros Ingresos Generados por Agrequima año ${data.anio}` : "Otros ingresos generados";

  return (
    <div>
      <div className="relative flex min-h-[40px] items-center justify-center">
        <Title className="px-4 text-center text-2xl font-bold text-ink">{tituloPagina}</Title>
        <div className="absolute right-0 top-0">
          <FilterYear label="Año" anio={anio} onChangeAnio={setAnio} aniosOpciones={anioOpciones.map(String)} theme="gris" anchoFijo />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          <div className="mx-auto" style={{ width: ANCHO_GRAFICA, marginTop: GAP_TITULO_CONTENIDO }}>
            <GraficoBarrasOtrosIngresos
              titulo="Otros ingresos generados por Agrequima"
              filas={data.filas}
              anioAnterior={data.anio_anterior}
              anio={data.anio}
            />
          </div>
          <div className="mx-auto" style={{ width: ANCHO_GRAFICA, marginTop: GAP_ENTRE_GRAFICAS }}>
            <GraficoTotalesOtrosIngresos total={data.total} />
          </div>
          <div className="mx-auto" style={{ width: ANCHO_TABLA, marginTop: GAP_ENTRE_GRAFICAS }}>
            <TablaOtrosIngresos filas={data.filas} total={data.total} anioAnterior={data.anio_anterior} anio={data.anio} />
          </div>
        </>
      )}
    </div>
  );
}

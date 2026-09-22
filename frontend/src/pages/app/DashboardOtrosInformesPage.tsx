import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Title } from "@tremor/react";
import { Bar, BarChart, Cell, Legend, LabelList, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  obtenerCuotasAsociados,
  obtenerEjecucionGastosAcumulado,
  obtenerEjecucionGastosMes,
} from "../../api/dashboardOtrosInformes";
import { mensajeError } from "../../api/client";
import { ChartCard } from "../../components/ChartCard";
import { FilterYearMonth } from "../../components/filters/PowerBiFilter";
import { FINANCIERO_SURFACE, KpiCardIcono, VERDE_ENCABEZADO } from "../../components/TablaGrupoExpandible";
import { formatPercent, formatQ, MESES_LARGOS } from "../../utils/format";
import type {
  CuotasAsociadosResponse,
  EjecucionGastosResponse,
  FilaGastoCategoria,
  TipoCuotaAsociados,
} from "../../types/dashboardOtrosInformes";

// COLOR_TEAL es el color del ícono KPI "T" (Total) Y de la barra
// angosta "Cancelado" (fija, sin variar por tipo) de la gráfica de
// barras -- #2C786C exacto, leído del Layout.json real (reemplaza el
// valor anterior #3f6f6b, que era una aproximación por muestreo de
// pantalla de una ronda previa).
const COLOR_TEAL = "#2C786C";

// Colores REALES por Tipo (A/B/C), leídos directo del archivo fuente
// del reporte (Layout.json del .pbix, no una muestra de pantalla) --
// usados en la dona "Cuotas por Tipo" y en la barra ANCHA ("base") de
// la gráfica "Cuota del año vs Cancelado" (con 60% de transparencia,
// ver FILL_OPACITY_BARRA_BASE más abajo).
const COLOR_TIPO_A = "#0C5A4A";
const COLOR_TIPO_B = "#3182BD";
const COLOR_TIPO_C = "#B7B7B7";

const COLOR_POR_TIPO: Record<string, string> = { A: COLOR_TIPO_A, B: COLOR_TIPO_B, C: COLOR_TIPO_C };

// fillTransparency=60 en el Layout.json real de la barra ancha
// ("Cuota del año", la de atrás) -- en Power BI "transparencia" se mide
// al revés de opacidad (0% transparencia = opaco, 100% = invisible),
// así que 60% de transparencia = 40% de opacidad. Sin este valor la
// barra ancha se ve más oscura/opaca de lo que corresponde, aunque el
// hex de base (COLOR_POR_TIPO) ya sea el correcto.
const FILL_OPACITY_BARRA_BASE = 0.4;

// Colores REALES de "Cancelado" y "Por cobrar" en la dona "Recuperación
// Cuota Asociados" y en las tarjetas KPI C/P -- deben ser IDÉNTICOS
// pixel a pixel entre el ícono de la tarjeta y el segmento de la dona
// (antes había una diferencia mínima de tono con el sombreado por
// muestreo de pantalla).
const COLOR_TURQUESA = "#4DB6AC";
const COLOR_GRIS_AZULADO = "#90A4AE";

// Colores REALES de OBJETO del visual (Layout.json a nivel de visual, no
// del tema general del reporte) para las gráficas de Presupuesto vs
// Ejecutado en Centro de Costo -- las 3 gráficas (Administración/
// Operación/Consolidado) usan un color por MÉTRICA (no por grupo),
// idéntico en las 3. El primer color pasado (#118DFF/#12239E) resultó
// ser el color del TEMA general del reporte, no el del visual -- se
// reemplaza por el valor correcto leído a nivel de objeto.
const COLOR_PRESUPUESTO = "#5C7285";
const COLOR_EJECUTADO = "#A7B49E";

// SIN abreviación K/M en ningún eje/etiqueta/tooltip de Financiero --
// regla PERMANENTE para todo el módulo, confirmada contra el archivo
// fuente real del reporte (Layout.json): la config real del eje tiene
// labelDisplayUnits=None y labelPrecision=0, o sea números COMPLETOS
// con formato de miles y prefijo Q, igual que las tarjetas KPI y las
// tablas -- se usa `formatQ` (utils/format.ts) en todos lados, nunca un
// formateador propio en K/M. Existía un `formatMiles` local (ej.
// "280K") usado en 2 lugares de este archivo (eje Y de esta gráfica y
// las etiquetas de GraficoColumnasGrupo en Centro de Costo, más abajo)
// -- se eliminó por completo y se reemplazaron esos 2 usos por formatQ.

// Layout COMPACTO calcado de las proporciones reales del .pbix (lienzo
// 1920x1500, todo el contenido cabe sin scroll) -- ver instrucción del
// usuario. Tipografía/padding reducidos a propósito (text-[11px], py-0.5)
// para que tablas de hasta ~18 filas quepan en la franja de alto que le
// corresponde sin necesitar scroll interno.

// --- Cuotas Asociados ------------------------------------------------------
//
// Las 3 tarjetas T/C/P reusan KpiCardIcono (TablaGrupoExpandible.tsx),
// el mismo componente ya validado para Estados Financieros -- un alto
// FIJO en px con flex-1 (ancho variable) se desproporciona en pantallas
// anchas (el ancho crece sin límite mientras el alto queda fijo, dejando
// un hueco vacío enorme entre el ícono y el valor); aspect-[4/1] escala
// el alto CON el ancho y mantiene siempre la misma proporción, sin
// importar el viewport.

// Alto FIJO (no derivado del contenido) para que las 3 tablas queden
// EXACTAMENTE parejas entre sí sin importar cuántas filas tenga cada
// Tipo (A=8, B=13, C=18 en 2026) -- calcado de cómo Power BI dibuja un
// visual de tabla: tamaño de lienzo fijo, no "en escalera" según los
// datos. Subido de 478 a 560: al quitar el `truncate` de la columna
// "Nombre" (los nombres largos ahora pasan a una 2da línea en vez de
// cortarse con "…"), varias filas de Tipo C (nombres largos como
// "AGROINDUSTRIAS SUCCESSO," o "CORPOGREEN, SOCIEDAD ANÓN...") ganan una
// línea extra de alto, y el contenido total de Tipo C pasó a medir
// ~519px reales (medido con DevTools) -- 560 le da margen para entrar
// completo sin scroll interno. overflow-y-auto queda como respaldo si
// algún año tuviera todavía más filas o nombres más largos.
const ALTO_TABLA_CUOTAS = 560;
// Alto de la fila de título "Tipo X", FUERA del área con scroll --
// calcado del .pbix real: ahí el título va en una fila propia, sin
// fondo de color, separada del encabezado de columnas (que sí lleva
// fondo verde sólido) -- antes las 2 cosas estaban mezcladas en una
// sola fila de tabla, coloreada por tipo y sin la columna "Nombre".
const ALTO_TITULO_TABLA = 33;

function TablaCuotasTipo({ tipo }: { tipo: TipoCuotaAsociados }) {
  return (
    // backgroundColor en el contenedor EXTERNO -- BUG REAL encontrado
    // midiendo pixel a pixel contra una captura real: getBoundingClientRect
    // ya daba 445px iguales en las 3 cajas (la CAJA CSS sí era igual),
    // pero ni este div ni el de scroll de abajo tenían fondo propio
    // (ambos transparentes) -- así que el tramo vacío debajo de la
    // última fila (445px menos el alto real del contenido: ~210px en
    // Tipo A con 8 filas, ~313px en Tipo B con 13, ~414px en Tipo C con
    // 18) dejaba ver el fondo de la PÁGINA por transparencia en vez del
    // fondo de la tarjeta, y a simple vista -- sobre todo en tema oscuro,
    // donde el fondo de página es bien distinto del gris de tarjeta --
    // las 3 cajas se ven de alto distinto aunque midan lo mismo. Con
    // fondo propio en todo el contenedor de 445px, la tarjeta se ve
    // rellena completa sin importar cuántas filas tenga la tabla.
    <div
      className="flex flex-col overflow-hidden rounded-tremor-default ring-1 ring-line"
      style={{ height: ALTO_TABLA_CUOTAS, backgroundColor: FINANCIERO_SURFACE }}
    >
      {/* Fila de título "Tipo X" SEPARADA del encabezado de columnas,
          sin fondo de color (solo texto blanco en negrita, centrado) --
          calcado del .pbix real: son 2 filas distintas, no una sola
          fila coloreada por tipo. */}
      <div className="flex shrink-0 items-center justify-center text-sm font-bold text-ink" style={{ height: ALTO_TITULO_TABLA }}>
        {`Tipo ${tipo.tipo}`}
      </div>
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        {/* table-fixed + colgroup: sin esto, un <table> en table-layout
            auto (el default) puede crecer MÁS ANCHO que su contenedor si
            el contenido de alguna fila lo exige -- eso generaba un
            scroll horizontal en Tipo C (nombres/montos más largos) que
            no aparecía en A/B, y ese scrollbar horizontal le robaba
            alto utilizable al contenedor, disparando TAMBIÉN un scroll
            vertical aunque las 18 filas ya entraban en los 445px. Con
            columnas de ancho fijo, las 3 tablas quedan con exactamente
            el mismo layout interno y ninguna arrastra un scroll que las
            otras no tengan. */}
        <table className="w-full table-fixed text-[11px]">
          {/* Nombre ensanchada de 30% a 42% -- con el wrap de nombres
              largos (ver `break-words` en el <td>, más abajo) una
              columna angosta hacía que MUCHAS filas de Tipo C
              necesitaran 2 líneas, disparando el alto de contenido muy
              por encima del contenedor. Cuota/Cancelado/Saldo son
              montos cortos ("Q12,000") que no necesitan tanto espacio,
              así que se les resta lo que gana Nombre. */}
          <colgroup>
            <col className="w-[42%]" />
            <col className="w-[19%]" />
            <col className="w-[21%]" />
            <col className="w-[18%]" />
          </colgroup>
          <thead>
            {/* Encabezado de columnas con fondo verde sólido -- calcado
                del .pbix real: es el MISMO verde en las 3 tablas (no un
                color distinto por tipo, medido pixel a pixel), palabras
                completas ("Cancelado", no "Canc."), columna "Nombre"
                explícita -- antes esta fila combinaba "Tipo X" +
                columnas con el color por tipo (COLOR_POR_TIPO), sin
                columna "Nombre". Sin flechita de orden: no hay
                funcionalidad real de ordenar por columna todavía (se
                agregará en otra ronda, para todas las tablas del
                sistema a la vez) -- tenerla ahí sin función era solo un
                ícono sin sentido. */}
            <tr style={{ backgroundColor: VERDE_ENCABEZADO }}>
              <th className="truncate px-2 py-1 text-left font-semibold text-white">Nombre</th>
              <th className="px-2 py-1 text-right font-semibold text-white">Cuota</th>
              <th className="px-2 py-1 text-right font-semibold text-white">Cancelado</th>
              <th className="px-2 py-1 text-right font-semibold text-white">Saldo</th>
            </tr>
          </thead>
          <tbody style={{ backgroundColor: FINANCIERO_SURFACE }}>
            {tipo.filas.map((f) => (
              <tr key={f.nombre} className="border-b border-line/50">
                {/* Sin `truncate`: los nombres largos pasan a una
                    segunda línea (word wrap normal) en vez de cortarse
                    con "…" -- se puede leer el nombre completo. */}
                <td className="break-words px-2 py-0.5 text-ink" title={f.nombre}>
                  {f.nombre}
                </td>
                <td className="whitespace-nowrap px-2 py-0.5 text-right text-ink">{formatQ(f.cuota)}</td>
                <td className="whitespace-nowrap px-2 py-0.5 text-right text-ink">{formatQ(f.cancelado)}</td>
                <td className="whitespace-nowrap px-2 py-0.5 text-right text-ink">{formatQ(f.saldo)}</td>
              </tr>
            ))}
            <tr className="font-semibold text-ink">
              <td className="px-2 py-1">Total {tipo.tipo}</td>
              <td className="whitespace-nowrap px-2 py-1 text-right">{formatQ(tipo.total_cuota)}</td>
              <td className="whitespace-nowrap px-2 py-1 text-right">{formatQ(tipo.total_cancelado)}</td>
              <td className="whitespace-nowrap px-2 py-1 text-right">{formatQ(tipo.total_saldo)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Alto compartido por los 3 visuales de abajo (columnas + 2 donas) --
// mismo valor en los 3 para que queden exactamente del mismo tamaño
// entre sí (ver instrucción del cliente), calcado del .pbix (w≈510
// h≈415 los 3 iguales entre sí). Subido de 190 a 340 -- a 190 los 3 se
// veían chicos y apretados (letra de ejes/leyenda encimada, donas casi
// sin anillo visible); con el ChartCard ya angosto de tituloChico, este
// alto más alto es lo que le da tamaño real al gráfico en sí.
const ALTO_VISUAL_CUOTAS = 340;

// Desglosada por Tipo (A/B/C) -- NO es solo el total del año, son datos
// DISTINTOS. El dato por tipo YA está disponible en data.tipos (mismo
// campo que ya usan las 3 tablas de arriba, total_cuota/total_cancelado)
// -- no hace falta tocar el backend, ya trae el desglose.
//
// TIPO DE VISUAL -- el .pbix real NO es un par de barras lado a lado
// por Tipo: es UNA sola barra ancha BASE (Cuota, coloreada POR TIPO con
// los mismos 3 tonos de la dona "Cuotas por Tipo" + 60% de
// transparencia -- fillTransparency=60 del Layout.json, ver
// FILL_OPACITY_BARRA_BASE) con un marcador angosto (Cancelado)
// SUPERPUESTO encima, de color FIJO (COLOR_TEAL, #2C786C, igual en los
// 3 grupos) -- como un target/reference marker de Power BI, no dos
// series agrupadas. CORRECCIÓN sobre una ronda anterior: se había
// puesto exactamente al revés (base uniforme + overlay por tipo) --
// confirmado contra Layout.json que es la barra ANCHA la que varía por
// tipo (con transparencia) y la angosta la de color fijo. Recharts no
// tiene un modo nativo "2 series superpuestas en la misma categoría" (2
// <Bar> con dataKey distinto en un mismo <BarChart> siempre se agrupan
// lado a lado) -- se logra apilando 2 BarChart idénticos (mismo
// dominio Y, mismo margin) uno encima del otro con position:absolute:
// el de abajo dibuja la barra ancha BASE de Cuota, el de arriba (fondo
// transparente, ejes ocultos) dibuja SOLO la barra angosta de Cancelado
// en la misma posición X -- al compartir dominio y márgenes exactos,
// coinciden pixel a pixel.
function GraficoCuotaVsCancelado({ data }: { data: CuotasAsociadosResponse }) {
  const filas = data.tipos.map((t) => ({
    tipo: t.tipo,
    cuota: t.total_cuota,
    cancelado: t.total_cancelado,
    color: COLOR_POR_TIPO[t.tipo],
  }));
  const maxValor = Math.max(...filas.map((f) => f.cuota)) * 1.25;
  const margin = { top: 20, right: 8, bottom: 4, left: 8 };
  // ALTO_EJE_X fijo e IDÉNTICO en los 2 <XAxis> -- BUG REAL encontrado
  // verificando con getBoundingClientRect: con `hide` en el eje del
  // segundo BarChart (el de "cancelado"), Recharts deja de reservarle
  // espacio al eje X, así que el ÁREA DE DIBUJO de ese chart queda más
  // alta que la del primero (que sí reserva espacio para sus ticks) --
  // aunque ambos comparten el mismo `domain` y `margin`, el baseline
  // (posición Y del valor 0) terminaba 30px más abajo en el segundo
  // chart que en el primero, así que la barra angosta de "cancelado" NO
  // quedaba alineada con la escala real de "cuota" (se veía más alta de
  // lo que le correspondía). Con `height` explícito e igual en los 2
  // <XAxis> (ocultando ticks/línea con tick={false} en vez de `hide`),
  // los 2 charts reservan exactamente el mismo espacio y comparten el
  // mismo baseline -- verificado: mismo baseline en los 2 (y + height
  // idéntico para las 3 barras anchas y las 3 barras angostas).
  const ALTO_EJE_X = 24;
  return (
    <div style={{ position: "relative", width: "100%", height: ALTO_VISUAL_CUOTAS }}>
      <ResponsiveContainer width="100%" height={ALTO_VISUAL_CUOTAS}>
        <BarChart data={filas} margin={margin}>
          {/* Ejes en blanco puro (#FFFFFF) por instrucción directa --
              línea, marcas y texto, vía `stroke` (línea/marcas) +
              `tick={{fill}}` (texto de las etiquetas, que Recharts NO
              hereda de `stroke`). */}
          <XAxis dataKey="tipo" height={ALTO_EJE_X} fontSize={10} tickLine={false} stroke="#FFFFFF" tick={{ fill: "#FFFFFF" }} />
          <YAxis
            type="number"
            domain={[0, maxValor]}
            tickFormatter={(v: number) => formatQ(v)}
            fontSize={10}
            width={65}
            stroke="#FFFFFF"
            tick={{ fill: "#FFFFFF" }}
          />
          <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
          {/* Barra BASE coloreada POR TIPO con 40% de opacidad (60% de
              transparencia, FILL_OPACITY_BARRA_BASE) -- confirmado
              contra Layout.json que ESTA barra (la ancha) es la que
              varía por tipo, no la angosta de abajo. */}
          <Bar dataKey="cuota" name="Cuota del año" radius={[3, 3, 0, 0]} isAnimationActive={false}>
            {filas.map((f) => (
              <Cell key={f.tipo} fill={f.color} fillOpacity={FILL_OPACITY_BARRA_BASE} />
            ))}
            <LabelList dataKey="cuota" position="top" formatter={(v: number) => formatQ(v)} fontSize={10} fontWeight={700} fill="rgb(var(--color-ink))" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
        <ResponsiveContainer width="100%" height={ALTO_VISUAL_CUOTAS}>
          <BarChart data={filas} margin={margin}>
            <XAxis dataKey="tipo" height={ALTO_EJE_X} tick={false} axisLine={false} tickLine={false} />
            {/* width=65 IGUAL al YAxis visible de arriba -- ver el
                comentario del bug de baseline más arriba: si el ancho
                reservado difiere entre los 2 charts superpuestos,
                dejan de compartir la misma escala/posición X. */}
            <YAxis type="number" domain={[0, maxValor]} width={65} tick={false} axisLine={false} tickLine={false} />
            {/* Overlay de color FIJO (COLOR_TEAL, #2C786C) igual en los
                3 grupos -- confirmado contra Layout.json que lo que
                varía por tipo es la barra ANCHA de abajo, no este
                overlay angosto. */}
            <Bar dataKey="cancelado" name="Cancelado" fill={COLOR_TEAL} barSize={8} isAnimationActive={false}>
              <LabelList dataKey="cancelado" position="top" formatter={(v: number) => formatQ(v)} fontSize={9} fontWeight={700} fill="rgb(var(--color-ink))" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Etiqueta de porcentaje AFUERA del anillo, con una línea conectora
// corta hacia el segmento -- calcado del .pbix real: el % NO va encima
// del anillo (eso lo tapaba), va afuera con un callout, igual que
// cualquier gráfico de dona estándar de Power BI. Compartida por las 2
// donas de esta página.
const RADIAN = Math.PI / 180;
function renderPorcentajeDona({
  cx,
  cy,
  midAngle,
  outerRadius,
  percent,
}: {
  cx: number;
  cy: number;
  midAngle: number;
  innerRadius: number;
  outerRadius: number;
  percent: number;
}) {
  const cos = Math.cos(-midAngle * RADIAN);
  const sin = Math.sin(-midAngle * RADIAN);
  const sx = cx + (outerRadius + 3) * cos;
  const sy = cy + (outerRadius + 3) * sin;
  const ex = cx + (outerRadius + 14) * cos;
  const ey = cy + (outerRadius + 14) * sin;
  const tx = cx + (outerRadius + 18) * cos;
  const ty = cy + (outerRadius + 18) * sin;
  return (
    <g>
      <path d={`M${sx},${sy}L${ex},${ey}`} stroke="rgb(var(--color-ink-faint))" fill="none" />
      <text
        x={tx}
        y={ty}
        fill="rgb(var(--color-ink))"
        fontSize={11}
        fontWeight={700}
        textAnchor={cos >= 0 ? "start" : "end"}
        dominantBaseline="central"
      >
        {`${Math.round(percent * 100)}%`}
      </text>
    </g>
  );
}

// Leyenda de las donas con color de texto FIJO (rgb(var(--color-ink)),
// el mismo tono de alto contraste que el resto de textos del reporte) en
// vez del color por defecto de Recharts (el mismo color de cada porción
// -- en modo oscuro, donde el fondo de la tarjeta también es oscuro, un
// texto teal/marino oscuro sobre ese fondo queda casi ilegible). Tamaño
// de fuente subido de 10 a 12px por el mismo motivo (legibilidad).
function DonutCuotasPorTipo({ data }: { data: CuotasAsociadosResponse }) {
  // Leyenda con solo la letra (A/B/C), calcado del .pbix real -- antes
  // decía "Tipo A" completo, ahí solo va la letra.
  const filas = data.tipos.map((t) => ({ nombre: t.tipo, valor: t.total_cuota, color: COLOR_POR_TIPO[t.tipo] }));
  return (
    <ResponsiveContainer width="100%" height={ALTO_VISUAL_CUOTAS}>
      <PieChart>
        {/* stroke="none" en el <Pie> -- Recharts pone stroke="#fff" por
            default (ver defaultProps de Pie.js), y eso es exactamente
            el borde blanco grueso alrededor de cada porción que no
            existe en el .pbix real. */}
        <Pie
          data={filas}
          dataKey="valor"
          nameKey="nombre"
          innerRadius="42%"
          outerRadius="65%"
          paddingAngle={2}
          stroke="none"
          label={renderPorcentajeDona}
          labelLine={false}
          isAnimationActive={false}
        >
          {filas.map((f) => (
            <Cell key={f.nombre} fill={f.color} />
          ))}
        </Pie>
        <Legend
          wrapperStyle={{ fontSize: 12, color: "rgb(var(--color-ink))" }}
          payload={filas.map((f) => ({ value: f.nombre, type: "square" as const, color: f.color }))}
          formatter={(value: string) => <span style={{ color: "rgb(var(--color-ink))" }}>{value}</span>}
        />
        <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

function DonutRecuperacion({ data }: { data: CuotasAsociadosResponse }) {
  const filas = [
    { nombre: "Cancelado", valor: data.kpis.cancelado, color: COLOR_TURQUESA },
    { nombre: "Por cobrar", valor: data.kpis.por_cobrar, color: COLOR_GRIS_AZULADO },
  ];
  return (
    <ResponsiveContainer width="100%" height={ALTO_VISUAL_CUOTAS}>
      <PieChart>
        <Pie
          data={filas}
          dataKey="valor"
          nameKey="nombre"
          innerRadius="42%"
          outerRadius="65%"
          paddingAngle={2}
          stroke="none"
          label={renderPorcentajeDona}
          labelLine={false}
          isAnimationActive={false}
        >
          {filas.map((f) => (
            <Cell key={f.nombre} fill={f.color} />
          ))}
        </Pie>
        <Legend
          wrapperStyle={{ fontSize: 12, color: "rgb(var(--color-ink))" }}
          payload={filas.map((f) => ({ value: f.nombre, type: "square" as const, color: f.color }))}
          formatter={(value: string) => <span style={{ color: "rgb(var(--color-ink))" }}>{value}</span>}
        />
        <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

// "Otros informes financieros" -- 5 páginas hermanas de "Estados
// financieros" en el Sidebar (mismo patrón: 1 sola ruta + ?vista=, ver
// DashboardFinancieroPage). Cuotas Asociados y Ejecución de gastos (mes/
// acumulado) ya están implementadas; Conciliación Bancaria y Flujo de
// Caja quedan con placeholder (la primera bloqueada por falta de datos
// de Saldo Bancario, la segunda a la espera del layout exacto -- ver
// Sidebar.tsx, que todavía no les da href a esas 2 a propósito).
const VISTAS = ["cuotas-asociados", "conciliacion-bancaria", "flujo-caja", "gastos-mes", "gastos-acumulado"] as const;

export function DashboardOtrosInformesPage() {
  const [searchParams] = useSearchParams();
  const vistaParam = searchParams.get("vista") ?? "cuotas-asociados";
  const vista = VISTAS.includes(vistaParam as (typeof VISTAS)[number])
    ? (vistaParam as (typeof VISTAS)[number])
    : "cuotas-asociados";

  if (vista === "gastos-mes") {
    return <PaginaEjecucionGastos acumulado={false} />;
  }
  if (vista === "gastos-acumulado") {
    return <PaginaEjecucionGastos acumulado={true} />;
  }
  if (vista !== "cuotas-asociados") {
    return <p className="text-sm text-ink-muted">Todavía no implementado.</p>;
  }

  return <PaginaCuotasAsociados />;
}

// Los 12 meses siempre están disponibles como corte de "hasta el mes"
// (a diferencia de Ejecución de Gastos, donde `mesesOpciones` depende de
// qué combinaciones año+mes existen de verdad en los datos, acá
// cualquier mes 1-12 es un corte válido del acumulado de Cancelado
// dentro del año elegido, sin importar si ese mes específico tuvo
// movimientos).
const MES_OPCIONES = MESES_LARGOS.map((nombre, i) => ({ value: String(i + 1), label: nombre }));

function PaginaCuotasAsociados() {
  const [anio, setAnio] = useState("");
  // Selector de Mes -- FUNCIONAL: filtra "Cancelado" (y por lo tanto
  // Saldo/Por cobrar) acumulado hasta el mes elegido dentro del año.
  // "Cuota" no varía por mes (es un monto fijo anual). Ver el docstring
  // de obtener_cuotas_asociados (backend) para el detalle de la
  // corrección: una nota anterior decía que filtrar por mes "no
  // aplicaba" a este concepto -- investigado de nuevo con una consulta
  // directa, el acumulado por mes es correcto (crece mes a mes hasta
  // llegar al total anual verificado en el último mes con datos).
  const [mes, setMes] = useState("");
  const [data, setData] = useState<CuotasAsociadosResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerCuotasAsociados(anio ? Number(anio) : undefined, mes ? Number(mes) : undefined)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        if (!anio) setAnio(String(res.anio));
        if (!mes) setMes(String(res.mes));
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

  const aniosDisponibles = data?.periodos_disponibles ?? [];

  return (
    // Mismo patrón EXACTO que DashboardFinancieroPage (Estados
    // Financieros, 4 páginas ya aprobadas): min-h-[64px] + título
    // text-3xl centrado + filtro FilterYearMonth posicionado con
    // `absolute right-0 top-full mt-5` (debajo de la fila del título,
    // no encima) -- antes esta página tenía su propio min-h-[40px] +
    // text-xl + 2 <select> sueltos, un patrón distinto al ya aprobado.
    <div className="space-y-5">
      <div className="relative flex min-h-[64px] items-center justify-center">
        <Title className="px-4 text-center text-3xl text-ink">{`Cuotas Asociados ${data?.anio ?? ""}`}</Title>
        <div className="absolute right-0 top-full mt-5">
          <FilterYearMonth
            theme="gris"
            anio={anio}
            mes={mes}
            onChangeAnio={setAnio}
            onChangeMes={setMes}
            aniosOpciones={aniosDisponibles.map(String)}
            mesesOpciones={MES_OPCIONES}
          />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        // Layout calcado del .pbix: las 3 tablas van LADO A LADO (no
        // apiladas), compactas, con margen libre a los costados -- antes
        // 94% (casi borde a borde), comparado en pantalla contra el
        // .pbix real se veía demasiado estirado. Reducido al mismo
        // espíritu de ANCHO_TABLA_FINANCIERO (patrón ya usado en
        // Centro de Costo/Estados Financieros: bloque angosto y
        // centrado, no de borde a borde) -- acá algo más ancho que el
        // 55% de una tabla sola porque son 3 tablas de 4 columnas cada
        // una lado a lado, pero con el mismo espíritu de margen visible.
        <div className="mx-auto" style={{ width: "72%" }}>
          {/* Fila de KPI a 80.6% de ESTE contenedor (que a su vez ya es
              72% del área de contenido de la página) = 72% × 80.6% ≈
              58% del área de contenido total -- medido con
              getBoundingClientRect contra el ~58% real del .pbix
              (antes cada tarjeta tenía maxWidth:320 sin tope de fila,
              y las 3 juntas terminaban ocupando ~70% del área de
              contenido, notablemente más ancho que el original). */}
          <div className="mx-auto flex justify-center gap-2" style={{ width: "80.6%" }}>
            <div className="flex-1">
              <KpiCardIcono letra="T" color={COLOR_TEAL} label="Total" valor={formatQ(data.kpis.total)} />
            </div>
            <div className="flex-1">
              <KpiCardIcono letra="C" color={COLOR_TURQUESA} label="Cancelado" valor={formatQ(data.kpis.cancelado)} />
            </div>
            <div className="flex-1">
              <KpiCardIcono letra="P" color={COLOR_GRIS_AZULADO} label="Por cobrar" valor={formatQ(data.kpis.por_cobrar)} />
            </div>
          </div>

          {/* mt-8 (no space-y-3 del padre): espacio considerable entre
              las tarjetas KPI y las tablas, calcado del .pbix real --
              antes estaba pegado (space-y-3 = 12px parejo entre TODAS
              las secciones). Mismo criterio para el mt-8 antes de las
              gráficas, más abajo. */}
          <div className="mt-8 grid grid-cols-3 gap-3">
            {data.tipos.map((t) => (
              <TablaCuotasTipo key={t.tipo} tipo={t} />
            ))}
          </div>

          <div className="mt-8 grid grid-cols-3 gap-3">
            <ChartCard
              theme="financiero"
              colorSeleccionHex={COLOR_TEAL}
              tituloChico
              estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
              title="Cuota del año vs Cancelado"
              chart={<GraficoCuotaVsCancelado data={data} />}
              table={
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-line">
                      <th className="px-2 py-1 text-left text-ink-muted">Tipo</th>
                      <th className="px-2 py-1 text-right text-ink-muted">Cuota del año</th>
                      <th className="px-2 py-1 text-right text-ink-muted">Cancelado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.tipos.map((t) => (
                      <tr key={t.tipo} className="border-b border-line/50">
                        <td className="px-2 py-1 text-ink">{`Tipo ${t.tipo}`}</td>
                        <td className="px-2 py-1 text-right text-ink">{formatQ(t.total_cuota)}</td>
                        <td className="px-2 py-1 text-right text-ink">{formatQ(t.total_cancelado)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            />
            <ChartCard
              theme="financiero"
              colorSeleccionHex={COLOR_TEAL}
              tituloChico
              estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
              title="Cuotas por Tipo"
              chart={<DonutCuotasPorTipo data={data} />}
              table={
                <table className="w-full text-xs">
                  <tbody>
                    {data.tipos.map((t) => (
                      <tr key={t.tipo} className="border-b border-line/50">
                        <td className="px-2 py-1 text-ink">{`Tipo ${t.tipo}`}</td>
                        <td className="px-2 py-1 text-right text-ink">{formatQ(t.total_cuota)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            />
            <ChartCard
              theme="financiero"
              colorSeleccionHex={COLOR_TEAL}
              tituloChico
              estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
              title={`Recuperación Cuota Asociados Año ${data.anio}`}
              chart={<DonutRecuperacion data={data} />}
              table={
                <table className="w-full text-xs">
                  <tbody>
                    <tr className="border-b border-line/50">
                      <td className="px-2 py-1 text-ink">Cancelado</td>
                      <td className="px-2 py-1 text-right text-ink">{formatQ(data.kpis.cancelado)}</td>
                    </tr>
                    <tr>
                      <td className="px-2 py-1 text-ink">Por cobrar</td>
                      <td className="px-2 py-1 text-right text-ink">{formatQ(data.kpis.por_cobrar)}</td>
                    </tr>
                  </tbody>
                </table>
              }
            />
          </div>
        </div>
      )}
    </div>
  );
}

// --- Ejecución de gastos (por mes / acumulado) ------------------------------
//
// Estructura CORREGIDA (ver dashboard_otros_informes.py): la tabla
// agrupa por categoría de gasto (GroupEgresos), no por centro de costo.
// Columnas: Administración | Peso % | Operación | Peso % | Consolidado.
// Debajo, 2 filas de resumen (Presupuesto / Ejecución, misma forma que
// las filas de la tabla) y 3 tarjetas (Administración/Operación/
// Consolidado) con % de ejecución, diferencia y una gráfica chica.
//
// Layout calcado del .pbix: tabla principal ~58% de ancho, ~35% de alto,
// bloque compacto arriba (NO estirada a todo el ancho) -- todo el
// contenido de la página cabe en una sola pantalla, sin scroll.

function FilaTabla({ fila, negrita = false }: { fila: FilaGastoCategoria; negrita?: boolean }) {
  return (
    <tr className={`border-b border-line/50 ${negrita ? "font-semibold" : ""} text-ink`}>
      <td className="truncate px-2 py-0.5" title={fila.categoria}>
        {fila.categoria}
      </td>
      <td className="whitespace-nowrap px-2 py-0.5 text-right">{formatQ(fila.administracion)}</td>
      <td className="whitespace-nowrap px-2 py-0.5 text-right">{formatPercent(fila.peso_administracion)}</td>
      <td className="whitespace-nowrap px-2 py-0.5 text-right">{formatQ(fila.operacion)}</td>
      <td className="whitespace-nowrap px-2 py-0.5 text-right">{formatPercent(fila.peso_operacion)}</td>
      <td className="whitespace-nowrap px-2 py-0.5 text-right">{formatQ(fila.consolidado)}</td>
    </tr>
  );
}

function TablaEjecucionGastos({ data }: { data: EjecucionGastosResponse }) {
  return (
    <div className="overflow-hidden rounded-tremor-default ring-1 ring-line">
      <table className="w-full text-[11px]">
        <thead>
          {/* VERDE_ENCABEZADO (#4CAF50, TablaGrupoExpandible.tsx): el
              mismo verde real que ya usan las demás tablas del sistema
              (leído pixel a pixel de las capturas de referencia) -- antes
              usaba COLOR_TEAL (#3f6f6b), un verde/teal distinto que no
              coincidía con el resto del reporte. */}
          <tr style={{ backgroundColor: VERDE_ENCABEZADO }}>
            <th className="px-2 py-1 text-left font-semibold text-white">Categoría</th>
            <th className="px-2 py-1 text-right font-semibold text-white">Administración</th>
            <th className="px-2 py-1 text-right font-semibold text-white">Peso %</th>
            <th className="px-2 py-1 text-right font-semibold text-white">Operación</th>
            <th className="px-2 py-1 text-right font-semibold text-white">Peso %</th>
            <th className="px-2 py-1 text-right font-semibold text-white">Consolidado</th>
          </tr>
        </thead>
        <tbody style={{ backgroundColor: FINANCIERO_SURFACE }}>
          {data.categorias.map((f) => (
            <FilaTabla key={f.categoria} fila={f} />
          ))}
          <FilaTabla fila={data.fila_total_ejecutado} negrita />
        </tbody>
      </table>
    </div>
  );
}

// Texto de resumen en línea (12 de estos) -- calcado del reporte
// original: NO son tarjetas KPI (sin caja, sin ícono, sin relleno), son
// etiqueta y valor pegados uno al otro en la misma línea, como una
// oración normal de texto, del mismo tamaño que el resto de textos del
// reporte. El diseño anterior (KpiMini) los mostraba como tiras con
// caja/ring/franja de color -- eso es justamente lo que se está
// sacando acá.
function TextoResumen({ label, valor }: { label: string; valor: string }) {
  return (
    <span className="text-xs text-ink">
      <span className="font-semibold">{label}:</span> {valor}
    </span>
  );
}

// Gráfica de columnas verticales Presupuesto vs Ejecutado de un grupo --
// las 3 (Administración/Operación/Consolidado) comparten el mismo alto
// fijo para quedar exactamente del mismo tamaño entre sí, calcado del
// contenedor real del .pbix (w=480 h=325, ratio ~1.48:1 -- 280px de alto
// de gráfica + cabecera del grupo arriba se acerca a esa proporción).
const ALTO_GRAFICA_GRUPO = 280;

// Colores por MÉTRICA (no por grupo) -- ver COLOR_PRESUPUESTO/
// COLOR_EJECUTADO arriba: las 3 gráficas (Administración/Operación/
// Consolidado) usan EXACTAMENTE los mismos 2 colores, calcado del tema
// real del .pbix (las 3 heredan el mismo tema de reporte, sin color
// propio por grupo).
function GraficoColumnasGrupo({ presupuesto, ejecutado }: { presupuesto: number; ejecutado: number }) {
  const filas = [
    { etiqueta: "Presupuesto", valor: presupuesto, color: COLOR_PRESUPUESTO },
    { etiqueta: "Ejecutado", valor: ejecutado, color: COLOR_EJECUTADO },
  ];
  return (
    <ResponsiveContainer width="100%" height={ALTO_GRAFICA_GRUPO}>
      <BarChart data={filas} margin={{ top: 20, right: 16, bottom: 4, left: 4 }}>
        <XAxis dataKey="etiqueta" fontSize={10} tickLine={false} />
        <YAxis type="number" tickFormatter={(v: number) => formatQ(v)} fontSize={10} width={60} stroke="rgb(var(--color-ink-faint))" />
        <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
        <Legend
          wrapperStyle={{ fontSize: 10 }}
          payload={[
            { value: "Presupuesto", type: "square", color: COLOR_PRESUPUESTO },
            { value: "Ejecutado", type: "square", color: COLOR_EJECUTADO },
          ]}
        />
        {/* isAnimationActive={false}: Recharts solo pinta el LabelList
            DESPUÉS de que termina la animación de entrada de las barras
            (Bar.renderLabelList espera isAnimationFinished) -- en la
            práctica esa animación no siempre llega a completar/disparar
            su callback, y la etiqueta de valor quedaba invisible pese a
            estar en el árbol de props. Sin animación, la etiqueta se
            pinta de inmediato y de forma confiable. */}
        <Bar dataKey="valor" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {filas.map((f) => (
            <Cell key={f.etiqueta} fill={f.color} />
          ))}
          <LabelList dataKey="valor" position="top" formatter={(v: number) => formatQ(v)} fontSize={12} fill="rgb(var(--color-ink))" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function PaginaEjecucionGastos({ acumulado }: { acumulado: boolean }) {
  const [anio, setAnio] = useState("");
  const [mes, setMes] = useState("");
  const [data, setData] = useState<EjecucionGastosResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const obtener = acumulado ? obtenerEjecucionGastosAcumulado : obtenerEjecucionGastosMes;

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtener(anio ? Number(anio) : undefined, mes ? Number(mes) : undefined)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        if (!anio) setAnio(String(res.anio));
        if (!mes) setMes(String(res.mes));
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

  function cambiarAnio(nuevoAnio: string) {
    const mesesDelNuevoAnio = periodos.filter((p) => String(p.anio) === nuevoAnio).map((p) => p.mes);
    setAnio(nuevoAnio);
    if (!mesesDelNuevoAnio.includes(Number(mes))) {
      setMes(String(Math.max(...mesesDelNuevoAnio)));
    }
  }

  const tituloPagina = data
    ? acumulado
      ? `Detalle de Ejecución Gastos vs. Presupuesto al ${MESES_LARGOS[data.mes - 1]} ${data.anio}`
      : `Ejecución de Gastos por Mes — ${MESES_LARGOS[data.mes - 1]} ${data.anio}`
    : `Ejecución de Gastos ${acumulado ? "Acumulado" : "por Mes"}`;

  return (
    <div className="space-y-3">
      <div className="relative flex min-h-[40px] items-center justify-center">
        <Title className="px-4 text-center text-xl text-ink">{tituloPagina}</Title>
        <div className="absolute right-0 top-0 flex gap-2">
          <select
            value={anio}
            onChange={(e) => cambiarAnio(e.target.value)}
            className="rounded-tremor-default border border-line bg-surface px-2 py-1 text-xs text-ink"
          >
            {aniosDisponibles.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <select
            value={mes}
            onChange={(e) => setMes(e.target.value)}
            className="rounded-tremor-default border border-line bg-surface px-2 py-1 text-xs text-ink"
          >
            {mesesDelAnio.map((m) => (
              <option key={m} value={m}>
                {MESES_LARGOS[m - 1]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          {/* Tabla dinámica principal + los 12 textos de resumen,
              centrados al mismo 55% de ancho que ya usan las tablas de
              Estados Financieros (ANCHO_TABLA_FINANCIERO en
              DashboardFinancieroPage.tsx) -- antes 58%, un valor propio
              de esta página que no coincidía con el resto del sistema. */}
          <div className="mx-auto space-y-2" style={{ width: "55%" }}>
            <TablaEjecucionGastos data={data} />

            {/* 12 textos de resumen en línea, no tarjetas -- fila 1:
                Presupuesto y Ejecutado de los 3 grupos; fila 2: % de
                Ejecución y Diferencia de los 3 grupos. Mismos 3 grupos
                que ya calcula el backend (Administración/Operación/
                Consolidado, en ese orden fijo). */}
            <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1">
              <TextoResumen label="Presupuesto Admin." valor={formatQ(data.fila_presupuesto.administracion)} />
              <TextoResumen label="Presupuesto Oper." valor={formatQ(data.fila_presupuesto.operacion)} />
              <TextoResumen label="Presupuesto Consol." valor={formatQ(data.fila_presupuesto.consolidado)} />
              <TextoResumen label="Ejecutado Admin." valor={formatQ(data.fila_total_ejecutado.administracion)} />
              <TextoResumen label="Ejecutado Oper." valor={formatQ(data.fila_total_ejecutado.operacion)} />
              <TextoResumen label="Ejecutado Consol." valor={formatQ(data.fila_total_ejecutado.consolidado)} />
              <TextoResumen label="% Ejec. Admin." valor={formatPercent(data.tarjetas[0].porcentaje_ejecucion)} />
              <TextoResumen label="% Ejec. Oper." valor={formatPercent(data.tarjetas[1].porcentaje_ejecucion)} />
              <TextoResumen label="% Ejec. Consol." valor={formatPercent(data.tarjetas[2].porcentaje_ejecucion)} />
              <TextoResumen label="Diferencia Admin." valor={formatQ(data.tarjetas[0].diferencia)} />
              <TextoResumen label="Diferencia Oper." valor={formatQ(data.tarjetas[1].diferencia)} />
              <TextoResumen label="Diferencia Consol." valor={formatQ(data.tarjetas[2].diferencia)} />
            </div>
          </div>

          {/* Las 3 gráficas de columnas (Administración/Operación/
              Consolidado) van más anchas que la tabla, a propósito --
              calcado del .pbix (w=480 cada una, las 3 iguales entre sí). */}
          <div className="mx-auto grid grid-cols-3 gap-3 pt-2" style={{ width: "90%" }}>
            {data.tarjetas.map((t) => (
              <div key={t.grupo} className="overflow-hidden rounded-tremor-default ring-1 ring-line" style={{ backgroundColor: FINANCIERO_SURFACE }}>
                <div className="px-2 py-1 text-center text-xs font-semibold text-ink">{t.grupo}</div>
                <GraficoColumnasGrupo presupuesto={t.presupuesto} ejecutado={t.ejecutado} />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

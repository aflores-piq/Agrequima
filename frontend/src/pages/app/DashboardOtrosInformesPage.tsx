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
  TarjetaResumenGasto,
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
          {/* Tooltip calcado EXACTO del patrón aprobado de Estados
              Financieros (ver TresBarrasResultado.tsx): fondo
              FINANCIERO_SURFACE (el mismo gris de las tarjetas/celdas,
              NO rgb(var(--color-bg-surface)) -- esa es la variable
              general de la app, que resuelve a slate-900/#0F172A en
              oscuro, un azul marino inventado que nunca se usó en las
              páginas aprobadas) + labelStyle/itemStyle en color ink. */}
          <Tooltip
            cursor={{ fill: "rgb(var(--color-ink-faint) / 0.08)" }}
            formatter={(v: number) => formatQ(v)}
            contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
            labelStyle={{ color: "rgb(var(--color-ink))" }}
            itemStyle={{ color: "rgb(var(--color-ink))" }}
          />
          {/* Barra BASE coloreada POR TIPO con 40% de opacidad (60% de
              transparencia, FILL_OPACITY_BARRA_BASE) -- confirmado
              contra Layout.json que ESTA barra (la ancha) es la que
              varía por tipo, no la angosta de abajo. */}
          <Bar dataKey="cuota" name="Cuota del año" radius={[3, 3, 0, 0]} isAnimationActive={false}>
            {filas.map((f) => (
              <Cell key={f.tipo} fill={f.color} fillOpacity={FILL_OPACITY_BARRA_BASE} />
            ))}
            {/* fillOpacity={1} EXPLÍCITO -- BUG REAL encontrado
                inspeccionando el DOM real: Recharts filtra el
                fillOpacity de los <Cell> de arriba hacia el <text> del
                LabelList hermano (confirmado con fill-opacity="0.4"
                real en el atributo del <text>, mismo valor que
                FILL_OPACITY_BARRA_BASE) -- por eso la etiqueta "Q
                280,000" salía gris (blanco al 40% sobre fondo oscuro),
                pese a que su propio `fill` ya era el ink correcto. Con
                fillOpacity={1} en el propio LabelList se corta esa
                herencia y queda 100% opaco. */}
            <LabelList
              dataKey="cuota"
              position="top"
              formatter={(v: number) => formatQ(v)}
              fontSize={10}
              fontWeight={700}
              fill="rgb(var(--color-ink))"
              fillOpacity={1}
            />
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
        {/* Mismo tooltip aprobado que BalanceDonut.tsx (Estados
            Financieros): fondo FINANCIERO_SURFACE + labelStyle/
            itemStyle en ink, sin `cursor` (las donas no lo necesitan,
            es un concepto de gráficas cartesianas/de barras). */}
        <Tooltip
          formatter={(v: number) => formatQ(v)}
          contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
          labelStyle={{ color: "rgb(var(--color-ink))" }}
          itemStyle={{ color: "rgb(var(--color-ink))" }}
        />
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
        <Tooltip
          formatter={(v: number) => formatQ(v)}
          contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
          labelStyle={{ color: "rgb(var(--color-ink))" }}
          itemStyle={{ color: "rgb(var(--color-ink))" }}
        />
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
          {/* Reducido de 80.6% a 58% de ESTE contenedor (72% del área de
              contenido) = 72%×58% ≈ 42% del área de contenido total.
              Rondas anteriores habían llegado a ~56.7% (verificado
              exacto en 2 navegadores distintos: el Browser pane de
              Claude Y un Chromium de Playwright 100% independiente,
              sin caché previo -- ambos dieron el mismo número, así que
              NO era un problema de caché ni de medición) pero a ese
              ancho cada tarjeta (~275px) deja un hueco vacío visible
              entre el ícono y el texto (KpiCardIcono alinea el
              texto al borde derecho de la tarjeta, no pegado al
              ícono) -- la diferencia con el .pbix se notaba ahí, no
              en el % de la fila en sí. Bajado agresivamente a ~42%
              (dentro del rango 40-45% pedido) para que la tarjeta sea
              angosta de verdad y el hueco deje de ser visible. */}
          <div className="mx-auto flex justify-center gap-2" style={{ width: "58%" }}>
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

function FilaTabla({
  fila,
  negrita = false,
  ocultarCeros = false,
  fondoTotal = false,
  // pivotTable real: values.wordWrap=true -- el nombre de categoría debe
  // poder pasar a una 2da línea, NO truncarse con "..." (antes usaba
  // `truncate`, que corta nombres largos como "Literatura y Material
  // para Capacitación Programa Educación").
  ajustarTexto = false,
}: {
  fila: FilaGastoCategoria;
  negrita?: boolean;
  // Página "Ejecución gastos por mes" (pivotTable real del .pbix, sin
  // propiedad visual explícita de "vacío" -- las categorías vienen de un
  // COALESCE(...,0), así que un 0 acá siempre significa "sin dato para
  // ese grupo", nunca un monto real de Q0. Celda vacía en vez de "Q0"/
  // "0.0%" para esos casos.
  ocultarCeros?: boolean;
  // rowTotal.backColor='#4CAF50' + applyToHeaders=true en el pivotTable
  // real -- la fila "Total ejecutado" lleva fondo verde en TODAS sus
  // celdas (incluida la del nombre), no solo texto en negrita.
  fondoTotal?: boolean;
  ajustarTexto?: boolean;
}) {
  const celda = (valor: number, formatear: (v: number) => string) => (ocultarCeros && valor === 0 ? "" : formatear(valor));
  const claseCelda = `whitespace-nowrap px-2 py-1 text-right ${fondoTotal ? "text-white" : ""}`;
  return (
    <tr
      className={`border-b border-line/50 ${negrita ? "font-semibold" : ""} text-ink`}
      style={fondoTotal ? { backgroundColor: VERDE_ENCABEZADO } : undefined}
    >
      <td
        className={`px-2 py-1 ${ajustarTexto ? "whitespace-normal break-words" : "truncate"} ${fondoTotal ? "text-white" : ""}`}
        title={ajustarTexto ? undefined : fila.categoria}
      >
        {fila.categoria}
      </td>
      <td className={claseCelda}>{celda(fila.administracion, formatQ)}</td>
      <td className={claseCelda}>{celda(fila.peso_administracion, formatPercent)}</td>
      <td className={claseCelda}>{celda(fila.operacion, formatQ)}</td>
      <td className={claseCelda}>{celda(fila.peso_operacion, formatPercent)}</td>
      <td className={claseCelda}>{celda(fila.consolidado, formatQ)}</td>
    </tr>
  );
}

// Ancho de columnas calcado del pivotTable real de cada página
// (columnWidth del Layout.json) -- son 2 medidas DAX/páginas distintas
// ("Centros de Costo" vs "Centros de Costo acumulado") con anchos
// propios, no el mismo layout reusado:
// mensual: GroupEgresos≈542px de ~1115px (49%), EjecutadoOperativo≈9%.
// acumulado: GroupEgresos≈483px de ~1113px (43%), EjecutadoAdministrativo≈
// 14%, EjecutadoOperativo≈11%, TotalEjecutado≈12%, ambos Peso≈9%.
const ANCHOS_COLUMNA_MENSUAL = ["49%", "12%", "9%", "12%", "9%", "9%"];
const ANCHOS_COLUMNA_ACUMULADO = ["43%", "14%", "9%", "11%", "9%", "12%"];

function ColgroupEjecucion({ variante }: { variante: "mensual" | "acumulado" }) {
  const anchos = variante === "mensual" ? ANCHOS_COLUMNA_MENSUAL : ANCHOS_COLUMNA_ACUMULADO;
  return (
    <colgroup>
      {anchos.map((ancho, i) => (
        <col key={i} style={{ width: ancho }} />
      ))}
    </colgroup>
  );
}

function TablaEjecucionGastos({ data, variante }: { data: EjecucionGastosResponse; variante: "mensual" | "acumulado" }) {
  const esAcumulado = variante === "acumulado";
  // pivotTable real: values/columnHeaders/rowHeaders.fontSize=14D en las
  // 2 páginas -- antes esta tabla usaba 11px (un valor propio de una
  // versión anterior, nunca actualizado al dato real ya extraído del
  // Layout.json).
  const claseTabla = "w-full text-sm";
  // columnHeaders real: alignment='Center' en las 2 páginas. bold: la
  // página mensual lo desactiva explícitamente (bold=false); la página
  // acumulado NO trae esa propiedad, así que queda con el bold por
  // default del widget pivotTable de Power BI -- son 2 configs
  // distintas, confirmado comparando ambos pivotTable.config.
  const claseHeader = `px-2 py-1.5 text-center text-white ${esAcumulado ? "font-semibold" : "font-normal"}`;
  return (
    <div className="overflow-hidden rounded-tremor-default ring-1 ring-line">
      <table className={claseTabla}>
        <ColgroupEjecucion variante={variante} />
        <thead>
          {/* VERDE_ENCABEZADO (#4CAF50, TablaGrupoExpandible.tsx): el
              mismo verde real que ya usan las demás tablas del sistema
              (leído pixel a pixel de las capturas de referencia) -- antes
              usaba COLOR_TEAL (#3f6f6b), un verde/teal distinto que no
              coincidía con el resto del reporte. */}
          <tr style={{ backgroundColor: VERDE_ENCABEZADO }}>
            <th className={claseHeader}>Gastos</th>
            <th className={claseHeader}>Administración</th>
            <th className={claseHeader}>Peso en %</th>
            <th className={claseHeader}>Operación</th>
            <th className={claseHeader}>Peso en %</th>
            <th className={claseHeader}>Consolidado</th>
          </tr>
        </thead>
        <tbody style={{ backgroundColor: FINANCIERO_SURFACE }}>
          {data.categorias.map((f) => (
            <FilaTabla key={f.categoria} fila={f} ocultarCeros ajustarTexto />
          ))}
          <FilaTabla fila={data.fila_total_ejecutado} negrita ocultarCeros fondoTotal ajustarTexto />
        </tbody>
      </table>
    </div>
  );
}

// Ancho de columna en fracciones de grid (mismo valor que ANCHOS_COLUMNA_*
// de arriba, para que ResumenPresupuestoEjecucion quede pixel-alineado
// con las columnas de la tabla de encima).
function anchosGrid(variante: "mensual" | "acumulado"): string {
  return (variante === "mensual" ? ANCHOS_COLUMNA_MENSUAL : ANCHOS_COLUMNA_ACUMULADO).join(" ");
}

// Bloque "Presupuesto"/"Ejecución" -- en el .pbix real es un elemento
// INDEPENDIENTE debajo de la tabla (2 textbox + 12 advanceCard sueltos,
// no parte del pivotTable), con su propia franja de fondo y cada valor
// en su propia caja. Antes estas 2 filas vivían DENTRO de la tabla
// (como si fueran más filas del pivotTable) -- error de esta misma
// tarea, corregido acá.
function FilaResumenGrande({ fila, variante }: { fila: FilaGastoCategoria; variante: "mensual" | "acumulado" }) {
  const valores = [
    { texto: formatQ(fila.administracion), negrita: false },
    { texto: formatPercent(fila.peso_administracion), negrita: true },
    { texto: formatQ(fila.operacion), negrita: false },
    { texto: formatPercent(fila.peso_operacion), negrita: true },
    { texto: formatQ(fila.consolidado), negrita: false },
  ];
  return (
    <div
      className="grid items-center gap-1.5 rounded px-2 py-2"
      style={{ backgroundColor: FINANCIERO_SURFACE, gridTemplateColumns: anchosGrid(variante) }}
    >
      <div className="truncate text-base font-bold text-ink">{fila.categoria}</div>
      {/* Mismo gris que la tabla y las tarjetas de las gráficas
          (FINANCIERO_SURFACE) -- antes usaba bg-app (--color-bg-app,
          casi negro en modo oscuro), un token distinto que no coincidía
          con el resto de la página. Sin ring/borde: las celdas quedan
          separadas solo por el gap del grid, sin contorno oscuro -- el
          ring-1 anterior se veía como un borde/sombra marcada, no como
          el reporte real. */}
      {valores.map((v, i) => (
        <div
          key={i}
          className={`rounded px-2 py-1 text-right text-sm text-ink ${v.negrita ? "font-bold" : ""}`}
          style={{ backgroundColor: FINANCIERO_SURFACE }}
        >
          {v.texto}
        </div>
      ))}
    </div>
  );
}

function ResumenPresupuestoEjecucion({ data, variante }: { data: EjecucionGastosResponse; variante: "mensual" | "acumulado" }) {
  return (
    // mt-8 (32px) separa este bloque de la tabla, como en el reporte
    // real -- antes las 2 filas quedaban pegadas dentro de la tabla.
    <div className="mt-8 flex flex-col gap-2">
      <FilaResumenGrande fila={data.fila_presupuesto} variante={variante} />
      <FilaResumenGrande fila={data.fila_ejecucion} variante={variante} />
    </div>
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

// EJE Y COMPARTIDO entre las 3 gráficas -- en el .pbix real el `end` del
// eje Y es una medida DAX distinta por página (_Calculos.EscalaEjeY en
// mensual, _Calculos.EscalaEjeY_CentroAcumulado en acumulado), ninguna
// extraíble como literal desde Layout.json.
// Mensual: se fija en 1,000,000 porque el usuario confirmó viendo el
// reporte real que los 3 grupos caben en esa escala para Agosto 2026 (un
// valor puntual validado, no una fórmula).
// Acumulado: NO puede ser el mismo literal fijo -- los montos acumulados
// crecen mes a mes (un acumulado a Diciembre es ~12x uno a Enero), así
// que se calcula dinámicamente a partir de los datos reales cargados
// (calcularEscalaEjeY), redondeando hacia arriba al siguiente
// 1/2/5×10^n "número redondo" como hace Power BI.
const ESCALA_EJE_Y_MENSUAL = { max: 1_000_000, ticks: [0, 500_000, 1_000_000] };

// La medida DAX real (_Calculos.EscalaEjeY / EscalaEjeY_CentroAcumulado)
// no es extraíble desde Layout.json -- esto es una aproximación por
// "número redondo" (1/2/5×10^n), no la fórmula real. Si el usuario
// puede pasar el DAX desde Power BI Desktop, se reemplaza por la lógica
// exacta.
function calcularEscalaEjeY(valores: number[]): { max: number; ticks: number[] } {
  const maxValor = Math.max(0, ...valores);
  if (maxValor <= 0) return { max: 1, ticks: [0, 0.5, 1] };
  const magnitud = Math.pow(10, Math.floor(Math.log10(maxValor)));
  const normalizado = maxValor / magnitud;
  const base = normalizado <= 1 ? 1 : normalizado <= 2 ? 2 : normalizado <= 5 ? 5 : 10;
  const max = base * magnitud;
  return { max, ticks: [0, max / 2, max] };
}

// Último día real del mes (28/29 de febrero según año bisiesto, 30 o 31
// el resto) -- para el título de "Ejecución gastos acumulado".
function ultimoDiaDelMes(anio: number, mes: number): number {
  return new Date(anio, mes, 0).getDate();
}

// Chips de cabecera de cada tarjeta (nombre + % ejecución a la
// izquierda, diferencia a la derecha) -- calcado de los 2 advanceCard
// "chip" por grupo del .pbix real, que van AFUERA y ARRIBA de la
// tarjeta de la gráfica (visualHeader de la gráfica en sí queda oculto,
// show=false en chart_config.json: el título real de cada grupo vive en
// estos chips externos, no dentro de la tarjeta ni centrados).
function ChipsResumenGrupo({ tarjeta }: { tarjeta: TarjetaResumenGasto }) {
  return (
    <div className="flex items-center justify-between gap-2 px-1 pb-1 text-xs text-ink">
      <span className="flex items-center gap-2">
        {/* Los 3 chips (nombre, % y diferencia) van en la MISMA caja
            gris FINANCIERO_SURFACE, sin ring/borde -- antes el chip del
            nombre era texto suelto sin caja, y los otros 2 llevaban
            ring-1 (que en la práctica se veía como un contorno/sombra
            oscura marcada, no como el reporte real). */}
        <span className="rounded px-2 py-0.5 font-semibold" style={{ backgroundColor: FINANCIERO_SURFACE }}>
          {tarjeta.grupo}
        </span>
        <span className="rounded px-2 py-0.5" style={{ backgroundColor: FINANCIERO_SURFACE }}>
          {tarjeta.porcentaje_ejecucion.toFixed(2)}%
        </span>
      </span>
      <span className="rounded px-2 py-0.5" style={{ backgroundColor: FINANCIERO_SURFACE }}>
        {formatQ(tarjeta.diferencia)}
      </span>
    </div>
  );
}

// Gráfica de columnas verticales Presupuesto vs Ejecutado -- calcada del
// clusteredColumnChart real (chart_config.json de "Centros de Costo" /
// "Centros de Costo acumulado", visualmente idénticos salvo la escala
// del eje Y): UNA sola categoría con 2 series (Presupuesto/Ejecutado)
// juntas y centradas -- antes cada una vivía en su propia categoría del
// eje X, lo que las separaba a los extremos de la gráfica en vez de
// dejarlas lado a lado como en el reporte real. barGap/barSize
// calibrados para que la etiqueta de valor (arriba de cada barra) no
// toque la de la barra vecina en el caso más ancho real (acumulado,
// 7 dígitos: "Q6,943,846"/"Q8,440,050") -- verificado midiendo el
// bounding box real de las 2 etiquetas en el navegador, no a ojo. Eje Y
// con dominio y ticks pasados por props (compartido entre las 3
// gráficas de la página), SIN línea de eje visible, etiquetas en
// negrita. Etiqueta de valor en negrita arriba de cada barra
// (labels.bold=true en el visual real; color adaptativo al tema en vez
// del blanco fijo del visual real -- en modo oscuro (el único que tiene
// el .pbix) ese color adaptativo YA se ve blanco; en modo claro, que el
// .pbix no contempla, queda legible en vez de invisible).
function GraficoColumnasGrupoEjecucion({
  presupuesto,
  ejecutado,
  escalaMax,
  escalaTicks,
}: {
  presupuesto: number;
  ejecutado: number;
  escalaMax: number;
  escalaTicks: number[];
}) {
  const fila = [{ presupuesto, ejecutado }];
  const estiloEtiquetaEje = { fontSize: 10, fontWeight: 700, fill: "rgb(var(--color-ink))" };
  return (
    <ResponsiveContainer width="100%" height={ALTO_GRAFICA_GRUPO}>
      <BarChart data={fila} margin={{ top: 24, right: 16, bottom: 4, left: 4 }} barGap={24}>
        <XAxis dataKey={() => ""} tick={false} axisLine={false} tickLine={false} />
        <YAxis
          type="number"
          domain={[0, escalaMax]}
          ticks={escalaTicks}
          tickFormatter={(v: number) => formatQ(v)}
          tick={estiloEtiquetaEje}
          axisLine={false}
          tickLine={false}
          // 60px alcanzaba para "Q1,000,000" (mensual) pero no para
          // "Q10,000,000" (acumulado, 1 dígito más) -- la etiqueta se
          // salía por la izquierda del área del SVG y quedaba cortada
          // por el overflow-hidden de la tarjeta. Se calcula el ancho
          // según el texto más largo de los ticks reales de cada
          // gráfica en vez de un valor fijo.
          width={Math.max(60, 12 + Math.max(...escalaTicks.map((v) => formatQ(v).length)) * 6)}
        />
        <Tooltip
          cursor={{ fill: "rgb(var(--color-ink-faint) / 0.08)" }}
          formatter={(v: number) => formatQ(v)}
          contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
          labelStyle={{ color: "rgb(var(--color-ink))" }}
          itemStyle={{ color: "rgb(var(--color-ink))" }}
        />
        {/* formatter fuerza el MISMO color de texto en las 2 entradas --
            sin esto, Recharts pinta "Presupuesto" con un gris apagado
            por default en vez del color de texto normal (bug reportado:
            se veía "como deshabilitado" comparado con "Ejecutado"). */}
        <Legend
          wrapperStyle={{ fontSize: 10 }}
          formatter={(value: string) => <span style={{ color: "rgb(var(--color-ink))" }}>{value}</span>}
          payload={[
            { value: "Presupuesto", type: "circle", color: COLOR_PRESUPUESTO },
            { value: "Ejecutado", type: "circle", color: COLOR_EJECUTADO },
          ]}
        />
        <Bar dataKey="presupuesto" fill={COLOR_PRESUPUESTO} radius={[4, 4, 0, 0]} isAnimationActive={false} barSize={58}>
          <LabelList
            dataKey="presupuesto"
            position="top"
            formatter={(v: number) => formatQ(v)}
            fontSize={12}
            fontWeight={700}
            fill="rgb(var(--color-ink))"
            fillOpacity={1}
          />
        </Bar>
        <Bar dataKey="ejecutado" fill={COLOR_EJECUTADO} radius={[4, 4, 0, 0]} isAnimationActive={false} barSize={58}>
          <LabelList
            dataKey="ejecutado"
            position="top"
            formatter={(v: number) => formatQ(v)}
            fontSize={12}
            fontWeight={700}
            fill="rgb(var(--color-ink))"
            fillOpacity={1}
          />
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

  // "Ejecución Gastos {Mes} {Año}" (mensual) -- queda igual, ya
  // confirmado contra el reporte real. Acumulado: texto real confirmado
  // por el usuario contra su captura de Power BI -- "Detalle de
  // Ejecución Gastos vs. Presupuesto al {último día del mes} de {Mes} de
  // {Año}", con el día siendo el último día REAL del mes (28/29 en
  // febrero según año bisiesto, 30 o 31 el resto).
  const tituloPagina = data
    ? acumulado
      ? `Detalle de Ejecución Gastos vs. Presupuesto al ${ultimoDiaDelMes(data.anio, data.mes)} de ${MESES_LARGOS[data.mes - 1]} de ${data.anio}`
      : `Ejecución Gastos ${MESES_LARGOS[data.mes - 1]} ${data.anio}`
    : `Ejecución de Gastos ${acumulado ? "Acumulado" : "por Mes"}`;

  // Escala del eje Y: mensual usa el valor fijo validado contra Agosto
  // 2026 real; acumulado la calcula de los datos reales cargados, porque
  // los montos acumulados crecen mes a mes (ver comentario en
  // calcularEscalaEjeY).
  const escalaEjeY =
    acumulado && data ? calcularEscalaEjeY(data.tarjetas.flatMap((t) => [t.presupuesto, t.ejecutado])) : ESCALA_EJE_Y_MENSUAL;

  return (
    <div className="space-y-3">
      <div className="relative flex min-h-[40px] items-center justify-center">
        <Title className="px-4 text-center text-2xl font-bold text-ink">{tituloPagina}</Title>
        {/* Selector "Año y Mes" único (slicer real del .pbix, mismo en
            las 2 páginas) -- mismo FilterYearMonth ya aprobado y usado en
            Estados Financieros. */}
        <div className="absolute right-0 top-0">
          <FilterYearMonth
            label="Año y Mes"
            anio={anio}
            mes={mes}
            onChangeAnio={cambiarAnio}
            onChangeMes={setMes}
            aniosOpciones={aniosDisponibles.map(String)}
            mesesOpciones={mesesDelAnio.map((m) => ({ value: String(m), label: MESES_LARGOS[m - 1] }))}
            theme="gris"
          />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          {/* Tabla + filas Presupuesto/Ejecución, centrada y más angosta
              que el ancho total (60%, calcado de la proporción tabla vs.
              lienzo del .pbix real: ~1115px de 1920px ≈ 58%). Mismo
              componente para mensual y acumulado -- solo cambian anchos
              de columna y negrita de encabezado (ver TablaEjecucionGastos). */}
          <div className="mx-auto" style={{ width: "60%" }}>
            <TablaEjecucionGastos data={data} variante={acumulado ? "acumulado" : "mensual"} />
            <ResumenPresupuestoEjecucion data={data} variante={acumulado ? "acumulado" : "mensual"} />
          </div>

          {/* Las 3 gráficas (Administración/Operación/Consolidado) con
              chips de resumen AFUERA y ARRIBA de la tarjeta -- calcado
              del .pbix (w=480 cada una, las 3 iguales entre sí,
              separadas con espacio real). */}
          <div className="mx-auto grid grid-cols-3 gap-4 pt-3" style={{ width: "90%" }}>
            {data.tarjetas.map((t) => (
              <div key={t.grupo}>
                <ChipsResumenGrupo tarjeta={t} />
                <div className="overflow-hidden rounded-tremor-default ring-1 ring-line" style={{ backgroundColor: FINANCIERO_SURFACE }}>
                  <GraficoColumnasGrupoEjecucion
                    presupuesto={t.presupuesto}
                    ejecutado={t.ejecutado}
                    escalaMax={escalaEjeY.max}
                    escalaTicks={escalaEjeY.ticks}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

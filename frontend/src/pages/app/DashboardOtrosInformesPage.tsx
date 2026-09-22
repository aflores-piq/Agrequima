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
import { FINANCIERO_SURFACE, KpiCardIcono, VERDE_ENCABEZADO } from "../../components/TablaGrupoExpandible";
import { formatPercent, formatQ, MESES_LARGOS } from "../../utils/format";
import type {
  CuotasAsociadosResponse,
  EjecucionGastosResponse,
  FilaGastoCategoria,
  TipoCuotaAsociados,
} from "../../types/dashboardOtrosInformes";

// Mismos colores de identidad que Estados Financieros (teal/coral/azul,
// ver DashboardFinancieroPage) para que "Otros informes financieros" se
// vea consistente con el resto de Financiero -- acá se le suma un color
// más (marino) para el tercer tipo (C) de Cuotas Asociados.
const COLOR_TEAL = "#3f6f6b";
const COLOR_CORAL = "#e87471";
const COLOR_AZUL = "#507eaa";
const COLOR_MARINO = "#375b7d";

const COLOR_POR_TIPO: Record<string, string> = { A: COLOR_TEAL, B: COLOR_AZUL, C: COLOR_MARINO };

// Colores REALES de OBJETO del visual (Layout.json a nivel de visual, no
// del tema general del reporte) para las gráficas de Presupuesto vs
// Ejecutado en Centro de Costo -- las 3 gráficas (Administración/
// Operación/Consolidado) usan un color por MÉTRICA (no por grupo),
// idéntico en las 3. El primer color pasado (#118DFF/#12239E) resultó
// ser el color del TEMA general del reporte, no el del visual -- se
// reemplaza por el valor correcto leído a nivel de objeto.
const COLOR_PRESUPUESTO = "#5C7285";
const COLOR_EJECUTADO = "#A7B49E";

/** Etiqueta de valor en miles, sin decimales (ej. "160K") -- calcado de
 * la unidad de miles del .pbix para las etiquetas sobre cada barra. */
function formatMiles(v: number): string {
  return `${Math.round(v / 1000).toLocaleString("es-GT")}K`;
}

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
// datos. Medido con DevTools (getBoundingClientRect): con 430px las 3
// cajas SÍ salían exactamente iguales (430px las 3), pero el contenido
// de Tipo C (18 filas + total = 436px reales) no entraba completo y
// quedaba con scroll interno, tapando la fila "Total C" -- por eso se
// veía "distinta" pese a tener la misma caja. 445px le da margen a las
// 18 filas de Tipo C para entrar completas sin scroll; overflow-y-auto
// queda como respaldo si algún año tuviera todavía más filas.
const ALTO_TABLA_CUOTAS = 445;

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
            otras no tengan. Columna "Nombre" reducida de 40% a 32% --
            los nombres de empresa no necesitan tanto ancho (ya van
            truncados con "…" si hace falta) y el 40% original dejaba un
            hueco en blanco de más en esa columna. */}
        <table className="w-full table-fixed text-[11px]">
          <colgroup>
            <col className="w-[32%]" />
            <col className="w-[23%]" />
            <col className="w-[23%]" />
            <col className="w-[22%]" />
          </colgroup>
          <thead>
            <tr style={{ backgroundColor: COLOR_POR_TIPO[tipo.tipo] }}>
              <th className="truncate px-2 py-1 text-left font-semibold text-white">{`Tipo ${tipo.tipo}`}</th>
              <th className="px-2 py-1 text-right font-semibold text-white">Cuota</th>
              <th className="px-2 py-1 text-right font-semibold text-white">Canc.</th>
              <th className="px-2 py-1 text-right font-semibold text-white">Saldo</th>
            </tr>
          </thead>
          <tbody style={{ backgroundColor: FINANCIERO_SURFACE }}>
            {tipo.filas.map((f) => (
              <tr key={f.nombre} className="border-b border-line/50">
                <td className="truncate px-2 py-0.5 text-ink" title={f.nombre}>
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
// h≈415 los 3 iguales entre sí).
const ALTO_VISUAL_CUOTAS = 190;

// Desglosada por Tipo (A/B/C) -- NO es solo el total del año, son datos
// DISTINTOS: el .pbix real muestra 6 barras (Cuota y Cancelado de cada
// Tipo, 3 pares agrupados), no 2 barras con el total agregado de los 3
// tipos. El dato por tipo YA está disponible en data.tipos (mismo campo
// que ya usan las 3 tablas de arriba, total_cuota/total_cancelado) --
// no hace falta tocar el backend, ya trae el desglose.
function GraficoCuotaVsCancelado({ data }: { data: CuotasAsociadosResponse }) {
  const filas = data.tipos.map((t) => ({
    tipo: `Tipo ${t.tipo}`,
    cuota: t.total_cuota,
    cancelado: t.total_cancelado,
  }));
  return (
    // SIN layout="vertical": layout="vertical" en Recharts pone el eje de
    // categoría en Y y las barras ACOSTADAS (horizontal) -- eso era el
    // bug. El default (sin el prop) es columnas PARADAS (verticales),
    // que es lo que pide el .pbix real. 2 <Bar> con dataKey distinto bajo
    // el mismo XAxis categórico = barras agrupadas de a pares (Recharts
    // las dibuja lado a lado automáticamente, sin configuración extra).
    <ResponsiveContainer width="100%" height={ALTO_VISUAL_CUOTAS}>
      <BarChart data={filas} margin={{ top: 16, right: 8, bottom: 4, left: 8 }}>
        <XAxis dataKey="tipo" fontSize={10} tickLine={false} />
        <YAxis type="number" tickFormatter={(v: number) => formatMiles(v)} fontSize={10} width={40} stroke="rgb(var(--color-ink-faint))" />
        <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
        <Bar dataKey="cuota" name="Cuota del año" fill={COLOR_TEAL} radius={[3, 3, 0, 0]} isAnimationActive={false}>
          <LabelList dataKey="cuota" position="top" formatter={(v: number) => formatMiles(v)} fontSize={9} fill="rgb(var(--color-ink))" />
        </Bar>
        <Bar dataKey="cancelado" name="Cancelado" fill={COLOR_AZUL} radius={[3, 3, 0, 0]} isAnimationActive={false}>
          <LabelList dataKey="cancelado" position="top" formatter={(v: number) => formatMiles(v)} fontSize={9} fill="rgb(var(--color-ink))" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Etiqueta de porcentaje SOBRE el anillo de la dona (a mitad de camino
// entre el radio interno y externo) -- calcado del .pbix real, que
// muestra el % directamente sobre cada segmento, no solo en la leyenda
// de abajo. Compartida por las 2 donas de esta página.
const RADIAN = Math.PI / 180;
function renderPorcentajeDona({
  cx,
  cy,
  midAngle,
  innerRadius,
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
  const radio = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radio * Math.cos(-midAngle * RADIAN);
  const y = cy + radio * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="#ffffff" fontSize={11} fontWeight={700} textAnchor="middle" dominantBaseline="central">
      {`${Math.round(percent * 100)}%`}
    </text>
  );
}

// Leyenda de las donas con color de texto FIJO (rgb(var(--color-ink)),
// el mismo tono de alto contraste que el resto de textos del reporte) en
// vez del color por defecto de Recharts (el mismo color de cada porción
// -- en modo oscuro, donde el fondo de la tarjeta también es oscuro, un
// texto teal/marino oscuro sobre ese fondo queda casi ilegible). Tamaño
// de fuente subido de 10 a 12px por el mismo motivo (legibilidad).
function DonutCuotasPorTipo({ data }: { data: CuotasAsociadosResponse }) {
  const filas = data.tipos.map((t) => ({ nombre: `Tipo ${t.tipo}`, valor: t.total_cuota, color: COLOR_POR_TIPO[t.tipo] }));
  return (
    <ResponsiveContainer width="100%" height={ALTO_VISUAL_CUOTAS}>
      <PieChart>
        <Pie
          data={filas}
          dataKey="valor"
          nameKey="nombre"
          innerRadius="50%"
          outerRadius="80%"
          paddingAngle={2}
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
    { nombre: "Cancelado", valor: data.kpis.cancelado, color: COLOR_TEAL },
    { nombre: "Por cobrar", valor: data.kpis.por_cobrar, color: COLOR_CORAL },
  ];
  return (
    <ResponsiveContainer width="100%" height={ALTO_VISUAL_CUOTAS}>
      <PieChart>
        <Pie
          data={filas}
          dataKey="valor"
          nameKey="nombre"
          innerRadius="50%"
          outerRadius="80%"
          paddingAngle={2}
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

function PaginaCuotasAsociados() {
  const [anio, setAnio] = useState("");
  const [data, setData] = useState<CuotasAsociadosResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerCuotasAsociados(anio ? Number(anio) : undefined)
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

  const aniosDisponibles = data?.periodos_disponibles ?? [];

  return (
    <div className="space-y-3">
      <div className="relative flex min-h-[40px] items-center justify-center">
        <Title className="px-4 text-center text-xl text-ink">{`Cuotas Asociados ${data?.anio ?? ""}`}</Title>
        <div className="absolute right-0 top-0">
          <select
            value={anio}
            onChange={(e) => setAnio(e.target.value)}
            className="rounded-tremor-default border border-line bg-surface px-2 py-1 text-xs text-ink"
          >
            {aniosDisponibles.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
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
        <div className="mx-auto space-y-3" style={{ width: "72%" }}>
          {/* max-width en el wrapper de cada tarjeta -- KpiCardIcono es
              flex-1 (ancho variable) por diseño para la fila angosta de
              55% donde vive en Estados Financieros; acá, aunque el
              contenedor de la página ya se angostó a 72%, sigue siendo
              más ancho que esa fila original, y sin este tope cada
              tarjeta se estira más de lo que su aspect-[4/1] compensa,
              dejando un hueco vacío entre el ícono y el valor. */}
          <div className="flex flex-wrap justify-center gap-2">
            <div className="flex-1" style={{ maxWidth: 320 }}>
              <KpiCardIcono letra="T" color={COLOR_TEAL} label="Total" valor={formatQ(data.kpis.total)} />
            </div>
            <div className="flex-1" style={{ maxWidth: 320 }}>
              <KpiCardIcono letra="C" color={COLOR_AZUL} label="Cancelado" valor={formatQ(data.kpis.cancelado)} />
            </div>
            <div className="flex-1" style={{ maxWidth: 320 }}>
              <KpiCardIcono letra="P" color={COLOR_CORAL} label="Por cobrar" valor={formatQ(data.kpis.por_cobrar)} />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {data.tipos.map((t) => (
              <TablaCuotasTipo key={t.tipo} tipo={t} />
            ))}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <ChartCard
              theme="financiero"
              colorSeleccionHex={COLOR_TEAL}
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
              estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
              title="Recuperación Cuota Asociados"
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
          <LabelList dataKey="valor" position="top" formatter={(v: number) => formatMiles(v)} fontSize={14} fill="rgb(var(--color-ink))" />
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

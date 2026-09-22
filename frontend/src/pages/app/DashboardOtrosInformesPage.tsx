import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Title } from "@tremor/react";
import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  obtenerCuotasAsociados,
  obtenerEjecucionGastosAcumulado,
  obtenerEjecucionGastosMes,
} from "../../api/dashboardOtrosInformes";
import { mensajeError } from "../../api/client";
import { ChartCard } from "../../components/ChartCard";
import { FINANCIERO_SURFACE } from "../../components/TablaGrupoExpandible";
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

// Layout COMPACTO calcado de las proporciones reales del .pbix (lienzo
// 1920x1500, todo el contenido cabe sin scroll) -- ver instrucción del
// usuario. Tipografía/padding reducidos a propósito (text-[11px], py-0.5)
// para que tablas de hasta ~18 filas quepan en la franja de alto que le
// corresponde sin necesitar scroll interno.

/** Tarjeta KPI chica, mismo espíritu que KpiCardIcono pero más angosta y
 * más baja -- KpiCardIcono (aspect-[4/1]) es demasiado grande para el
 * layout compacto de estas 3 páginas. */
function KpiChico({ letra, color, label, valor }: { letra: string; color: string; label: string; valor: string }) {
  return (
    <div className="flex h-11 flex-1 items-stretch overflow-hidden rounded-tremor-default ring-1 ring-line" style={{ backgroundColor: FINANCIERO_SURFACE }}>
      <div className="flex aspect-square h-full shrink-0 items-center justify-center text-sm font-bold text-white" style={{ backgroundColor: color }} aria-hidden="true">
        {letra}
      </div>
      <div className="flex min-w-0 flex-1 flex-col items-end justify-center gap-0 px-2.5 py-1">
        <span className="text-[10px] font-semibold text-white">{label}</span>
        <span className="text-sm font-semibold text-ink">{valor}</span>
      </div>
    </div>
  );
}

// --- Cuotas Asociados ------------------------------------------------------

// Alto FIJO (no derivado del contenido) para que las 3 tablas queden
// EXACTAMENTE parejas entre sí sin importar cuántas filas tenga cada
// Tipo (A=8, B=13, C=18 en 2026) -- calcado de cómo Power BI dibuja un
// visual de tabla: tamaño de lienzo fijo, no "en escalera" según los
// datos. Con text-[11px]/py-0.5, 340px alcanza para las 18 filas de
// Tipo C sin scroll; overflow-y-auto queda como respaldo si algún año
// tuviera más filas todavía, no como mecanismo principal de layout.
const ALTO_TABLA_CUOTAS = 430;

function TablaCuotasTipo({ tipo }: { tipo: TipoCuotaAsociados }) {
  return (
    <div className="flex flex-col overflow-hidden rounded-tremor-default ring-1 ring-line" style={{ height: ALTO_TABLA_CUOTAS }}>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-[11px]">
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

function GraficoCuotaVsCancelado({ data }: { data: CuotasAsociadosResponse }) {
  const filas = [
    { etiqueta: "Cuota del año", valor: data.kpis.total },
    { etiqueta: "Cancelado", valor: data.kpis.cancelado },
  ];
  return (
    // SIN layout="vertical": layout="vertical" en Recharts pone el eje de
    // categoría en Y y las barras ACOSTADAS (horizontal) -- eso era el
    // bug. El default (sin el prop) es columnas PARADAS (verticales),
    // que es lo que pide el .pbix real.
    <ResponsiveContainer width="100%" height={ALTO_VISUAL_CUOTAS}>
      <BarChart data={filas} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
        <XAxis dataKey="etiqueta" fontSize={10} tickLine={false} />
        <YAxis type="number" tickFormatter={(v: number) => formatQ(v)} fontSize={10} width={55} stroke="rgb(var(--color-ink-faint))" />
        <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
        <Bar dataKey="valor" radius={[4, 4, 0, 0]}>
          <Cell fill={COLOR_TEAL} />
          <Cell fill={COLOR_AZUL} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function DonutCuotasPorTipo({ data }: { data: CuotasAsociadosResponse }) {
  const filas = data.tipos.map((t) => ({ nombre: `Tipo ${t.tipo}`, valor: t.total_cuota, color: COLOR_POR_TIPO[t.tipo] }));
  return (
    <ResponsiveContainer width="100%" height={ALTO_VISUAL_CUOTAS}>
      <PieChart>
        <Pie data={filas} dataKey="valor" nameKey="nombre" innerRadius="50%" outerRadius="80%" paddingAngle={2}>
          {filas.map((f) => (
            <Cell key={f.nombre} fill={f.color} />
          ))}
        </Pie>
        <Legend wrapperStyle={{ fontSize: 10 }} />
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
        <Pie data={filas} dataKey="valor" nameKey="nombre" innerRadius="50%" outerRadius="80%" paddingAngle={2}>
          {filas.map((f) => (
            <Cell key={f.nombre} fill={f.color} />
          ))}
        </Pie>
        <Legend wrapperStyle={{ fontSize: 10 }} />
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
        // apiladas), ~27% de ancho cada una, ~34% del alto de la página;
        // las gráficas van debajo, en la misma pantalla, sin scroll.
        <div className="mx-auto space-y-3" style={{ width: "94%" }}>
          <div className="flex flex-wrap justify-center gap-2">
            <KpiChico letra="T" color={COLOR_TEAL} label="Total" valor={formatQ(data.kpis.total)} />
            <KpiChico letra="C" color={COLOR_AZUL} label="Cancelado" valor={formatQ(data.kpis.cancelado)} />
            <KpiChico letra="P" color={COLOR_CORAL} label="Por cobrar" valor={formatQ(data.kpis.por_cobrar)} />
          </div>

          <div className="grid grid-cols-3 gap-3">
            {data.tipos.map((t) => (
              <TablaCuotasTipo key={t.tipo} tipo={t} />
            ))}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <ChartCard
              theme="financiero"
              estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
              title="Cuota del año vs Cancelado"
              chart={<GraficoCuotaVsCancelado data={data} />}
              table={
                <table className="w-full text-xs">
                  <tbody>
                    <tr className="border-b border-line/50">
                      <td className="px-2 py-1 text-ink">Cuota del año</td>
                      <td className="px-2 py-1 text-right text-ink">{formatQ(data.kpis.total)}</td>
                    </tr>
                    <tr>
                      <td className="px-2 py-1 text-ink">Cancelado</td>
                      <td className="px-2 py-1 text-right text-ink">{formatQ(data.kpis.cancelado)}</td>
                    </tr>
                  </tbody>
                </table>
              }
            />
            <ChartCard
              theme="financiero"
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
          <tr style={{ backgroundColor: COLOR_TEAL }}>
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

// Tarjeta KPI de una sola cifra (12 de estas, en 2 filas de 6) -- calcado
// del .pbix real: debajo de la tabla dinámica van 12 tarjetas KPI en 2
// filas, no las 3 tarjetas-con-gráfica-embebida que había antes. Franja
// de color arriba en vez de cuadrito con letra (KpiChico/KpiCardIcono):
// acá el nombre completo del grupo (Administración/Operación/
// Consolidado) ya va en el label, no hace falta una letra aparte.
function KpiMini({ label, valor, color }: { label: string; valor: string; color: string }) {
  return (
    <div className="overflow-hidden rounded-tremor-default ring-1 ring-line" style={{ backgroundColor: FINANCIERO_SURFACE }}>
      <div className="h-1" style={{ backgroundColor: color }} aria-hidden="true" />
      <div className="px-2 py-1.5 text-center">
        <div className="truncate text-[9px] font-semibold text-ink-muted" title={label}>
          {label}
        </div>
        <div className="text-sm font-bold text-ink">{valor}</div>
      </div>
    </div>
  );
}

// Gráfica de columnas verticales Presupuesto vs Ejecutado de un grupo --
// las 3 (Administración/Operación/Consolidado) comparten el mismo alto
// fijo para quedar exactamente del mismo tamaño entre sí (calcado del
// .pbix: 3 gráficas w=480 iguales entre sí).
const ALTO_GRAFICA_GRUPO = 210;

function GraficoColumnasGrupo({ presupuesto, ejecutado, color }: { presupuesto: number; ejecutado: number; color: string }) {
  const filas = [
    { etiqueta: "Presupuesto", valor: presupuesto },
    { etiqueta: "Ejecutado", valor: ejecutado },
  ];
  return (
    <ResponsiveContainer width="100%" height={ALTO_GRAFICA_GRUPO}>
      <BarChart data={filas} margin={{ top: 8, right: 12, bottom: 4, left: 8 }}>
        <XAxis dataKey="etiqueta" fontSize={10} tickLine={false} />
        <YAxis type="number" tickFormatter={(v: number) => formatQ(v)} fontSize={10} width={60} stroke="rgb(var(--color-ink-faint))" />
        <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
        <Bar dataKey="valor" radius={[4, 4, 0, 0]} fill={color} />
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
          {/* Tabla dinámica principal + las 12 tarjetas KPI, centradas al
              58% de ancho (bloque compacto arriba, NO estirado a todo el
              ancho -- calcado del .pbix: w≈1115 de un lienzo de 1920). */}
          <div className="mx-auto space-y-2" style={{ width: "58%" }}>
            <TablaEjecucionGastos data={data} />

            {/* 12 tarjetas KPI en 2 filas de 6 (grid-cols-6 se envuelve
                solo) -- fila 1: Presupuesto y Ejecutado de los 3 grupos;
                fila 2: % de Ejecución y Diferencia de los 3 grupos. Mismos
                3 grupos que ya calcula el backend (Administración/
                Operación/Consolidado, en ese orden fijo), solo se
                muestran como 12 tarjetas de una cifra en vez de 3
                tarjetas con gráfica embebida. */}
            <div className="grid grid-cols-6 gap-2 pt-1">
              <KpiMini label="Presupuesto Admin." valor={formatQ(data.fila_presupuesto.administracion)} color={COLOR_TEAL} />
              <KpiMini label="Presupuesto Oper." valor={formatQ(data.fila_presupuesto.operacion)} color={COLOR_AZUL} />
              <KpiMini label="Presupuesto Consol." valor={formatQ(data.fila_presupuesto.consolidado)} color={COLOR_MARINO} />
              <KpiMini label="Ejecutado Admin." valor={formatQ(data.fila_total_ejecutado.administracion)} color={COLOR_TEAL} />
              <KpiMini label="Ejecutado Oper." valor={formatQ(data.fila_total_ejecutado.operacion)} color={COLOR_AZUL} />
              <KpiMini label="Ejecutado Consol." valor={formatQ(data.fila_total_ejecutado.consolidado)} color={COLOR_MARINO} />
              <KpiMini label="% Ejec. Admin." valor={formatPercent(data.tarjetas[0].porcentaje_ejecucion)} color={COLOR_TEAL} />
              <KpiMini label="% Ejec. Oper." valor={formatPercent(data.tarjetas[1].porcentaje_ejecucion)} color={COLOR_AZUL} />
              <KpiMini label="% Ejec. Consol." valor={formatPercent(data.tarjetas[2].porcentaje_ejecucion)} color={COLOR_MARINO} />
              <KpiMini label="Diferencia Admin." valor={formatQ(data.tarjetas[0].diferencia)} color={COLOR_TEAL} />
              <KpiMini label="Diferencia Oper." valor={formatQ(data.tarjetas[1].diferencia)} color={COLOR_AZUL} />
              <KpiMini label="Diferencia Consol." valor={formatQ(data.tarjetas[2].diferencia)} color={COLOR_MARINO} />
            </div>
          </div>

          {/* Las 3 gráficas de columnas (Administración/Operación/
              Consolidado) van más anchas que la tabla, a propósito --
              calcado del .pbix (w=480 cada una, las 3 iguales entre sí). */}
          <div className="mx-auto grid grid-cols-3 gap-3 pt-2" style={{ width: "90%" }}>
            {data.tarjetas.map((t) => (
              <div key={t.grupo} className="overflow-hidden rounded-tremor-default ring-1 ring-line" style={{ backgroundColor: FINANCIERO_SURFACE }}>
                <div className="px-2 py-1 text-center text-xs font-semibold text-ink">{t.grupo}</div>
                <GraficoColumnasGrupo
                  presupuesto={t.presupuesto}
                  ejecutado={t.ejecutado}
                  color={t.grupo === "Administración" ? COLOR_TEAL : t.grupo === "Operación" ? COLOR_AZUL : COLOR_MARINO}
                />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

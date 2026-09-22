import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Title } from "@tremor/react";
import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { obtenerCuotasAsociados } from "../../api/dashboardOtrosInformes";
import { mensajeError } from "../../api/client";
import { ChartCard } from "../../components/ChartCard";
import { KpiCardIcono, FINANCIERO_SURFACE } from "../../components/TablaGrupoExpandible";
import { formatQ } from "../../utils/format";
import type { CuotasAsociadosResponse, TipoCuotaAsociados } from "../../types/dashboardOtrosInformes";

// Mismos colores de identidad que Estados Financieros (teal/coral/azul,
// ver DashboardFinancieroPage) para que "Otros informes financieros" se
// vea consistente con el resto de Financiero -- acá se le suma un color
// más (marino) para el tercer tipo (C), ya que esta página tiene 3
// categorías (A/B/C) en vez de las 2-3 de Estados Financieros.
const COLOR_TEAL = "#3f6f6b";
const COLOR_CORAL = "#e87471";
const COLOR_AZUL = "#507eaa";
const COLOR_MARINO = "#375b7d";

const COLOR_POR_TIPO: Record<string, string> = { A: COLOR_TEAL, B: COLOR_AZUL, C: COLOR_MARINO };
const ANCHO_TABLA = "55%";

// Todavía no existe un componente compartido para tabla simple (no
// expandible) fuera de Estados Financieros -- ahí también es local a la
// página (ver TablaCategorias en DashboardFinancieroPage.tsx), mismo
// patrón acá: una por Tipo, columnas fijas Nombre/Cuota/Cancelado/Saldo.
function TablaCuotasTipo({ tipo }: { tipo: TipoCuotaAsociados }) {
  return (
    <div className="overflow-hidden rounded-tremor-default ring-1 ring-line">
      <table className="w-full text-sm">
        <thead>
          <tr style={{ backgroundColor: COLOR_POR_TIPO[tipo.tipo] }}>
            <th className="px-3 py-2 text-left font-semibold text-white">{`Tipo ${tipo.tipo}`}</th>
            <th className="px-3 py-2 text-right font-semibold text-white">Cuota</th>
            <th className="px-3 py-2 text-right font-semibold text-white">Cancelado</th>
            <th className="px-3 py-2 text-right font-semibold text-white">Saldo</th>
          </tr>
        </thead>
        <tbody style={{ backgroundColor: FINANCIERO_SURFACE }}>
          {tipo.filas.map((f) => (
            <tr key={f.nombre} className="border-b border-line/50">
              <td className="break-words px-3 py-1.5 text-ink" title={f.nombre}>
                {f.nombre}
              </td>
              <td className="px-3 py-1.5 text-right text-ink">{formatQ(f.cuota)}</td>
              <td className="px-3 py-1.5 text-right text-ink">{formatQ(f.cancelado)}</td>
              <td className="px-3 py-1.5 text-right text-ink">{formatQ(f.saldo)}</td>
            </tr>
          ))}
          <tr className="font-semibold text-ink">
            <td className="px-3 py-2">Total {tipo.tipo}</td>
            <td className="px-3 py-2 text-right">{formatQ(tipo.total_cuota)}</td>
            <td className="px-3 py-2 text-right">{formatQ(tipo.total_cancelado)}</td>
            <td className="px-3 py-2 text-right">{formatQ(tipo.total_saldo)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function GraficoCuotaVsCancelado({ data }: { data: CuotasAsociadosResponse }) {
  const filas = [
    { etiqueta: "Cuota del año", valor: data.kpis.total },
    { etiqueta: "Cancelado", valor: data.kpis.cancelado },
  ];
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
        <XAxis type="number" tickFormatter={(v: number) => formatQ(v)} fontSize={12} stroke="rgb(var(--color-ink-faint))" />
        <YAxis type="category" dataKey="etiqueta" width={110} fontSize={12} tickLine={false} />
        <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
        <Bar dataKey="valor" radius={[0, 4, 4, 0]}>
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
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={filas} dataKey="valor" nameKey="nombre" innerRadius="55%" outerRadius="85%" paddingAngle={2}>
          {filas.map((f) => (
            <Cell key={f.nombre} fill={f.color} />
          ))}
        </Pie>
        <Legend />
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
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={filas} dataKey="valor" nameKey="nombre" innerRadius="55%" outerRadius="85%" paddingAngle={2}>
          {filas.map((f) => (
            <Cell key={f.nombre} fill={f.color} />
          ))}
        </Pie>
        <Legend />
        <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: "rgb(var(--color-bg-surface))", border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

// "Otros informes financieros" -- 5 páginas hermanas de "Estados
// financieros" en el Sidebar (mismo patrón: 1 sola ruta + ?vista=, ver
// DashboardFinancieroPage). Por ahora solo "cuotas-asociados" está
// implementada; las otras 4 quedan con placeholder hasta construirse
// (Sidebar.tsx todavía no les da href a esas 4 a propósito).
const VISTAS = ["cuotas-asociados", "conciliacion-bancaria", "flujo-caja", "gastos-mes", "gastos-acumulado"] as const;

export function DashboardOtrosInformesPage() {
  const [searchParams] = useSearchParams();
  const vistaParam = searchParams.get("vista") ?? "cuotas-asociados";
  const vista = VISTAS.includes(vistaParam as (typeof VISTAS)[number])
    ? (vistaParam as (typeof VISTAS)[number])
    : "cuotas-asociados";

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
    <div className="space-y-5">
      <div className="relative flex min-h-[64px] items-center justify-center">
        <Title className="px-4 text-center text-3xl text-ink">{`Cuotas Asociados ${data?.anio ?? ""}`}</Title>
        <div className="absolute right-0 top-full mt-5">
          <label className="block">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-ink-muted">Año</span>
            <select
              value={anio}
              onChange={(e) => setAnio(e.target.value)}
              className="rounded-tremor-default border border-line bg-surface px-3 py-1.5 text-sm text-ink"
            >
              {aniosDisponibles.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          <div className="mx-auto space-y-5" style={{ width: ANCHO_TABLA }}>
            <div className="flex flex-wrap justify-center gap-3">
              <KpiCardIcono letra="T" color={COLOR_TEAL} label="Total" valor={formatQ(data.kpis.total)} />
              <KpiCardIcono letra="C" color={COLOR_AZUL} label="Cancelado" valor={formatQ(data.kpis.cancelado)} />
              <KpiCardIcono letra="P" color={COLOR_CORAL} label="Por cobrar" valor={formatQ(data.kpis.por_cobrar)} />
            </div>

            {data.tipos.map((t) => (
              <TablaCuotasTipo key={t.tipo} tipo={t} />
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <ChartCard
              theme="financiero"
              estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
              title="Cuota del año vs Cancelado"
              chart={<GraficoCuotaVsCancelado data={data} />}
              table={
                <table className="w-full text-sm">
                  <tbody>
                    <tr className="border-b border-line/50">
                      <td className="px-2 py-1.5 text-ink">Cuota del año</td>
                      <td className="px-2 py-1.5 text-right text-ink">{formatQ(data.kpis.total)}</td>
                    </tr>
                    <tr>
                      <td className="px-2 py-1.5 text-ink">Cancelado</td>
                      <td className="px-2 py-1.5 text-right text-ink">{formatQ(data.kpis.cancelado)}</td>
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
                <table className="w-full text-sm">
                  <tbody>
                    {data.tipos.map((t) => (
                      <tr key={t.tipo} className="border-b border-line/50">
                        <td className="px-2 py-1.5 text-ink">{`Tipo ${t.tipo}`}</td>
                        <td className="px-2 py-1.5 text-right text-ink">{formatQ(t.total_cuota)}</td>
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
                <table className="w-full text-sm">
                  <tbody>
                    <tr className="border-b border-line/50">
                      <td className="px-2 py-1.5 text-ink">Cancelado</td>
                      <td className="px-2 py-1.5 text-right text-ink">{formatQ(data.kpis.cancelado)}</td>
                    </tr>
                    <tr>
                      <td className="px-2 py-1.5 text-ink">Por cobrar</td>
                      <td className="px-2 py-1.5 text-right text-ink">{formatQ(data.kpis.por_cobrar)}</td>
                    </tr>
                  </tbody>
                </table>
              }
            />
          </div>
        </>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { Title, Text } from "@tremor/react";
import { obtenerDashboardFinanciero } from "../../api/dashboardFinanciero";
import { mensajeError } from "../../api/client";
import { FilterYearMonth } from "../../components/filters/PowerBiFilter";
import { KpiCard } from "../../components/KpiCard";
import { ChartCard } from "../../components/ChartCard";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import { SimpleGroupBarChart } from "../../components/charts/SimpleGroupBarChart";
import { BalanceDonut } from "../../components/charts/BalanceDonut";
import { formatPercent, formatQAbrev, MESES_LARGOS } from "../../utils/format";
import { dashboardAccent } from "../../theme/colors";
import type {
  DashboardFinancieroResponse,
  DetalleCuentaBalance,
  DetalleCuentaBalanceComparativo,
  DetalleCuentaComparativoMovimiento,
  DetalleCuentaMovimiento,
} from "../../types/dashboardFinanciero";

const ACCENT = dashboardAccent.financiero;

function TablaMovimiento({ filas, etiquetaColumna }: { filas: DetalleCuentaMovimiento[]; etiquetaColumna: string }) {
  return (
    <SimpleDataTable
      sinLimiteAltura
      compacto="px-1 py-1 text-xs"
      columnas={[
        { header: "Grupo", accessor: (r: DetalleCuentaMovimiento) => r.grupo ?? "SIN CLASIFICAR" },
        { header: "Cuenta (N5)", accessor: (r: DetalleCuentaMovimiento) => r.nombre_cuenta_n5 ?? "—" },
        { header: `Mes anterior (${etiquetaColumna})`, accessor: (r) => formatQAbrev(r.mes_anterior), align: "right" },
        { header: "Saldo acumulado", accessor: (r) => formatQAbrev(r.saldo_acumulado), align: "right" },
      ]}
      filas={filas}
      getKey={(r, i) => `${r.nombre_cuenta_n5}-${i}`}
    />
  );
}

function TablaComparativoMovimiento({ filas }: { filas: DetalleCuentaComparativoMovimiento[] }) {
  return (
    <SimpleDataTable
      sinLimiteAltura
      compacto="px-1 py-1 text-xs"
      columnas={[
        { header: "Cuenta", accessor: (r: DetalleCuentaComparativoMovimiento) => r.cuenta ?? "—" },
        { header: "Grupo", accessor: (r) => r.grupo ?? "SIN CLASIFICAR" },
        { header: "Año anterior", accessor: (r) => formatQAbrev(r.monto_anio_anterior), align: "right" },
        { header: "Variación", accessor: (r) => formatQAbrev(r.variacion), align: "right" },
        { header: "Año actual", accessor: (r) => formatQAbrev(r.monto_anio_actual), align: "right" },
      ]}
      filas={filas}
      getKey={(r, i) => `${r.cuenta}-${i}`}
    />
  );
}

function TablaBalance({ filas }: { filas: DetalleCuentaBalance[] }) {
  return (
    <SimpleDataTable
      sinLimiteAltura
      compacto="px-1 py-1 text-xs"
      columnas={[
        { header: "Cuenta (N5)", accessor: (r: DetalleCuentaBalance) => r.nombre_n5 ?? "—" },
        { header: "Grupo", accessor: (r) => r.grupo ?? "SIN CLASIFICAR" },
        { header: "Saldo mes anterior", accessor: (r) => formatQAbrev(r.saldo_mes_anterior), align: "right" },
        { header: "Saldo acumulado actual", accessor: (r) => formatQAbrev(r.saldo_acumulado_actual), align: "right" },
        { header: "Variación", accessor: (r) => formatQAbrev(r.variacion), align: "right" },
      ]}
      filas={filas}
      getKey={(r, i) => `${r.nombre_n5}-${i}`}
    />
  );
}

function TablaBalanceComparativo({ filas }: { filas: DetalleCuentaBalanceComparativo[] }) {
  return (
    <SimpleDataTable
      sinLimiteAltura
      compacto="px-1 py-1 text-xs"
      columnas={[
        { header: "Cuenta (N5)", accessor: (r: DetalleCuentaBalanceComparativo) => r.nombre_n5 ?? "—" },
        { header: "Grupo", accessor: (r) => r.grupo ?? "SIN CLASIFICAR" },
        { header: "Saldo acumulado actual", accessor: (r) => formatQAbrev(r.saldo_acumulado_actual), align: "right" },
        { header: "Saldo acumulado anterior", accessor: (r) => formatQAbrev(r.saldo_acumulado_anterior), align: "right" },
        { header: "Variación", accessor: (r) => formatQAbrev(r.variacion), align: "right" },
      ]}
      filas={filas}
      getKey={(r, i) => `${r.nombre_n5}-${i}`}
    />
  );
}

const PAGINAS = [
  "Ingresos y desembolsos mensual",
  "Ingresos y desembolsos acumulado",
  "Balance general mensual",
  "Balance general comparativo",
] as const;

export function DashboardFinancieroPage() {
  const [anio, setAnio] = useState("");
  const [mes, setMes] = useState("");
  const [data, setData] = useState<DashboardFinancieroResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pagina, setPagina] = useState(0);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerDashboardFinanciero(anio ? Number(anio) : undefined, mes ? Number(mes) : undefined)
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

  const anioOpciones = data
    ? Array.from({ length: 5 }, (_, i) => String(data.anio - 4 + i))
    : [];
  const mesOpciones = MESES_LARGOS.map((nombre, i) => ({ value: String(i + 1), label: nombre }));

  return (
    <div className="space-y-6">
      <div>
        <Title className="text-ink">Estados Financieros</Title>
        {data && (
          <Text className="text-ink-muted">
            {MESES_LARGOS[data.mes - 1]} {data.anio}
          </Text>
        )}
      </div>

      <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-6">
          <FilterYearMonth
            theme="blue"
            anio={anio}
            mes={mes}
            onChangeAnio={setAnio}
            onChangeMes={setMes}
            aniosOpciones={anioOpciones}
            mesesOpciones={mesOpciones}
          />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <div>
          <div role="tablist" className="flex flex-wrap gap-1 border-b border-line">
            {PAGINAS.map((nombre, i) => (
              <button
                key={nombre}
                type="button"
                role="tab"
                aria-selected={pagina === i}
                onClick={() => setPagina(i)}
                className={`rounded-t-tremor-small px-3 py-2 text-sm font-medium transition-colors ${
                  pagina === i
                    ? "border-b-2 border-blue-500 text-blue-500"
                    : "text-ink-muted hover:text-ink"
                }`}
              >
                {nombre}
              </button>
            ))}
          </div>

          {/* --- Página 1 --- */}
          {pagina === 0 && (
            <div className="space-y-6 pt-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <KpiCard label="Ingresos" value={formatQAbrev(data.ingresos_desembolsos_mensual.kpis.ingresos)} accentColor={ACCENT.tremor} />
                <KpiCard label="Egresos" value={formatQAbrev(data.ingresos_desembolsos_mensual.kpis.egresos)} accentColor={ACCENT.tremor} />
                <KpiCard label="Resultado" value={formatQAbrev(data.ingresos_desembolsos_mensual.kpis.resultado)} accentColor={ACCENT.tremor} />
                <KpiCard label="Saldo mes corriente" value={formatQAbrev(data.ingresos_desembolsos_mensual.kpis.saldo_mes_corriente)} accentColor={ACCENT.tremor} />
                <KpiCard label="Acumulado saldo mes corriente" value={formatQAbrev(data.ingresos_desembolsos_mensual.kpis.acumulado_saldo_mes_corriente)} accentColor={ACCENT.tremor} />
                <KpiCard label="Saldo mes anterior" value={formatQAbrev(data.ingresos_desembolsos_mensual.kpis.saldo_mes_anterior)} accentColor={ACCENT.tremor} />
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ChartCard
                  theme="financiero"
                  title="Ingresos por grupo de cuenta"
                  chart={<SimpleGroupBarChart data={data.ingresos_desembolsos_mensual.cascada_ingresos_por_grupo} color="#3b82f6" />}
                  table={<SimpleDataTable sinLimiteAltura columnas={[{ header: "Grupo", accessor: (r: any) => r.grupo }, { header: "Monto", accessor: (r: any) => formatQAbrev(r.monto), align: "right" }]} filas={data.ingresos_desembolsos_mensual.cascada_ingresos_por_grupo} getKey={(r: any) => r.grupo} />}
                />
                <ChartCard
                  theme="financiero"
                  title="Egresos por grupo de cuenta"
                  chart={<SimpleGroupBarChart data={data.ingresos_desembolsos_mensual.cascada_egresos_por_grupo} color="#f97316" />}
                  table={<SimpleDataTable sinLimiteAltura columnas={[{ header: "Grupo", accessor: (r: any) => r.grupo }, { header: "Monto", accessor: (r: any) => formatQAbrev(r.monto), align: "right" }]} filas={data.ingresos_desembolsos_mensual.cascada_egresos_por_grupo} getKey={(r: any) => r.grupo} />}
                />
              </div>

              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Egresos por grupo</Title>
                <TablaMovimiento filas={data.ingresos_desembolsos_mensual.detalle_egresos} etiquetaColumna="débitos" />
              </div>
              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Ingresos por grupo</Title>
                <TablaMovimiento filas={data.ingresos_desembolsos_mensual.detalle_ingresos} etiquetaColumna="créditos" />
              </div>
            </div>
          )}

          {/* --- Página 2 --- */}
          {pagina === 1 && (
            <div className="space-y-6 pt-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard label="Ingresos" value={formatQAbrev(data.ingresos_desembolsos_acumulado.kpis.ingresos)} accentColor={ACCENT.tremor} />
                <KpiCard label="Egresos" value={formatQAbrev(data.ingresos_desembolsos_acumulado.kpis.egresos)} accentColor={ACCENT.tremor} />
                <KpiCard label="Saldo acumulado" value={formatQAbrev(data.ingresos_desembolsos_acumulado.kpis.saldo_acumulado)} accentColor={ACCENT.tremor} />
                <KpiCard label="Resultado año actual" value={formatQAbrev(data.ingresos_desembolsos_acumulado.kpis.resultado_anio_actual)} accentColor={ACCENT.tremor} />
                <KpiCard label="Variación resultado" value={formatQAbrev(data.ingresos_desembolsos_acumulado.kpis.variacion_resultado)} accentColor={ACCENT.tremor} />
                <KpiCard label="ER año anterior" value={formatQAbrev(data.ingresos_desembolsos_acumulado.kpis.er_anio_anterior)} accentColor={ACCENT.tremor} />
                <KpiCard label="ER año actual" value={formatQAbrev(data.ingresos_desembolsos_acumulado.kpis.er_anio_actual)} accentColor={ACCENT.tremor} />
                <KpiCard label="ER mensual" value={formatQAbrev(data.ingresos_desembolsos_acumulado.kpis.er_mensual)} accentColor={ACCENT.tremor} />
                <KpiCard label="Acumulado saldo año anterior" value={formatQAbrev(data.ingresos_desembolsos_acumulado.kpis.acumulado_saldo_anio_anterior)} accentColor={ACCENT.tremor} />
              </div>

              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Egresos por grupo</Title>
                <TablaComparativoMovimiento filas={data.ingresos_desembolsos_acumulado.detalle_egresos} />
              </div>
              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Ingresos por grupo</Title>
                <TablaComparativoMovimiento filas={data.ingresos_desembolsos_acumulado.detalle_ingresos} />
              </div>
            </div>
          )}

          {/* --- Página 3 --- */}
          {pagina === 2 && (
            <div className="space-y-6 pt-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard label="Activo" value={formatQAbrev(data.balance_general_mensual.kpis.activo)} accentColor={ACCENT.tremor} />
                <KpiCard label="Pasivo" value={formatQAbrev(data.balance_general_mensual.kpis.pasivo)} accentColor={ACCENT.tremor} />
                <KpiCard label="Patrimonio" value={formatQAbrev(data.balance_general_mensual.kpis.patrimonio)} accentColor={ACCENT.tremor} />
                <KpiCard label="Balance mensual" value={formatQAbrev(data.balance_general_mensual.kpis.balance_mensual)} accentColor={ACCENT.tremor} />
                <KpiCard label="% Activo" value={formatPercent(data.balance_general_mensual.kpis.porcentaje_activo)} accentColor={ACCENT.tremor} />
                <KpiCard label="% Pasivo" value={formatPercent(data.balance_general_mensual.kpis.porcentaje_pasivo)} accentColor={ACCENT.tremor} />
                <KpiCard label="% Patrimonio" value={formatPercent(data.balance_general_mensual.kpis.porcentaje_patrimonio)} accentColor={ACCENT.tremor} />
                <KpiCard label="% Fondos por aplicar" value={formatPercent(data.balance_general_mensual.kpis.porcentaje_fondos_por_aplicar)} accentColor={ACCENT.tremor} />
              </div>

              <ChartCard
                theme="financiero"
                title="Distribución del balance"
                subtitle="Activo / Pasivo / Patrimonio / Fondos por aplicar"
                chart={<BalanceDonut data={data.balance_general_mensual.distribucion_balance} />}
                table={
                  <SimpleDataTable
                    sinLimiteAltura
                    columnas={[
                      { header: "Categoría", accessor: (r: any) => r.etiqueta },
                      { header: "Monto", accessor: (r: any) => formatQAbrev(r.monto), align: "right" },
                    ]}
                    filas={data.balance_general_mensual.distribucion_balance}
                    getKey={(r: any) => r.etiqueta}
                  />
                }
              />

              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Activo</Title>
                <TablaBalance filas={data.balance_general_mensual.detalle_activo} />
              </div>
              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Pasivo</Title>
                <TablaBalance filas={data.balance_general_mensual.detalle_pasivo} />
              </div>
              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Patrimonio</Title>
                <TablaBalance filas={data.balance_general_mensual.detalle_patrimonio} />
              </div>
            </div>
          )}

          {/* --- Página 4 --- */}
          {pagina === 3 && (
            <div className="space-y-6 pt-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard label="Diferencia % Activo" value={formatPercent(data.balance_general_comparativo.kpis.diferencia_porcentaje_activo)} accentColor={ACCENT.tremor} />
                <KpiCard label="Variación (Q) Activo" value={formatQAbrev(data.balance_general_comparativo.kpis.variacion_q_activo)} accentColor={ACCENT.tremor} />
                <KpiCard label="Diferencia % Pasivo" value={formatPercent(data.balance_general_comparativo.kpis.diferencia_porcentaje_pasivo)} accentColor={ACCENT.tremor} />
                <KpiCard label="Variación (Q) Pasivo" value={formatQAbrev(data.balance_general_comparativo.kpis.variacion_q_pasivo)} accentColor={ACCENT.tremor} />
                <KpiCard label="Diferencia % Patrimonio" value={formatPercent(data.balance_general_comparativo.kpis.diferencia_porcentaje_patrimonio)} accentColor={ACCENT.tremor} />
                <KpiCard label="Variación (Q) Patrimonio" value={formatQAbrev(data.balance_general_comparativo.kpis.variacion_q_patrimonio)} accentColor={ACCENT.tremor} />
                <KpiCard label="Total acumulado anterior" value={formatQAbrev(data.balance_general_comparativo.kpis.total_acumulado_anterior)} accentColor={ACCENT.tremor} />
                <KpiCard label="Total acumulado actual" value={formatQAbrev(data.balance_general_comparativo.kpis.total_acumulado_actual)} accentColor={ACCENT.tremor} />
                <KpiCard label="Total variación" value={formatQAbrev(data.balance_general_comparativo.kpis.total_variacion)} accentColor={ACCENT.tremor} />
                <KpiCard label="Balance acumulado" value={formatQAbrev(data.balance_general_comparativo.kpis.balance_acumulado)} accentColor={ACCENT.tremor} />
              </div>

              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Activo</Title>
                <TablaBalanceComparativo filas={data.balance_general_comparativo.detalle_activo} />
              </div>
              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Pasivo</Title>
                <TablaBalanceComparativo filas={data.balance_general_comparativo.detalle_pasivo} />
              </div>
              <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
                <Title className="mb-3 text-ink">Detalle de Patrimonio</Title>
                <TablaBalanceComparativo filas={data.balance_general_comparativo.detalle_patrimonio} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

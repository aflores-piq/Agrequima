import { useEffect, useState } from "react";
import { ProgressBar, Title, Text } from "@tremor/react";
import { obtenerDashboardNutrientes, obtenerOpcionesNutrientes } from "../../api/dashboard";
import { mensajeError } from "../../api/client";
import { FilterMultiCombobox, FilterYearMonth } from "../../components/filters/PowerBiFilter";
import { KpiCard } from "../../components/KpiCard";
import { ChartCard } from "../../components/ChartCard";
import { BotonExportarExcel } from "../../components/BotonExportarExcel";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import { ScrollDataTable } from "../../components/ScrollDataTable";
import { RankingTable } from "../../components/RankingTable";
import { ComparativeBarChart } from "../../components/charts/ComparativeBarChart";
import { MultiAnnualLineChart } from "../../components/charts/MultiAnnualLineChart";
import { RankingBarChart } from "../../components/charts/RankingBarChart";
import { formatNumber, formatQAbrev, formatUSDAbrev, MESES, MESES_LARGOS } from "../../utils/format";
import { dashboardAccent } from "../../theme/colors";
import type {
  DashboardNutrientesResponse,
  DetalleLicenciaNutriente,
  OpcionesFiltroNutrientes,
} from "../../types/dashboard";

const ACCENT = dashboardAccent.nutrientes;
const TAMANO_BLOQUE_DETALLE = 50;

export function DashboardNutrientesPage() {
  const [opciones, setOpciones] = useState<OpcionesFiltroNutrientes | null>(null);

  const [anio, setAnio] = useState("");
  const [mes, setMes] = useState("");
  const [origen, setOrigen] = useState<string[]>([]);
  const [nombreComercial, setNombreComercial] = useState<string[]>([]);
  const [nombreComercialRaw, setNombreComercialRaw] = useState<string[]>([]);
  const [componente, setComponente] = useState<string[]>([]);

  const [data, setData] = useState<DashboardNutrientesResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filasDetalle, setFilasDetalle] = useState<DetalleLicenciaNutriente[]>([]);
  const [bloqueDetalle, setBloqueDetalle] = useState(1);
  const [cargandoMasFilas, setCargandoMasFilas] = useState(false);

  useEffect(() => {
    obtenerOpcionesNutrientes().then(setOpciones).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerDashboardNutrientes({
      anio: anio ? Number(anio) : undefined,
      mes: mes ? Number(mes) : undefined,
      origen,
      nombreComercial,
      nombreComercialRaw,
      componente,
      pagina: 1,
      tamanoPagina: TAMANO_BLOQUE_DETALLE,
    })
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        setFilasDetalle(res.detalle.filas);
        setBloqueDetalle(1);
        if (!anio) setAnio(String(res.anio_actual));
        if (!mes) setMes(String(res.mes_seleccionado));
        // Si al cambiar de año el mes ya elegido queda fuera del rango
        // con datos del nuevo año, lo ajustamos al último disponible.
        else if (Number(mes) > res.mes_maximo) setMes(String(res.mes_maximo));
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
  }, [anio, mes, origen, nombreComercial, nombreComercialRaw, componente]);

  function cargarMasFilasDetalle() {
    setCargandoMasFilas(true);
    const siguienteBloque = bloqueDetalle + 1;
    obtenerDashboardNutrientes({
      anio: anio ? Number(anio) : undefined,
      mes: mes ? Number(mes) : undefined,
      origen,
      nombreComercial,
      nombreComercialRaw,
      componente,
      pagina: siguienteBloque,
      tamanoPagina: TAMANO_BLOQUE_DETALLE,
    })
      .then((res) => {
        setFilasDetalle((prev) => [...prev, ...res.detalle.filas]);
        setBloqueDetalle(siguienteBloque);
      })
      .catch(() => {})
      .finally(() => setCargandoMasFilas(false));
  }

  function limpiarFiltros() {
    setOrigen([]);
    setNombreComercial([]);
    setNombreComercialRaw([]);
    setComponente([]);
  }

  if (error) {
    return <p className="rounded-tremor-small bg-danger-surface px-4 py-3 text-sm text-danger">{error}</p>;
  }

  const anioActual = data?.anio_actual;
  const anioAnterior = data?.anio_anterior;

  const filtrosExport = {
    anio: anio ? Number(anio) : undefined,
    mes: mes ? Number(mes) : undefined,
    nombre_comercial: nombreComercial.length ? nombreComercial : undefined,
    nombre_comercial_raw: nombreComercialRaw.length ? nombreComercialRaw : undefined,
    origen: origen.length ? origen : undefined,
    componente: componente.length ? componente : undefined,
  };
  const sufijoArchivo = `${anioActual ?? ""}`;

  const dataComparacionAcumulada =
    data?.comparacion_acumulada_mensual.map((m) => ({
      mes: MESES[m.mes - 1],
      [`${anioActual}`]: m.cif_usd_actual_acumulado,
      [`${anioAnterior}`]: m.cif_usd_anterior_acumulado,
    })) ?? [];

  const dataComparacionMensual =
    data?.comparacion_mensual.map((m) => ({
      mes: MESES[m.mes - 1],
      [`${anioActual}`]: m.cif_usd_actual,
      [`${anioAnterior}`]: m.cif_usd_anterior,
    })) ?? [];

  const serieMultianual = data?.comparativo_acumulado_multianual ?? [];
  const dataComparacionMultianual = (serieMultianual[0]?.puntos ?? []).map((_, i) => {
    const fila: Record<string, string | number> = { mes: MESES[i] };
    for (const serie of serieMultianual) {
      fila[String(serie.anio)] = serie.puntos[i]?.cif_usd_acumulado ?? 0;
    }
    return fila;
  });

  return (
    <div className="space-y-6">
      <div>
        <Title className="text-ink">Dashboard de Nutrientes</Title>
        {data && (
          <Text className="text-ink-muted">
            {anioActual} + {MESES_LARGOS[data.mes_seleccionado - 1]} · Comparado contra {anioAnterior}
          </Text>
        )}
      </div>

      <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          <FilterYearMonth
            anio={anio}
            mes={mes}
            onChangeAnio={setAnio}
            onChangeMes={setMes}
            aniosOpciones={(opciones?.anios ?? []).map((a) => String(a))}
            mesesOpciones={MESES_LARGOS.slice(0, data?.mes_maximo ?? 12).map((nombre, i) => ({
              value: String(i + 1),
              label: nombre,
            }))}
            theme="orange"
          />
          <FilterMultiCombobox
            label="Componente"
            values={componente}
            onChange={setComponente}
            options={opciones?.componentes ?? []}
            theme="orange"
          />
          <FilterMultiCombobox
            label="Nombre comercial (agrupado)"
            values={nombreComercial}
            onChange={setNombreComercial}
            options={opciones?.nombres_comerciales ?? []}
            theme="orange"
          />
          <FilterMultiCombobox
            label="Nombre comercial"
            values={nombreComercialRaw}
            onChange={setNombreComercialRaw}
            options={opciones?.nombres_comerciales_raw ?? []}
            theme="orange"
          />
          <FilterMultiCombobox
            label="País de origen"
            values={origen}
            onChange={setOrigen}
            options={opciones?.paises_origen ?? []}
            theme="orange"
          />
        </div>
        <div className="mt-3 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={limpiarFiltros}
            className="text-xs font-medium text-ink-muted hover:text-ink"
          >
            Limpiar filtros
          </button>
          <BotonExportarExcel
            theme="nutrientes"
            endpoint="/dashboard/nutrientes/export-todo"
            filtros={filtrosExport}
            nombreArchivoPorDefecto={`nutrientes_completo_${sufijoArchivo}.xlsx`}
            etiqueta="Exportar todo"
          />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Total CIF USD" value={formatUSDAbrev(data.kpis.cif_total_usd)} accentColor={ACCENT.tremor} />
            <KpiCard label="Total CIF Quetzales" value={formatQAbrev(data.kpis.cif_total_q)} accentColor={ACCENT.tremor} />
            <KpiCard label="Registros" value={formatNumber(data.kpis.registros)} accentColor={ACCENT.tremor} />
            <KpiCard label="Empresas" value={formatNumber(data.kpis.empresas)} accentColor={ACCENT.tremor} />
          </div>

          <ChartCard
            theme="nutrientes"
            title="Comparativo acumulado de CIF USD por mes"
            subtitle={`${anioActual} vs. ${anioAnterior}, hasta ${MESES_LARGOS[data.mes_seleccionado - 1]}`}
            exportar={
              <BotonExportarExcel
                theme="nutrientes"
                endpoint="/dashboard/nutrientes/export/acumulado-mensual"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`nutrientes_acumulado_mensual_${sufijoArchivo}.xlsx`}
              />
            }
            chart={
              <ComparativeBarChart
                data={dataComparacionAcumulada}
                index="mes"
                categories={[`${anioAnterior}`, `${anioActual}`]}
                colors={["slate", ACCENT.tremor]}
              />
            }
            table={
              <SimpleDataTable
                sinLimiteAltura
                columnas={[
                  { header: "Mes", accessor: (r: any) => r.mes },
                  { header: `CIF USD ${anioActual}`, accessor: (r: any) => formatUSDAbrev(r[`${anioActual}`]), align: "right" },
                  { header: `CIF USD ${anioAnterior}`, accessor: (r: any) => formatUSDAbrev(r[`${anioAnterior}`]), align: "right" },
                ]}
                filas={dataComparacionAcumulada}
                getKey={(r: any) => r.mes}
              />
            }
          />

          <ChartCard
            theme="nutrientes"
            title="Comparación mensual de CIF"
            subtitle={`${anioActual} vs. ${anioAnterior}, hasta ${MESES_LARGOS[data.mes_seleccionado - 1]}`}
            exportar={
              <BotonExportarExcel
                theme="nutrientes"
                endpoint="/dashboard/nutrientes/export/comparativo-mensual"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`nutrientes_comparativo_mensual_${sufijoArchivo}.xlsx`}
              />
            }
            chart={
              <ComparativeBarChart
                data={dataComparacionMensual}
                index="mes"
                categories={[`${anioAnterior}`, `${anioActual}`]}
                colors={["slate", ACCENT.tremor]}
              />
            }
            table={
              <SimpleDataTable
                sinLimiteAltura
                columnas={[
                  { header: "Mes", accessor: (r: any) => r.mes },
                  { header: `CIF USD ${anioActual}`, accessor: (r: any) => formatUSDAbrev(r[`${anioActual}`]), align: "right" },
                  { header: `CIF USD ${anioAnterior}`, accessor: (r: any) => formatUSDAbrev(r[`${anioAnterior}`]), align: "right" },
                ]}
                filas={dataComparacionMensual}
                getKey={(r: any) => r.mes}
              />
            }
          />

          <ChartCard
            theme="nutrientes"
            title="Comparativo acumulado de CIF USD por año"
            subtitle={`Últimos ${serieMultianual.length} año(s) con datos, hasta ${MESES_LARGOS[data.mes_seleccionado - 1]}`}
            exportar={
              <BotonExportarExcel
                theme="nutrientes"
                endpoint="/dashboard/nutrientes/export/acumulado-multianual"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`nutrientes_acumulado_multianual_${sufijoArchivo}.xlsx`}
              />
            }
            chart={<MultiAnnualLineChart theme="nutrientes" series={serieMultianual} />}
            table={
              <SimpleDataTable
                sinLimiteAltura
                columnas={[
                  { header: "Mes", accessor: (r: any) => r.mes },
                  ...serieMultianual.map((serie) => ({
                    header: `CIF USD ${serie.anio}`,
                    accessor: (r: any) => formatUSDAbrev(r[`${serie.anio}`]),
                    align: "right" as const,
                  })),
                ]}
                filas={dataComparacionMultianual}
                getKey={(r: any) => r.mes}
              />
            }
          />

          <ChartCard
            theme="nutrientes"
            title={`Top ${data.top_formulas.length} fórmulas químicas`}
            subtitle="Por CIF USD"
            exportar={
              <BotonExportarExcel
                theme="nutrientes"
                endpoint="/dashboard/nutrientes/export/top-formulas"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`nutrientes_top_formulas_${sufijoArchivo}.xlsx`}
              />
            }
            chart={<RankingBarChart theme="nutrientes" data={data.top_formulas} />}
            table={
              <SimpleDataTable
                sinLimiteAltura
                compacto="px-1 py-1 text-xs"
                columnas={[
                  { header: "Fórmula", accessor: (r) => r.etiqueta },
                  { header: "CIF USD", accessor: (r) => formatUSDAbrev(r.cif_usd), align: "right" },
                ]}
                filas={data.top_formulas}
                getKey={(r) => r.etiqueta}
              />
            }
          />

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
              <Title className="mb-3 text-ink">{`Top ${data.top_paises_origen.length} países de origen`}</Title>
              <RankingTable filas={data.top_paises_origen} etiquetaColumna="País" etiquetaConteo="Licencias" />
            </div>

            <ChartCard
              theme="nutrientes"
              title={`Top ${data.top_aduanas.length} aduanas de ingreso`}
              subtitle="Por CIF USD"
              exportar={
                <BotonExportarExcel
                  theme="nutrientes"
                  endpoint="/dashboard/nutrientes/export/top-aduanas"
                  filtros={filtrosExport}
                  nombreArchivoPorDefecto={`nutrientes_top_aduanas_${sufijoArchivo}.xlsx`}
                />
              }
              chart={<RankingBarChart theme="nutrientes" data={data.top_aduanas} />}
              table={
                <SimpleDataTable
                  sinLimiteAltura
                  compacto="px-1 py-1 text-xs"
                  columnas={[
                    { header: "Aduana", accessor: (r) => r.etiqueta },
                    { header: "CIF USD", accessor: (r) => formatUSDAbrev(r.cif_usd), align: "right" },
                  ]}
                  filas={data.top_aduanas}
                  getKey={(r) => r.etiqueta}
                />
              }
            />
          </div>

          <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
            <div className="mb-3 flex items-center justify-between gap-3">
              <Title className="text-ink">Fórmulas/Componentes ordenado por CIF USD</Title>
              <BotonExportarExcel
                theme="nutrientes"
                endpoint="/dashboard/nutrientes/export/formulas-componentes"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`nutrientes_formulas_componentes_${sufijoArchivo}.xlsx`}
              />
            </div>
            <SimpleDataTable
              sinLimiteAltura
              compacto
              columnas={[
                { header: "#", accessor: (_r, i = 0) => i + 1, align: "right" },
                { header: "Fórmula/Componente", accessor: (r) => r.componente, ancho: "max-w-[170px]" },
                {
                  header: "Proporción",
                  accessor: (r) => (
                    <div className="flex items-center gap-2">
                      <ProgressBar value={r.porcentaje_del_total} color={ACCENT.tremor} className="w-24" />
                      <span className="w-12 text-xs text-ink-muted">{r.porcentaje_del_total.toFixed(1)}%</span>
                    </div>
                  ),
                },
                {
                  header: "Concentración principal",
                  accessor: (r) => r.concentracion_principal ?? "SIN INFORMACIÓN",
                  ancho: "max-w-[200px]",
                },
                { header: "Cantidad", accessor: (r) => formatNumber(r.cantidad), align: "right" },
                { header: "Unidad", accessor: (r) => r.unidad ?? "SIN INFORMACIÓN", ancho: "max-w-[100px]" },
                { header: "CIF USD", accessor: (r) => formatUSDAbrev(r.cif_usd), align: "right" },
                { header: "CIF Q", accessor: (r) => formatQAbrev(r.cif_q), align: "right" },
              ]}
              filas={data.tabla_formulas_componentes.slice(0, 10)}
              getKey={(r) => r.componente}
            />
            <p className="mt-2 text-xs text-ink-faint">Mostrando las 10 fórmulas o componentes con mayor CIF USD.</p>
          </div>

          <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
            <div className="mb-3 flex items-center justify-between gap-3">
              <Title className="text-ink">Detalle de licencias</Title>
              <BotonExportarExcel
                theme="nutrientes"
                endpoint="/dashboard/nutrientes/export/detalle"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`nutrientes_detalle_${sufijoArchivo}.xlsx`}
              />
            </div>
            <ScrollDataTable
              columnas={[
                { header: "Aduana", accessor: (r) => r.aduana ?? "—" },
                { header: "No. licencia", accessor: (r) => r.no_licencia ?? "—" },
                { header: "No. registro", accessor: (r) => r.no_registro ?? "—" },
                { header: "Nombre comercial", accessor: (r) => r.nombre_comercial ?? "—" },
                { header: "Empresa importadora", accessor: (r) => r.empresa_importadora ?? "—" },
                { header: "Fecha de emisión", accessor: (r) => r.fecha_emision ?? "—" },
                { header: "Unidad", accessor: (r) => r.unidad ?? "—" },
              ]}
              filas={filasDetalle}
              total={data.detalle.total}
              cargandoMas={cargandoMasFilas}
              hayMas={filasDetalle.length < data.detalle.total}
              onCargarMas={cargarMasFilasDetalle}
              getKey={(r, i) => `${r.no_licencia}-${i}`}
            />
          </div>
        </>
      )}
    </div>
  );
}

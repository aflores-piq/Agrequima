import { useEffect, useState } from "react";
import { Title, Text } from "@tremor/react";
import { obtenerDashboardPlaguicidas, obtenerOpcionesPlaguicidas } from "../../api/dashboard";
import { mensajeError } from "../../api/client";
import { FilterMultiCombobox, FilterYearMonth } from "../../components/filters/PowerBiFilter";
import { KpiCard } from "../../components/KpiCard";
import { ChartCard } from "../../components/ChartCard";
import { BotonExportarExcel } from "../../components/BotonExportarExcel";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import { ScrollDataTable } from "../../components/ScrollDataTable";
import { ResumenTable } from "../../components/ResumenTable";
import { RankingTable } from "../../components/RankingTable";
import { CategoricalDonut } from "../../components/charts/CategoricalDonut";
import { ComparativeBarChart } from "../../components/charts/ComparativeBarChart";
import { MultiAnnualLineChart } from "../../components/charts/MultiAnnualLineChart";
import { RankingBarChart } from "../../components/charts/RankingBarChart";
import { formatNumber, formatQAbrev, formatUSDAbrev, MESES, MESES_LARGOS } from "../../utils/format";
import { dashboardAccent } from "../../theme/colors";
import type {
  DashboardPlaguicidasResponse,
  DetalleTransaccionPlaguicida,
  OpcionesFiltroPlaguicidas,
} from "../../types/dashboard";

const ACCENT = dashboardAccent.plaguicidas;
const TAMANO_BLOQUE_DETALLE = 50;

export function DashboardPlaguicidasPage() {
  const [opciones, setOpciones] = useState<OpcionesFiltroPlaguicidas | null>(null);

  const [anio, setAnio] = useState("");
  const [mes, setMes] = useState("");
  const [origen, setOrigen] = useState<string[]>([]);
  const [aplicacion, setAplicacion] = useState<string[]>([]);
  const [ingredienteAct, setIngredienteAct] = useState<string[]>([]);
  const [producto, setProducto] = useState<string[]>([]);

  const [data, setData] = useState<DashboardPlaguicidasResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filasDetalle, setFilasDetalle] = useState<DetalleTransaccionPlaguicida[]>([]);
  const [bloqueDetalle, setBloqueDetalle] = useState(1);
  const [cargandoMasFilas, setCargandoMasFilas] = useState(false);

  useEffect(() => {
    obtenerOpcionesPlaguicidas().then(setOpciones).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerDashboardPlaguicidas({
      anio: anio ? Number(anio) : undefined,
      mes: mes ? Number(mes) : undefined,
      origen,
      aplicacion,
      ingredienteAct,
      producto,
      pagina: 1,
      tamanoPagina: TAMANO_BLOQUE_DETALLE,
    })
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        setFilasDetalle(res.detalle.filas);
        setBloqueDetalle(1);
        // Si el usuario no fijó año/mes explícitos, reflejar en los
        // selectores los valores por defecto que resolvió el backend
        // (el mes por defecto es independiente por dashboard, ver
        // services/dashboard_plaguicidas.py).
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
  }, [anio, mes, origen, aplicacion, ingredienteAct, producto]);

  function cargarMasFilasDetalle() {
    setCargandoMasFilas(true);
    const siguienteBloque = bloqueDetalle + 1;
    obtenerDashboardPlaguicidas({
      anio: anio ? Number(anio) : undefined,
      mes: mes ? Number(mes) : undefined,
      origen,
      aplicacion,
      ingredienteAct,
      producto,
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
    setAplicacion([]);
    setIngredienteAct([]);
    setProducto([]);
  }

  if (error) {
    return <p className="rounded-tremor-small bg-danger-surface px-4 py-3 text-sm text-danger">{error}</p>;
  }

  const anioActual = data?.anio_actual;
  const anioAnterior = data?.anio_anterior;

  const filtrosExport = {
    anio: anio ? Number(anio) : undefined,
    mes: mes ? Number(mes) : undefined,
    origen: origen.length ? origen : undefined,
    ingrediente_act: ingredienteAct.length ? ingredienteAct : undefined,
    aplicacion: aplicacion.length ? aplicacion : undefined,
    producto: producto.length ? producto : undefined,
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
        <Title className="text-ink">Dashboard de Plaguicidas</Title>
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
          />
          <FilterMultiCombobox
            label="Origen"
            values={origen}
            onChange={setOrigen}
            options={opciones?.origenes ?? []}
          />
          <FilterMultiCombobox
            label="Ingrediente activo"
            values={ingredienteAct}
            onChange={setIngredienteAct}
            options={opciones?.ingredientes_activos ?? []}
          />
          <FilterMultiCombobox
            label="Aplicación"
            values={aplicacion}
            onChange={setAplicacion}
            options={opciones?.aplicaciones ?? []}
          />
          <FilterMultiCombobox
            label="Producto"
            values={producto}
            onChange={setProducto}
            options={opciones?.productos ?? []}
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
            theme="plaguicidas"
            endpoint="/dashboard/plaguicidas/export-todo"
            filtros={filtrosExport}
            nombreArchivoPorDefecto={`plaguicidas_completo_${sufijoArchivo}.xlsx`}
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
            <KpiCard
              label="Ingredientes Activos"
              value={formatNumber(data.kpis.ingredientes_activos)}
              accentColor={ACCENT.tremor}
            />
          </div>

          <ChartCard
            theme="plaguicidas"
            title="Comparativo acumulado de CIF USD por mes"
            subtitle={`${anioActual} vs. ${anioAnterior}, hasta ${MESES_LARGOS[data.mes_seleccionado - 1]}`}
            exportar={
              <BotonExportarExcel
                theme="plaguicidas"
                endpoint="/dashboard/plaguicidas/export/acumulado-mensual"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`plaguicidas_acumulado_mensual_${sufijoArchivo}.xlsx`}
              />
            }
            chart={
              <ComparativeBarChart
                data={dataComparacionAcumulada}
                index="mes"
                categories={[`${anioActual}`, `${anioAnterior}`]}
                colors={[ACCENT.tremor, "slate"]}
              />
            }
            table={
              <SimpleDataTable
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
            theme="plaguicidas"
            title="Comparación mensual de CIF"
            subtitle={`${anioActual} vs. ${anioAnterior}, hasta ${MESES_LARGOS[data.mes_seleccionado - 1]}`}
            exportar={
              <BotonExportarExcel
                theme="plaguicidas"
                endpoint="/dashboard/plaguicidas/export/comparativo-mensual"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`plaguicidas_comparativo_mensual_${sufijoArchivo}.xlsx`}
              />
            }
            chart={
              <ComparativeBarChart
                data={dataComparacionMensual}
                index="mes"
                categories={[`${anioActual}`, `${anioAnterior}`]}
                colors={[ACCENT.tremor, "slate"]}
              />
            }
            table={
              <SimpleDataTable
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
            theme="plaguicidas"
            title="Comparativo acumulado de CIF USD por año"
            subtitle={`Últimos ${serieMultianual.length} año(s) con datos, hasta ${MESES_LARGOS[data.mes_seleccionado - 1]}`}
            exportar={
              <BotonExportarExcel
                theme="plaguicidas"
                endpoint="/dashboard/plaguicidas/export/acumulado-multianual"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`plaguicidas_acumulado_multianual_${sufijoArchivo}.xlsx`}
              />
            }
            chart={<MultiAnnualLineChart theme="plaguicidas" series={serieMultianual} />}
            table={
              <SimpleDataTable
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

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartCard
              theme="plaguicidas"
              title="Diversificación por tipo de aplicación"
              subtitle={`Año ${anioActual}`}
              exportar={
                <BotonExportarExcel
                  theme="plaguicidas"
                  endpoint="/dashboard/plaguicidas/export/por-aplicacion"
                  filtros={filtrosExport}
                  nombreArchivoPorDefecto={`plaguicidas_por_aplicacion_${sufijoArchivo}.xlsx`}
                />
              }
              chart={<CategoricalDonut data={data.diversificacion_aplicacion} />}
              table={
                <SimpleDataTable
                  columnas={[
                    { header: "Tipo de aplicación", accessor: (r) => r.etiqueta },
                    { header: "CIF USD", accessor: (r) => formatUSDAbrev(r.cif_usd), align: "right" },
                  ]}
                  filas={data.diversificacion_aplicacion}
                  getKey={(r) => r.etiqueta}
                />
              }
            />

            <ChartCard
              theme="plaguicidas"
              title="Top ingredientes activos"
              subtitle="Por CIF USD"
              exportar={
                <BotonExportarExcel
                  theme="plaguicidas"
                  endpoint="/dashboard/plaguicidas/export/top-moleculas"
                  filtros={filtrosExport}
                  nombreArchivoPorDefecto={`plaguicidas_top_moleculas_${sufijoArchivo}.xlsx`}
                />
              }
              chart={<RankingBarChart theme="plaguicidas" data={data.top_ingredientes} />}
              table={
                <SimpleDataTable
                  columnas={[
                    { header: "Ingrediente activo", accessor: (r) => r.etiqueta },
                    { header: "CIF USD", accessor: (r) => formatUSDAbrev(r.cif_usd), align: "right" },
                  ]}
                  filas={data.top_ingredientes}
                  getKey={(r) => r.etiqueta}
                />
              }
            />

          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartCard
              theme="plaguicidas"
              title="Top importadores"
              subtitle="Por CIF USD"
              exportar={
                <BotonExportarExcel
                  theme="plaguicidas"
                  endpoint="/dashboard/plaguicidas/export/top-importadores"
                  filtros={filtrosExport}
                  nombreArchivoPorDefecto={`plaguicidas_top_importadores_${sufijoArchivo}.xlsx`}
                />
              }
              chart={<RankingBarChart theme="plaguicidas" data={data.top_importadores} />}
              table={
                <SimpleDataTable
                  columnas={[
                    { header: "Importador", accessor: (r) => r.etiqueta },
                    { header: "CIF USD", accessor: (r) => formatUSDAbrev(r.cif_usd), align: "right" },
                  ]}
                  filas={data.top_importadores}
                  getKey={(r) => r.etiqueta}
                />
              }
            />

            <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
              <div className="mb-3 flex items-center justify-between gap-3">
                <Title className="text-ink">Top países de origen</Title>
                <BotonExportarExcel
                  theme="plaguicidas"
                  endpoint="/dashboard/plaguicidas/export/top-paises"
                  filtros={filtrosExport}
                  nombreArchivoPorDefecto={`plaguicidas_top_paises_${sufijoArchivo}.xlsx`}
                />
              </div>
              <RankingTable filas={data.top_origenes} etiquetaColumna="País" etiquetaConteo="Transacciones" />
            </div>
          </div>

          <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
            <Title className="mb-3 text-ink">Importadores — transacciones y CIF</Title>
            <ResumenTable filas={data.tabla_resumen_importadores} etiquetaColumna="Importador" accentColor={ACCENT.tremor} />
          </div>

          <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
            <div className="mb-3 flex items-center justify-between gap-3">
              <Title className="text-ink">Nombres comerciales — ordenado por CIF USD</Title>
              <BotonExportarExcel
                theme="plaguicidas"
                endpoint="/dashboard/plaguicidas/export/nombres-comerciales"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`plaguicidas_nombres_comerciales_${sufijoArchivo}.xlsx`}
              />
            </div>
            <SimpleDataTable
              columnas={[
                { header: "Producto", accessor: (r) => r.producto },
                { header: "Grupo", accessor: (r) => r.grupo ?? "—" },
                { header: "Aplicación", accessor: (r) => r.aplicacion ?? "—" },
                { header: "Importador", accessor: (r) => r.importador ?? "—" },
                { header: "Origen", accessor: (r) => r.origen ?? "—" },
                { header: "Cantidad", accessor: (r) => formatNumber(r.cantidad), align: "right" },
                { header: "Unidad", accessor: (r) => r.unidad_medida ?? "—" },
                { header: "CIF USD", accessor: (r) => formatUSDAbrev(r.cif_usd), align: "right" },
                { header: "CIF Q", accessor: (r) => formatQAbrev(r.cif_q), align: "right" },
              ]}
              filas={data.tabla_nombres_comerciales}
              getKey={(r, i) => `${r.producto}-${i}`}
            />
          </div>

          <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
            <div className="mb-3 flex items-center justify-between gap-3">
              <Title className="text-ink">Grupo — ordenado por CIF USD</Title>
              <BotonExportarExcel
                theme="plaguicidas"
                endpoint="/dashboard/plaguicidas/export/grupo"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`plaguicidas_grupo_${sufijoArchivo}.xlsx`}
              />
            </div>
            <SimpleDataTable
              columnas={[
                { header: "Grupo", accessor: (r) => r.grupo },
                { header: "% del total", accessor: (r) => `${r.porcentaje_del_total.toFixed(1)}%`, align: "right" },
                { header: "Aplicación principal", accessor: (r) => r.aplicacion_principal ?? "—" },
                { header: "Cantidad", accessor: (r) => formatNumber(r.cantidad), align: "right" },
                { header: "Unidad", accessor: (r) => r.unidad_medida ?? "—" },
                { header: "CIF USD", accessor: (r) => formatUSDAbrev(r.cif_usd), align: "right" },
                { header: "CIF Q", accessor: (r) => formatQAbrev(r.cif_q), align: "right" },
              ]}
              filas={data.tabla_grupos}
              getKey={(r) => r.grupo}
            />
          </div>

          <div className="rounded-tremor-default bg-surface p-4 ring-1 ring-line">
            <div className="mb-3 flex items-center justify-between gap-3">
              <Title className="text-ink">Detalle de transacciones</Title>
              <BotonExportarExcel
                theme="plaguicidas"
                endpoint="/dashboard/plaguicidas/export/detalle"
                filtros={filtrosExport}
                nombreArchivoPorDefecto={`plaguicidas_detalle_${sufijoArchivo}.xlsx`}
              />
            </div>
            <ScrollDataTable
              columnas={[
                { header: "Fecha", accessor: (r) => r.fecha ?? "—" },
                { header: "Recibo", accessor: (r) => r.recibointerno ?? "—" },
                { header: "Aplicación", accessor: (r) => r.aplicacion ?? "—" },
                { header: "Importador", accessor: (r) => r.importador ?? "—" },
                { header: "Producto", accessor: (r) => r.producto ?? "—" },
                { header: "Ingrediente activo", accessor: (r) => r.ingrediente_act ?? "—" },
                { header: "Exportador", accessor: (r) => r.exportador ?? "—" },
                { header: "Origen", accessor: (r) => r.origen ?? "—" },
                { header: "Institución", accessor: (r) => r.institucion ?? "—" },
              ]}
              filas={filasDetalle}
              total={data.detalle.total}
              cargandoMas={cargandoMasFilas}
              hayMas={filasDetalle.length < data.detalle.total}
              onCargarMas={cargarMasFilasDetalle}
              getKey={(r, i) => `${r.recibointerno}-${i}`}
            />
          </div>
        </>
      )}
    </div>
  );
}

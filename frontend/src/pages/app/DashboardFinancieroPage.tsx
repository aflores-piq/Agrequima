import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Title } from "@tremor/react";
import { obtenerDashboardFinanciero } from "../../api/dashboardFinanciero";
import { mensajeError } from "../../api/client";
import { FilterYearMonth } from "../../components/filters/PowerBiFilter";
import { ChartCard } from "../../components/ChartCard";
import { TresBarrasResultado } from "../../components/charts/TresBarrasResultado";
import { ComparativoAnioBarChart } from "../../components/charts/ComparativoAnioBarChart";
import { BalanceDonut } from "../../components/charts/BalanceDonut";
import {
  TablaGrupoExpandible,
  BandaResumenVerde,
  KpiCardIcono,
  KpiCardIconoComparativo,
  FINANCIERO_SURFACE,
  GAP_TITULO_PRIMER_ELEMENTO,
  type FilaGrupo,
} from "../../components/TablaGrupoExpandible";
import { formatPercent, formatQ, MESES_LARGOS, pctSeguro } from "../../utils/format";
import {
  tituloBalanceAcumuladoAl,
  tituloBalanceAcumuladoComparativo,
  tituloBalanceAl,
  tituloDiferenciaPorcentual,
  tituloEstadoAcumulado,
  tituloEstadoComparativo,
  tituloGraficaAcumuladoAl,
} from "../../utils/titulosFinanciero";
import type { DashboardFinancieroResponse } from "../../types/dashboardFinanciero";
import { useFinancieroFilterGrupo1 } from "../../financiero/FinancieroFilterContext";

// Mismos colores confirmados pixel a pixel contra las capturas reales
// (docs/legacy/Financiero_capturas/): Ingresos/Activo teal, Egresos/
// Pasivo coral, Resultado azul, Patrimonio azul marino.
const COLOR_TEAL = "#3f6f6b";
const COLOR_CORAL = "#e87471";
const COLOR_AZUL = "#507eaa";
const COLOR_MARINO = "#375b7d";

// Alto REAL del panel completo de gráfico (tarjeta con título) medido
// en el .pbix original, proporcional al ancho que cada gráfico ya
// tiene hoy en la app (páginas 1: ~805px→372px; 2: ~846px→382px; 3:
// ~764px→375px; 4: ~846px→388px, todas parecidas) -- estandarizado a
// 380px en las 4. Este valor NO es directamente el prop `altura` de
// abajo: hay que restarle el "overhead" fijo del título+padding de la
// tarjeta (medido: 292px de panel con altura=200 ⇒ overhead=92px) para
// que el panel completo termine midiendo 380px de verdad.
const ALTURA_PANEL_COMPLETO = 380;
const ALTURA_PANEL_GRAFICO = ALTURA_PANEL_COMPLETO - 92;

// Ancho ÚNICO de tabla para las 4 páginas -- antes cada página definía
// su propio % por separado (56% / 57% / 55% / 55%) y no coincidían
// entre sí. Reconciliado a un solo valor (55%, el que ya compartían 2
// de las 4) para que las 4 tablas midan EXACTAMENTE lo mismo en
// píxeles, medido con un único wrapper `style={{ width: ANCHO_TABLA }}`
// en vez de una clase `w-[...]` repetida en cada página (con clases de
// Tailwind arbitrarias no se puede interpolar un valor en runtime desde
// una sola constante -- Tailwind necesita ver el literal en el código
// para generarlo -- por eso este valor se aplica con `style`, no con
// className, así hay un solo lugar que lo define de verdad).
// En páginas 1, 2 y 3 la fila de KPIs comparte este mismo valor (mismo
// wrapper en 1 y 2; wrapper propio pero con el mismo ancho en 3) --
// página 4 queda afuera de esa regla a propósito (ver su KPI row).
const ANCHO_TABLA_FINANCIERO = "55%";

// --- Tabla chica (no expandible) para las mini-tablas que acompañan
// los gráficos de barra al final de cada página (categorías fijas:
// Ingresos/Egresos/Resultado o Activo/Pasivo/Patrimonio, no Grupos). ---
function TablaCategorias({ filas }: { filas: { etiqueta: string; valores: string[] }[] }) {
  return (
    <table className="w-full text-sm">
      <tbody>
        {filas.map((f) => (
          <tr key={f.etiqueta}>
            <td className="px-2 py-1.5 text-ink">{f.etiqueta}</td>
            {f.valores.map((v, i) => (
              <td key={i} className="px-2 py-1.5 text-right text-ink">
                {v}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function filaGrupo<T extends { grupo: string; cuentas: { cuenta?: string }[] }>(
  f: T,
  valores: number[],
  cuentaValores: (c: T["cuentas"][number]) => number[]
): FilaGrupo {
  return {
    grupo: f.grupo,
    valores,
    cuentas: f.cuentas.map((c) => ({ nombre: (c as { cuenta: string }).cuenta, valores: cuentaValores(c) })),
  };
}

// Las 4 "páginas" internas ahora son un query param (?vista=) en vez de
// solo estado local -- así el menú lateral (ver Sidebar.tsx) puede
// enlazar a cada una por separado y queden URLs reales/compartibles,
// no solo pestañas internas invisibles para el navegador.
const VISTAS = ["mensual", "acumulado", "balance-mensual", "balance-comparativo"] as const;

export function DashboardFinancieroPage() {
  const [searchParams] = useSearchParams();
  const vistaParam = searchParams.get("vista") ?? "mensual";
  // Navegación entre las 4 páginas solo por el sidebar (Link a
  // ?vista=...) -- esta página solo LEE el query param, ya no lo
  // escribe (antes había pestañas internas propias, eliminadas por
  // redundantes).
  const pagina = Math.max(0, VISTAS.indexOf(vistaParam as (typeof VISTAS)[number]));

  const [data, setData] = useState<DashboardFinancieroResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Año+Mes sincronizado con el resto del Grupo 1 (Otros informes
  // financieros, y a futuro Presupuestos / Comparación importaciones
  // kilolitros) -- ver FinancieroFilterContext.
  const { anio, mes, setAnioMes, cambiarAnio, cambiarMes } = useFinancieroFilterGrupo1(data?.periodos_disponibles ?? []);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerDashboardFinanciero(anio ? Number(anio) : undefined, mes ? Number(mes) : undefined)
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
  // Selector con drill de 2 niveles (Año expandible + Mes, calcado de
  // la estructura real "2026 (Año) +") -- cada nivel solo ofrece
  // combinaciones que existen de verdad en BalanceSaldos/BalanceGeneral.
  const aniosDisponibles = Array.from(new Set(periodos.map((p) => p.anio))).sort((a, b) => a - b);
  const mesesDelAnioSeleccionado = periodos
    .filter((p) => String(p.anio) === anio)
    .map((p) => p.mes)
    .sort((a, b) => a - b);
  const mesOpciones = mesesDelAnioSeleccionado.map((m) => ({ value: String(m), label: MESES_LARGOS[m - 1] }));

  // Títulos de página = medidas DAX del .pbix real (ver utils/titulosFinanciero.ts):
  // ERComparativo, ERMensual, BalanceMensual y BalanceAcumulado. OJO: en el .pbix
  // la página "Estado de ingresos y desembolsos mensual" lleva el título
  // "...Comparativo Al {último día} de {Mes} de {Año} vs {Año-1}" y la página
  // "...acumulado" lleva "...Acumulado a {Mes} {Año}" -- así está en Power BI.
  const tituloPagina = data
    ? [
        tituloEstadoComparativo(data.anio, data.mes),
        tituloEstadoAcumulado(data.anio, data.mes),
        tituloBalanceAcumuladoAl(data.anio, data.mes),
        tituloBalanceAcumuladoComparativo(data.anio, data.mes),
      ][pagina]
    : "Estados Financieros";

  return (
    // El ancho ya lo topa `main` en AppLayout.tsx (max-w-[1658px] solo
    // para la ruta de Financiero) -- acá adentro no hace falta ningún
    // truco de viewport, este div ya recibe el 100% de ese ancho
    // (excluyendo el sidebar, que es hermano flex de `main`). Todos los
    // porcentajes de las 4 páginas de abajo (56%, 57%, 55%, 52%, 47%,
    // etc.) son relativos a ESTE ancho.
    <div className="space-y-3">
      <div className="relative flex min-h-[40px] items-center justify-center">
        {/* Título unificado al mismo estilo que el resto del módulo
            (text-2xl font-bold) -- antes text-3xl sin negrita, un nivel
            visualmente distinto del resto de las 14 pantallas del
            Financiero (revisión de consistencia visual, ronda de
            estandarización). */}
        <Title className="px-4 text-center text-2xl font-bold text-ink">{tituloPagina}</Title>
        {/* Arriba a la derecha, en la MISMA fila que el título (top-0,
            no debajo) -- mismo patrón que las otras 13 pantallas del
            módulo (ver PaginaEjecucionGastos, Presupuestos, etc.). */}
        <div className="absolute right-0 top-0">
          <FilterYearMonth
            label="Año y Mes"
            theme="gris"
            anio={anio}
            mes={mes}
            onChangeAnio={cambiarAnio}
            onChangeMes={cambiarMes}
            aniosOpciones={aniosDisponibles.map(String)}
            mesesOpciones={mesOpciones}
          />
        </div>
      </div>

      {/* Pestañas internas eliminadas -- redundantes con el sidebar, que
          ya tiene un link a cada una de las 4 páginas dentro de "Estados
          financieros" (ver Sidebar.tsx). La navegación entre páginas
          queda solo por ahí; `pagina`/`setPagina` siguen derivados del
          query param ?vista= (ver arriba), no cambia la lógica interna. */}

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          {/* --- Página 1: Ingresos y desembolsos mensual --- */}
          {pagina === 0 &&
            (() => {
              const p1 = data.ingresos_desembolsos_mensual;
              const columnas = [p1.etiqueta_mes_anterior, p1.etiqueta_mes_actual, p1.etiqueta_acumulado];
              // "Acumulado Año 2026" necesita más ancho que Mayo/Junio para
              // no partirse en 2 líneas -- las 4 columnas como % (no un
              // ancho fijo + %, que no reparte bien el espacio restante).
              const anchoEtiquetaP1 = "42%";
              const anchosDatosP1 = ["17%", "17%", "24%"];
              return (
                <div className="space-y-5" style={{ marginTop: GAP_TITULO_PRIMER_ELEMENTO }}>
                  {/* Tabla y fila de KPIs comparten el mismo wrapper y el
                      mismo ancho único (ANCHO_TABLA_FINANCIERO, ver
                      arriba) -- así miden exactamente lo mismo. */}
                  <div className="mx-auto space-y-5" style={{ width: ANCHO_TABLA_FINANCIERO }}>
                    <div className="flex flex-wrap justify-center gap-3">
                      <KpiCardIcono letra="I" color={COLOR_TEAL} label="Ingresos" valor={formatQ(p1.kpis.ingresos)} />
                      <KpiCardIcono letra="E" color={COLOR_CORAL} label="Egresos" valor={formatQ(p1.kpis.egresos)} />
                      <KpiCardIcono letra="R" color={COLOR_AZUL} label="Resultado" valor={formatQ(p1.kpis.resultado)} />
                    </div>

                    <TablaGrupoExpandible
                      titulo="Ingresos"
                      columnas={columnas}
                      anchoEtiqueta={anchoEtiquetaP1}
                      anchosDatos={anchosDatosP1}
                      filas={p1.detalle_ingresos.map((f) => filaGrupo(f, [f.mes_anterior, f.mes_actual, f.acumulado_anio], (c) => [c.mes_anterior, c.mes_actual, c.acumulado_anio]))}
                      etiquetaTotal="Total ingresos"
                      totalValores={[p1.total_ingresos.mes_anterior, p1.total_ingresos.mes_actual, p1.total_ingresos.acumulado_anio]}
                    />
                    <TablaGrupoExpandible
                      titulo="Egresos"
                      columnas={columnas}
                      anchoEtiqueta={anchoEtiquetaP1}
                      anchosDatos={anchosDatosP1}
                      filas={p1.detalle_egresos.map((f) => filaGrupo(f, [f.mes_anterior, f.mes_actual, f.acumulado_anio], (c) => [c.mes_anterior, c.mes_actual, c.acumulado_anio]))}
                      etiquetaTotal="Total egresos"
                      totalValores={[p1.total_egresos.mes_anterior, p1.total_egresos.mes_actual, p1.total_egresos.acumulado_anio]}
                    />
                    <BandaResumenVerde
                      etiqueta="Resultado del ejercicio"
                      columnas={columnas}
                      anchoEtiqueta={anchoEtiquetaP1}
                      anchosDatos={anchosDatosP1}
                      valores={[p1.resultado_del_ejercicio.mes_anterior, p1.resultado_del_ejercicio.mes_actual, p1.resultado_del_ejercicio.acumulado_anio]}
                    />
                  </div>

                  {/* Los 2 gráficos van MÁS ANCHOS que la tabla a propósito
                      (~48% cada uno, ~98% combinados, borde a borde) -- así
                      es el diseño real del .pbix, no un error. */}
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <ChartCard
                      theme="financiero"
                      estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
                      title={p1.titulo_grafico_mes}
                      chart={<TresBarrasResultado altura={ALTURA_PANEL_GRAFICO} ingresos={p1.grafico_mes.ingresos} egresos={p1.grafico_mes.egresos} resultado={p1.grafico_mes.resultado} />}
                      table={
                        <TablaCategorias
                          filas={[
                            { etiqueta: "Ingresos netos", valores: [formatQ(p1.grafico_mes.ingresos)] },
                            { etiqueta: "Egresos", valores: [formatQ(-p1.grafico_mes.egresos)] },
                            { etiqueta: "Resultado", valores: [formatQ(p1.grafico_mes.resultado)] },
                          ]}
                        />
                      }
                    />
                    <ChartCard
                      theme="financiero"
                      estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
                      title={tituloGraficaAcumuladoAl(data.anio, data.mes)}
                      chart={<TresBarrasResultado altura={ALTURA_PANEL_GRAFICO} ingresos={p1.grafico_acumulado.ingresos} egresos={p1.grafico_acumulado.egresos} resultado={p1.grafico_acumulado.resultado} />}
                      table={
                        <TablaCategorias
                          filas={[
                            { etiqueta: "Ingresos netos", valores: [formatQ(p1.grafico_acumulado.ingresos)] },
                            { etiqueta: "Egresos", valores: [formatQ(-p1.grafico_acumulado.egresos)] },
                            { etiqueta: "Resultado", valores: [formatQ(p1.grafico_acumulado.resultado)] },
                          ]}
                        />
                      }
                    />
                  </div>
                </div>
              );
            })()}

          {/* --- Página 2: Ingresos y desembolsos acumulado --- */}
          {pagina === 1 &&
            (() => {
              const p2 = data.ingresos_desembolsos_acumulado;
              // Encabezados = medidas ERAnioAnterior / ERAnioActual del .pbix:
              // "Acumulado {año-1}" y "Acumulado {año}" (la gráfica de abajo conserva "2025"/"2026").
              const columnas = [`Acumulado ${data.anio - 1}`, `Acumulado ${data.anio}`, "Variación"];
              const datosGrafico = ["Ingresos", "Egresos", "Resultado"].map((cat) => ({
                categoria: cat,
                [p2.etiqueta_anio_anterior]:
                  cat === "Ingresos" ? p2.grafico[0].ingresos : cat === "Egresos" ? p2.grafico[0].egresos : p2.grafico[0].resultado,
                [p2.etiqueta_anio_actual]:
                  cat === "Ingresos" ? p2.grafico[1].ingresos : cat === "Egresos" ? p2.grafico[1].egresos : p2.grafico[1].resultado,
              }));
              return (
                <div className="space-y-5" style={{ marginTop: GAP_TITULO_PRIMER_ELEMENTO }}>
                  {/* Mismo ancho único que las otras 3 páginas
                      (ANCHO_TABLA_FINANCIERO), mismo wrapper para tabla
                      y KPIs. */}
                  <div className="mx-auto space-y-5" style={{ width: ANCHO_TABLA_FINANCIERO }}>
                    <div className="flex flex-wrap justify-center gap-3">
                      <KpiCardIcono letra="I" color={COLOR_TEAL} label="Ingresos" valor={formatQ(p2.kpis.ingresos)} />
                      <KpiCardIcono letra="E" color={COLOR_CORAL} label="Egresos" valor={formatQ(p2.kpis.egresos)} />
                      <KpiCardIcono letra="S" color={COLOR_AZUL} label="Saldo" valor={formatQ(p2.kpis.saldo)} />
                    </div>

                    <TablaGrupoExpandible
                      titulo="Ingresos"
                      columnas={columnas}
                      filas={p2.detalle_ingresos.map((f) => filaGrupo(f, [f.anio_anterior, f.anio_actual, f.variacion], (c) => [c.anio_anterior, c.anio_actual, c.variacion]))}
                      etiquetaTotal="Total ingresos"
                      totalValores={[p2.total_ingresos.anio_anterior, p2.total_ingresos.anio_actual, p2.total_ingresos.variacion]}
                    />
                    <TablaGrupoExpandible
                      titulo="Egresos"
                      columnas={columnas}
                      filas={p2.detalle_egresos.map((f) => filaGrupo(f, [f.anio_anterior, f.anio_actual, f.variacion], (c) => [c.anio_anterior, c.anio_actual, c.variacion]))}
                      etiquetaTotal="Total egresos"
                      totalValores={[p2.total_egresos.anio_anterior, p2.total_egresos.anio_actual, p2.total_egresos.variacion]}
                    />
                    <BandaResumenVerde
                      etiqueta="Resultado del ejercicio"
                      columnas={columnas}
                      valores={[p2.resultado_del_ejercicio.anio_anterior, p2.resultado_del_ejercicio.anio_actual, p2.resultado_del_ejercicio.variacion]}
                    />
                  </div>

                  {/* El gráfico va MÁS ANGOSTO que la tabla acá (~52%,
                      centrado) -- al revés que en la página 1. */}
                  <div className="mx-auto w-[52%]">
                    <ChartCard
                      theme="financiero"
                      estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
                      title={p2.titulo_grafico}
                      chart={
                        <ComparativoAnioBarChart
                          altura={ALTURA_PANEL_GRAFICO}
                          data={datosGrafico}
                          etiquetaAnioAnterior={p2.etiqueta_anio_anterior}
                          etiquetaAnioActual={p2.etiqueta_anio_actual}
                        />
                      }
                      table={
                        <TablaCategorias
                          filas={datosGrafico.map((d: any) => ({
                            etiqueta: d.categoria,
                            valores: [formatQ(d[p2.etiqueta_anio_anterior]), formatQ(d[p2.etiqueta_anio_actual])],
                          }))}
                        />
                      }
                    />
                  </div>
                </div>
              );
            })()}

          {/* --- Página 3: Balance general mensual --- */}
          {pagina === 2 &&
            (() => {
              const p3 = data.balance_general_mensual;
              const columnas = [p3.etiqueta_mes_anterior, p3.etiqueta_mes_actual, "Diferencia", "% Variación"];
              const formattersP3 = [formatQ, formatQ, formatQ, formatPercent];
              return (
                <div className="space-y-5" style={{ marginTop: GAP_TITULO_PRIMER_ELEMENTO }}>
                  {/* Tabla y fila de KPIs comparten el mismo wrapper y el
                      mismo ancho único (ANCHO_TABLA_FINANCIERO) -- antes
                      la fila de KPIs tenía su propio wrapper 2.85% más
                      ancho que la tabla, ahora miden exactamente lo mismo. */}
                  <div className="mx-auto space-y-5" style={{ width: ANCHO_TABLA_FINANCIERO }}>
                    <div className="flex flex-wrap justify-center gap-3">
                      <KpiCardIcono letra="A" color={COLOR_TEAL} label="Activo" valor={formatQ(p3.kpis.activo)} />
                      <KpiCardIcono letra="PA" color={COLOR_CORAL} label="Pasivo" valor={formatQ(p3.kpis.pasivo)} />
                      <KpiCardIcono letra="PT" color={COLOR_MARINO} label="Patrimonio" valor={formatQ(p3.kpis.patrimonio)} />
                    </div>

                    <div className="space-y-5">
                      <TablaGrupoExpandible
                        titulo="Activo"
                        columnas={columnas}
                        formatters={formattersP3}
                        filas={p3.detalle_activo.map((f) =>
                          filaGrupo(
                            f,
                            [f.mes_anterior, f.mes_actual, f.diferencia, pctSeguro(f.diferencia, f.mes_anterior)],
                            (c) => [c.mes_anterior, c.mes_actual, c.diferencia, pctSeguro(c.diferencia, c.mes_anterior)]
                          )
                        )}
                        etiquetaTotal="Total"
                        totalValores={[
                          p3.total_activo.mes_anterior,
                          p3.total_activo.mes_actual,
                          p3.total_activo.diferencia,
                          pctSeguro(p3.total_activo.diferencia, p3.total_activo.mes_anterior),
                        ]}
                      />
                      <TablaGrupoExpandible
                        titulo="Pasivo"
                        columnas={columnas}
                        formatters={formattersP3}
                        filas={p3.detalle_pasivo.map((f) =>
                          filaGrupo(
                            f,
                            [f.mes_anterior, f.mes_actual, f.diferencia, pctSeguro(f.diferencia, f.mes_anterior)],
                            (c) => [c.mes_anterior, c.mes_actual, c.diferencia, pctSeguro(c.diferencia, c.mes_anterior)]
                          )
                        )}
                        etiquetaTotal="Total"
                        totalValores={[
                          p3.total_pasivo.mes_anterior,
                          p3.total_pasivo.mes_actual,
                          p3.total_pasivo.diferencia,
                          pctSeguro(p3.total_pasivo.diferencia, p3.total_pasivo.mes_anterior),
                        ]}
                      />
                      <TablaGrupoExpandible
                        titulo="Patrimonio"
                        columnas={columnas}
                        formatters={formattersP3}
                        filas={p3.detalle_patrimonio.map((f) =>
                          filaGrupo(
                            f,
                            [f.mes_anterior, f.mes_actual, f.diferencia, pctSeguro(f.diferencia, f.mes_anterior)],
                            (c) => [c.mes_anterior, c.mes_actual, c.diferencia, pctSeguro(c.diferencia, c.mes_anterior)]
                          )
                        )}
                        etiquetaTotal="Total"
                        totalValores={[
                          p3.total_patrimonio.mes_anterior,
                          p3.total_patrimonio.mes_actual,
                          p3.total_patrimonio.diferencia,
                          pctSeguro(p3.total_patrimonio.diferencia, p3.total_patrimonio.mes_anterior),
                        ]}
                      />
                      <BandaResumenVerde
                        etiqueta="Total pasivo y patrimonio"
                        columnas={columnas}
                        formatters={formattersP3}
                        valores={[
                          p3.total_pasivo_y_patrimonio.mes_anterior,
                          p3.total_pasivo_y_patrimonio.mes_actual,
                          p3.total_pasivo_y_patrimonio.diferencia,
                          pctSeguro(p3.total_pasivo_y_patrimonio.diferencia, p3.total_pasivo_y_patrimonio.mes_anterior),
                        ]}
                      />
                    </div>
                  </div>

                  {/* Dona al 47%, centrada, mismo alto de panel que las
                      demás páginas (antes quedaba más baja). */}
                  <div className="mx-auto w-[47%]">
                    <ChartCard
                      theme="financiero"
                      estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
                      title={tituloBalanceAl(data.anio, data.mes)}
                      chart={<BalanceDonut altura={ALTURA_PANEL_GRAFICO} data={p3.distribucion_balance} activoReferencia={p3.activo_referencia} />}
                      table={
                        <TablaCategorias
                          filas={p3.distribucion_balance.map((d) => ({ etiqueta: d.etiqueta, valores: [formatPercent(d.porcentaje), formatQ(d.monto)] }))}
                        />
                      }
                    />
                  </div>
                </div>
              );
            })()}

          {/* --- Página 4: Balance general comparativo --- */}
          {pagina === 3 &&
            (() => {
              const p4 = data.balance_general_comparativo;
              // Encabezados = medidas MesAñoAnterior / MesAñoSeleccionado del .pbix:
              // "{Mes} {año-1}" y "{Mes} {año}" (la leyenda de la gráfica conserva "2025"/"2026").
              const columnas = [`${MESES_LARGOS[data.mes - 1]} ${data.anio - 1}`, `${MESES_LARGOS[data.mes - 1]} ${data.anio}`, "Variación", "% Variación"];
              // % Variación con 1 decimal (formatPercent, no formatPercent2) --
              // unificado con Balance general mensual: todo % NUEVO de esta
              // ronda va con 1 decimal, sin excepción por pantalla.
              const formattersP4 = [formatQ, formatQ, formatQ, formatPercent];
              const datosGrafico = ["Activo", "Pasivo", "Patrimonio"].map((cat) => ({
                categoria: cat,
                [p4.etiqueta_anio_anterior]: cat === "Activo" ? p4.grafico[0].activo : cat === "Pasivo" ? p4.grafico[0].pasivo : p4.grafico[0].patrimonio,
                [p4.etiqueta_anio_actual]: cat === "Activo" ? p4.grafico[1].activo : cat === "Pasivo" ? p4.grafico[1].pasivo : p4.grafico[1].patrimonio,
              }));
              return (
                <div className="space-y-5" style={{ marginTop: GAP_TITULO_PRIMER_ELEMENTO }}>
                  {/* Fila de KPIs de esta página: más ancha que la tabla
                      (57% vs 55%) porque cada tarjeta tiene más contenido
                      (título de 2 líneas + porcentaje + monto) que las
                      simples de las otras 3 páginas -- reducida de 59.6%
                      (quedaba visiblemente más grande que en la captura
                      real de Power BI, ver KpiCardIconoComparativo).
                      Centrada simple (antes tenía un offset asimétrico
                      `ml-[19.9%]` que compensaba el ancho mucho mayor de
                      antes; con este ancho más chico ya no hace falta). */}
                  <div className="mx-auto w-[57%]">
                    <div className="flex flex-wrap justify-center gap-3">
                      <KpiCardIconoComparativo
                        letra="A"
                        color={COLOR_TEAL}
                        tituloLinea1={tituloDiferenciaPorcentual("Activo", data.anio, data.mes).linea1}
                        tituloLinea2={tituloDiferenciaPorcentual("Activo", data.anio, data.mes).linea2}
                        porcentaje={formatPercent(p4.kpis.activo.diferencia_porcentaje)}
                        monto={formatQ(p4.kpis.activo.variacion_q)}
                      />
                      <KpiCardIconoComparativo
                        letra="PA"
                        color={COLOR_CORAL}
                        tituloLinea1={tituloDiferenciaPorcentual("Pasivo", data.anio, data.mes).linea1}
                        tituloLinea2={tituloDiferenciaPorcentual("Pasivo", data.anio, data.mes).linea2}
                        porcentaje={formatPercent(p4.kpis.pasivo.diferencia_porcentaje)}
                        monto={formatQ(p4.kpis.pasivo.variacion_q)}
                      />
                      <KpiCardIconoComparativo
                        letra="PT"
                        color={COLOR_MARINO}
                        tituloLinea1={tituloDiferenciaPorcentual("Patrimonio", data.anio, data.mes).linea1}
                        tituloLinea2={tituloDiferenciaPorcentual("Patrimonio", data.anio, data.mes).linea2}
                        porcentaje={formatPercent(p4.kpis.patrimonio.diferencia_porcentaje)}
                        monto={formatQ(p4.kpis.patrimonio.variacion_q)}
                      />
                    </div>
                  </div>

                  {/* Mismo ancho único que las otras 3 páginas
                      (ANCHO_TABLA_FINANCIERO) -- la fila de KPIs de esta
                      página queda afuera de esa regla a propósito (ver
                      comentario del wrapper de la fila de KPIs arriba). */}
                  <div className="mx-auto space-y-5" style={{ width: ANCHO_TABLA_FINANCIERO }}>
                    <TablaGrupoExpandible
                      titulo="Activo"
                      columnas={columnas}
                      formatters={formattersP4}
                      filas={p4.detalle_activo.map((f) =>
                        filaGrupo(
                          f,
                          [f.anio_anterior, f.anio_actual, f.variacion, pctSeguro(f.variacion, f.anio_anterior)],
                          (c) => [c.anio_anterior, c.anio_actual, c.variacion, pctSeguro(c.variacion, c.anio_anterior)]
                        )
                      )}
                      etiquetaTotal="Total"
                      totalValores={[
                        p4.total_activo.anio_anterior,
                        p4.total_activo.anio_actual,
                        p4.total_activo.variacion,
                        pctSeguro(p4.total_activo.variacion, p4.total_activo.anio_anterior),
                      ]}
                    />
                    <TablaGrupoExpandible
                      titulo="Pasivo"
                      columnas={columnas}
                      formatters={formattersP4}
                      filas={p4.detalle_pasivo.map((f) =>
                        filaGrupo(
                          f,
                          [f.anio_anterior, f.anio_actual, f.variacion, pctSeguro(f.variacion, f.anio_anterior)],
                          (c) => [c.anio_anterior, c.anio_actual, c.variacion, pctSeguro(c.variacion, c.anio_anterior)]
                        )
                      )}
                      etiquetaTotal="Total"
                      totalValores={[
                        p4.total_pasivo.anio_anterior,
                        p4.total_pasivo.anio_actual,
                        p4.total_pasivo.variacion,
                        pctSeguro(p4.total_pasivo.variacion, p4.total_pasivo.anio_anterior),
                      ]}
                    />
                    <TablaGrupoExpandible
                      titulo="Patrimonio"
                      columnas={columnas}
                      formatters={formattersP4}
                      filas={p4.detalle_patrimonio.map((f) =>
                        filaGrupo(
                          f,
                          [f.anio_anterior, f.anio_actual, f.variacion, pctSeguro(f.variacion, f.anio_anterior)],
                          (c) => [c.anio_anterior, c.anio_actual, c.variacion, pctSeguro(c.variacion, c.anio_anterior)]
                        )
                      )}
                      etiquetaTotal="Total"
                      totalValores={[
                        p4.total_patrimonio.anio_anterior,
                        p4.total_patrimonio.anio_actual,
                        p4.total_patrimonio.variacion,
                        pctSeguro(p4.total_patrimonio.variacion, p4.total_patrimonio.anio_anterior),
                      ]}
                    />
                    <BandaResumenVerde
                      etiqueta="Total pasivo y patrimonio"
                      columnas={columnas}
                      formatters={formattersP4}
                      valores={[
                        p4.total_pasivo_y_patrimonio.anio_anterior,
                        p4.total_pasivo_y_patrimonio.anio_actual,
                        p4.total_pasivo_y_patrimonio.variacion,
                        pctSeguro(p4.total_pasivo_y_patrimonio.variacion, p4.total_pasivo_y_patrimonio.anio_anterior),
                      ]}
                    />
                  </div>

                  {/* Gráfico al 52%, centrado -- mismo criterio que página 2. */}
                  <div className="mx-auto w-[52%]">
                    <ChartCard
                      theme="financiero"
                      estiloTarjeta={{ backgroundColor: FINANCIERO_SURFACE }}
                      title={p4.titulo_grafico}
                      chart={
                        <ComparativoAnioBarChart
                          altura={ALTURA_PANEL_GRAFICO}
                          data={datosGrafico}
                          etiquetaAnioAnterior={p4.etiqueta_anio_anterior}
                          etiquetaAnioActual={p4.etiqueta_anio_actual}
                        />
                      }
                      table={
                        <TablaCategorias
                          filas={datosGrafico.map((d: any) => ({
                            etiqueta: d.categoria,
                            valores: [formatQ(d[p4.etiqueta_anio_anterior]), formatQ(d[p4.etiqueta_anio_actual])],
                          }))}
                        />
                      }
                    />
                  </div>
                </div>
              );
            })()}
        </>
      )}
    </div>
  );
}

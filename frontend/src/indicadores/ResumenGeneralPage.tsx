import { useEffect, useState } from "react";
import { mensajeError } from "../api/client";
import {
  obtenerAcumulado,
  obtenerColaboradores,
  obtenerDetalle,
  obtenerMeses,
  obtenerTarjetas,
  obtenerTiposGasto,
} from "./api";
import { FiltroAnioMes } from "./FiltroAnioMes";
import { GraficaAcumulada } from "./GraficaAcumulada";
import { GraficaBarras } from "./GraficaBarras";
import { GraficaDona } from "./GraficaDona";
import { Icono } from "./iconos";
import { TablaDetalle } from "./TablaDetalle";
import { TarjetaKpi } from "./TarjetaKpi";
import type {
  AcumuladoRespuesta,
  AgrupadoRespuesta,
  DetalleRespuesta,
  MesDisponible,
  Periodo,
  TarjetasRespuesta,
} from "./tipos";

interface DatosPagina {
  tarjetas: TarjetasRespuesta;
  acumulado: AcumuladoRespuesta;
  tipos: AgrupadoRespuesta;
  colaboradores: AgrupadoRespuesta;
  detalle: DetalleRespuesta;
}

/** Indicadores > Viáticos > «Resumen General» (copia fiel de la página del PBIX, con el estilo de la imagen del nuevo diseño). */
export function ResumenGeneralPage() {
  const [meses, setMeses] = useState<MesDisponible[]>([]);
  const [periodo, setPeriodo] = useState<Periodo | null>(null);
  const [datos, setDatos] = useState<DatosPagina | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sinDatos, setSinDatos] = useState(false);

  // 1) meses disponibles; por defecto, el último mes con datos
  useEffect(() => {
    let vigente = true;
    obtenerMeses()
      .then((r) => {
        if (!vigente) return;
        setMeses(r.meses);
        if (r.por_defecto) setPeriodo(r.por_defecto);
        else setSinDatos(true);
      })
      .catch((e) => vigente && setError(mensajeError(e)));
    return () => {
      vigente = false;
    };
  }, []);

  // 2) los datos de la página para el mes elegido (las 5 consultas en paralelo)
  useEffect(() => {
    if (!periodo) return;
    let vigente = true;
    setError(null);
    Promise.all([
      obtenerTarjetas(periodo),
      obtenerAcumulado(periodo),
      obtenerTiposGasto(periodo),
      obtenerColaboradores(periodo),
      obtenerDetalle(periodo),
    ])
      .then(([tarjetas, acumulado, tipos, colaboradores, detalle]) => {
        if (vigente) setDatos({ tarjetas, acumulado, tipos, colaboradores, detalle });
      })
      .catch((e) => vigente && setError(mensajeError(e)));
    return () => {
      vigente = false;
    };
  }, [periodo]);

  return (
    <div className="ind-page">
      <div className="ind-cab">
        <div className="ind-cab-tit">
          <div className="ind-cab-ico">
            <Icono nombre="resumen" tam={26} />
          </div>
          <div style={{ minWidth: 0 }}>
            <h1>Resumen General</h1>
            <p title={datos?.tarjetas.titulo}>{datos ? datos.tarjetas.titulo : " "}</p>
          </div>
        </div>
        <FiltroAnioMes meses={meses} valor={periodo} onCambiar={setPeriodo} />
      </div>

      {error ? (
        <div className="ind-card ind-error" role="alert">
          No se pudo cargar la página: {error}
        </div>
      ) : sinDatos ? (
        <div className="ind-card ind-error" style={{ color: "var(--muted)" }}>
          Todavía no hay datos de viáticos cargados.
        </div>
      ) : (
        <>
          <div className="ind-kpis">
            {datos
              ? datos.tarjetas.tarjetas.map((t) => <TarjetaKpi key={t.clave} tarjeta={t} textoComparacion={datos.tarjetas.texto_comparacion} />)
              : [0, 1, 2, 3].map((i) => <div key={i} className="ind-card" />)}
          </div>
          <div className="ind-graficas">
            <GraficaAcumulada datos={datos?.acumulado ?? null} />
            <GraficaDona datos={datos?.tipos ?? null} />
            <GraficaBarras datos={datos?.colaboradores ?? null} />
          </div>
          <TablaDetalle datos={datos?.detalle ?? null} />
        </>
      )}
    </div>
  );
}

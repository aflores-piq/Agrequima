import { useState } from "react";
import { apiClient, mensajeError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { DashboardTheme } from "../theme/colors";

// Hover con el color de identidad FIJO del dashboard donde vive el botón
// (teal en Plaguicidas, naranja en Nutrientes) — nunca el acento general
// de la interfaz, igual que el interruptor Gráfico/Tabla (ChartCard) y
// los filtros (PowerBiFilter.tsx).
const COLOR_HOVER: Record<DashboardTheme, string> = {
  plaguicidas: "hover:bg-teal-600",
  nutrientes: "hover:bg-orange-600",
};

function IconoDescarga() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
      <path d="M10 2a.75.75 0 01.75.75v7.19l2.22-2.22a.75.75 0 111.06 1.06l-3.5 3.5a.75.75 0 01-1.06 0l-3.5-3.5a.75.75 0 111.06-1.06l2.22 2.22V2.75A.75.75 0 0110 2z" />
      <path d="M3.5 12.75a.75.75 0 01.75.75v2a.75.75 0 00.75.75h10a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0115 17.5H5a2.25 2.25 0 01-2.25-2.25v-2a.75.75 0 01.75-.75z" />
    </svg>
  );
}

function extraerNombreArchivo(contentDisposition: string | undefined, nombrePorDefecto: string): string {
  if (!contentDisposition) return nombrePorDefecto;
  const match = /filename="?([^"]+)"?/.exec(contentDisposition);
  return match ? match[1] : nombrePorDefecto;
}

/** Botón de exportar a Excel: solo se renderiza si el usuario logueado
 * tiene permiso (rol.PuedeExportar, consultado fresco en el backend en
 * cada descarga vía require_export_permission — el flag en la sesión
 * solo controla si el botón se muestra). */
export function BotonExportarExcel({
  theme,
  endpoint,
  filtros,
  nombreArchivoPorDefecto,
  etiqueta,
  className = "",
}: {
  theme: DashboardTheme;
  endpoint: string;
  filtros: Record<string, string | number | string[] | undefined>;
  nombreArchivoPorDefecto: string;
  etiqueta?: string;
  className?: string;
}) {
  const { sesion } = useAuth();
  const [descargando, setDescargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!sesion?.puedeExportar) return null;

  async function descargar() {
    setDescargando(true);
    setError(null);
    try {
      const respuesta = await apiClient.get(endpoint, {
        params: filtros,
        responseType: "blob",
      });
      const nombreArchivo = extraerNombreArchivo(
        respuesta.headers["content-disposition"],
        nombreArchivoPorDefecto
      );
      const url = window.URL.createObjectURL(respuesta.data);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = nombreArchivo;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setDescargando(false);
    }
  }

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <button
        type="button"
        onClick={descargar}
        disabled={descargando}
        title={etiqueta ? undefined : "Exportar a Excel"}
        className={`inline-flex items-center gap-1.5 rounded-tremor-small bg-surface-hover px-2 py-1 text-xs font-medium text-ink-muted transition-colors hover:text-white disabled:opacity-50 ${COLOR_HOVER[theme]}`}
      >
        <IconoDescarga />
        {etiqueta && <span>{descargando ? "Exportando…" : etiqueta}</span>}
      </button>
      {error && <span className="text-xs text-danger">{error}</span>}
    </div>
  );
}

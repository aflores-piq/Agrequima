import { useEffect, useState } from "react";
import { obtenerUltimaActualizacion } from "../../api/sistema";
import { useAuth } from "../../auth/AuthContext";
import agrequimaLogo from "../../assets/agrequima-logo.png";
import { formatFechaHoraPortada } from "../../utils/format";

/** Saludo según la hora de Guatemala (UTC-6 todo el año), tomada del reloj del navegador convertido a esa zona. */
function saludoGuatemala(): string {
  const hora =
    Number(new Intl.DateTimeFormat("en-US", { hour: "numeric", hourCycle: "h23", timeZone: "America/Guatemala" }).format(new Date())) % 24;
  if (hora >= 5 && hora < 12) return "Buenos días";
  if (hora >= 12 && hora < 19) return "Buenas tardes";
  return "Buenas noches";
}

/** Portada de /app: logo, saludo, nombre del informe y una indicación de uso. */
export function InicioPage() {
  const { sesion } = useAuth();
  // Fecha y hora de la última sincronización exitosa; sin registro (o sin respuesta) no se muestra el recuadro.
  const [actualizado, setActualizado] = useState<string | null>(null);
  useEffect(() => {
    obtenerUltimaActualizacion()
      .then((res) => setActualizado(res.ultima_actualizacion))
      .catch(() => setActualizado(null));
  }, []);
  if (!sesion?.accesoFinanciero && !sesion?.accesoImportaciones && !sesion?.accesoIndicadores) {
    return <p className="p-6 text-sm text-ink-muted">No tiene acceso a ningún módulo.</p>;
  }
  const informe = sesion.accesoFinanciero
    ? "Informe Financiero"
    : sesion.accesoImportaciones
      ? "Informe de Importaciones"
      : "Indicadores";
  const nombre = sesion.nombreCompleto || sesion.nombreUsuario;

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4 text-center">
      <img src={agrequimaLogo} alt="Agrequima" className="h-28 w-auto" />
      <h1 className="text-3xl font-semibold text-ink">
        {saludoGuatemala()}, {nombre}
      </h1>
      <p className="text-xl text-ink-muted">{informe}</p>
      <div className="h-1 w-16 rounded-full bg-emerald-500" />
      {actualizado && (
        <div className="rounded-tremor-default bg-surface px-5 py-2 text-sm text-ink ring-1 ring-line">
          Datos actualizados: {formatFechaHoraPortada(actualizado)}
        </div>
      )}
      <p className="text-sm text-ink-faint">Use el menú de la izquierda para ver cada informe.</p>
    </div>
  );
}

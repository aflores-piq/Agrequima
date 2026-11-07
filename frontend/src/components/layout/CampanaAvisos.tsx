import { useCallback, useEffect, useRef, useState } from "react";
import { marcarAvisoLeido, marcarTodosLeidos, obtenerAvisos } from "../../api/avisos";
import { mensajeError } from "../../api/client";
import { formatFechaHoraGuatemala } from "../../utils/format";
import type { Aviso } from "../../types/avisos";

const REFRESCO_MS = 60_000;

/** Campanita de avisos (arriba a la derecha). "Encendida" (color de acento y contador) cuando hay avisos sin leer; al hacer clic abre
 * el panel con la lista pendiente, LEÍDO por aviso y "Marcar todos como leídos". Cada usuario marca LEÍDO por su cuenta. Se
 * refresca al cargar, al abrir el panel y cada 60 segundos. Si falla la consulta no molesta: la campana queda como estaba. */
export function CampanaAvisos() {
  const [abierto, setAbierto] = useState(false);
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const [noLeidos, setNoLeidos] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const contenedorRef = useRef<HTMLDivElement>(null);

  const cargar = useCallback(() => {
    obtenerAvisos()
      .then((r) => {
        setAvisos(r.avisos);
        setNoLeidos(r.no_leidos);
      })
      .catch(() => {
        /* sin avisos disponibles: la campana queda como estaba */
      });
  }, []);

  useEffect(() => {
    cargar();
    const t = setInterval(cargar, REFRESCO_MS);
    return () => clearInterval(t);
  }, [cargar]);

  useEffect(() => {
    if (!abierto) return;
    function onClickFuera(e: MouseEvent) {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target as Node)) setAbierto(false);
    }
    function onTecla(e: KeyboardEvent) {
      if (e.key === "Escape") setAbierto(false);
    }
    document.addEventListener("mousedown", onClickFuera);
    document.addEventListener("keydown", onTecla);
    return () => {
      document.removeEventListener("mousedown", onClickFuera);
      document.removeEventListener("keydown", onTecla);
    };
  }, [abierto]);

  async function accion(operacion: () => Promise<unknown>) {
    setTrabajando(true);
    setError(null);
    try {
      await operacion();
      cargar();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setTrabajando(false);
    }
  }

  const encendida = noLeidos > 0;

  return (
    <div className="relative" ref={contenedorRef}>
      <button
        type="button"
        onClick={() => {
          if (!abierto) cargar();
          setAbierto(!abierto);
        }}
        aria-label={encendida ? `Avisos: ${noLeidos} sin leer` : "Avisos: no hay pendientes"}
        aria-expanded={abierto}
        title={encendida ? `${noLeidos} aviso(s) sin leer` : "Sin avisos pendientes"}
        className={`relative flex h-9 w-9 items-center justify-center rounded-full border transition-colors ${
          encendida
            ? "border-orange-400 bg-orange-500/10 text-orange-500 hover:bg-orange-500/20"
            : "border-line text-ink-muted hover:bg-surface-hover hover:text-ink"
        }`}
      >
        <svg
          viewBox="0 0 24 24"
          className="h-5 w-5"
          fill={encendida ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M6 9a6 6 0 1 1 12 0c0 5 2 6.5 2 6.5H4S6 14 6 9Z" />
          <path d="M10 19a2 2 0 0 0 4 0" fill="none" />
        </svg>
        {encendida && (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-orange-500 px-1 text-[11px] font-semibold leading-none text-white">
            {noLeidos > 99 ? "99+" : noLeidos}
          </span>
        )}
      </button>

      {abierto && (
        <div
          role="dialog"
          aria-label="Avisos"
          className="fixed inset-x-3 top-16 z-30 max-h-[70vh] overflow-hidden rounded-tremor-default border border-line bg-surface shadow-tremor-dropdown dark:shadow-dark-tremor-dropdown sm:absolute sm:inset-x-auto sm:right-0 sm:top-full sm:mt-2 sm:w-96"
        >
          <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-2.5">
            <p className="text-sm font-semibold text-ink">Avisos{encendida ? ` (${noLeidos})` : ""}</p>
            <button
              type="button"
              disabled={!encendida || trabajando}
              onClick={() => accion(marcarTodosLeidos)}
              className="text-xs font-medium text-orange-500 hover:text-orange-400 disabled:cursor-not-allowed disabled:text-ink-faint"
            >
              Marcar todos como leídos
            </button>
          </div>
          {error && (
            <p role="alert" className="bg-danger-surface px-4 py-2 text-xs text-danger">
              {error}
            </p>
          )}
          <div className="max-h-[calc(70vh-3rem)] overflow-y-auto">
            {avisos.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-ink-muted">No tienes avisos pendientes.</p>
            ) : (
              <ul className="divide-y divide-line">
                {avisos.map((a) => (
                  <li key={a.aviso_id} className="flex items-start gap-3 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] text-ink-faint">{formatFechaHoraGuatemala(a.fecha_creacion)}</p>
                      <p className="mt-0.5 break-words text-sm text-ink">{a.mensaje}</p>
                    </div>
                    <button
                      type="button"
                      disabled={trabajando}
                      onClick={() => accion(() => marcarAvisoLeido(a.aviso_id))}
                      className="shrink-0 rounded-tremor-small border border-line px-2 py-1 text-xs font-medium text-ink-muted hover:bg-surface-hover hover:text-ink disabled:opacity-50"
                    >
                      Leído
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

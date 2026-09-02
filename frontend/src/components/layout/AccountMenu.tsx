import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../../auth/AuthContext";
import { useTheme } from "../../theme/ThemeContext";
import { mensajeError } from "../../api/client";
import { cambiarMiPassword } from "../../api/auth";
import type { Tema } from "../../types/auth";

const TEMAS: { value: Tema; label: string }[] = [
  { value: "Claro", label: "Claro" },
  { value: "Oscuro", label: "Oscuro" },
];

function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "?";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

export function AccountMenu() {
  const { sesion, cerrarSesion } = useAuth();
  const { tema, actualizarPreferencia } = useTheme();
  const [abierto, setAbierto] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [errorTema, setErrorTema] = useState<string | null>(null);
  const contenedorRef = useRef<HTMLDivElement>(null);

  const [cambiandoPassword, setCambiandoPassword] = useState(false);
  const [passwordActual, setPasswordActual] = useState("");
  const [passwordNueva, setPasswordNueva] = useState("");
  const [passwordConfirmar, setPasswordConfirmar] = useState("");
  const [guardandoPassword, setGuardandoPassword] = useState(false);
  const [errorPassword, setErrorPassword] = useState<string | null>(null);
  const [exitoPassword, setExitoPassword] = useState(false);

  function cerrarFormularioPassword() {
    setCambiandoPassword(false);
    setPasswordActual("");
    setPasswordNueva("");
    setPasswordConfirmar("");
    setErrorPassword(null);
    setExitoPassword(false);
  }

  async function handleCambiarPassword(e: FormEvent) {
    e.preventDefault();
    setErrorPassword(null);
    if (passwordNueva.length < 8) {
      setErrorPassword("La contraseña nueva debe tener al menos 8 caracteres.");
      return;
    }
    if (passwordNueva !== passwordConfirmar) {
      setErrorPassword("La confirmación no coincide con la contraseña nueva.");
      return;
    }
    setGuardandoPassword(true);
    try {
      await cambiarMiPassword(passwordActual, passwordNueva);
      setPasswordActual("");
      setPasswordNueva("");
      setPasswordConfirmar("");
      setExitoPassword(true);
    } catch (error) {
      setErrorPassword(mensajeError(error));
    } finally {
      setGuardandoPassword(false);
    }
  }

  useEffect(() => {
    function onClickFuera(e: MouseEvent) {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", onClickFuera);
    return () => document.removeEventListener("mousedown", onClickFuera);
  }, []);

  if (!sesion) return null;

  const nombreMostrado = sesion.nombreCompleto ?? sesion.nombreUsuario;

  async function cambiarTema(nuevoTema: Tema) {
    if (nuevoTema === tema) return;
    setGuardando(true);
    setErrorTema(null);
    try {
      await actualizarPreferencia(nuevoTema);
    } catch (error) {
      // actualizarPreferencia ya revirtió el tema local si el PATCH falló
      // (ver ThemeContext) — aquí solo se le avisa al usuario, para que no
      // piense que el cambio se guardó cuando en realidad no se aplicó.
      setErrorTema(mensajeError(error));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="relative" ref={contenedorRef}>
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        aria-label="Cuenta"
        aria-expanded={abierto}
        className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-sm font-semibold text-white ring-2 ring-accent-subtle transition-shadow hover:ring-accent"
      >
        {iniciales(nombreMostrado)}
      </button>

      {abierto && (
        <div className="absolute right-0 top-full z-30 mt-2 w-64 overflow-hidden rounded-tremor-default border border-line bg-surface shadow-tremor-dropdown dark:shadow-dark-tremor-dropdown">
          <div className="px-4 pt-3 pb-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">Mi cuenta</p>
            <p className="mt-1 truncate text-sm font-semibold text-ink">{nombreMostrado}</p>
            {sesion.email && <p className="truncate text-xs text-ink-muted">{sesion.email}</p>}
          </div>

          <div className="border-t border-line px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">Preferencias</p>

            <p className="mb-1 mt-2 text-xs text-ink-muted">Tema</p>
            <div className="flex gap-2">
              {TEMAS.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  disabled={guardando}
                  onClick={() => cambiarTema(t.value)}
                  className={`flex-1 rounded-tremor-small border px-2 py-1 text-xs font-medium transition-colors disabled:opacity-60 ${
                    tema === t.value
                      ? "border-accent bg-accent-subtle text-accent-emphasis"
                      : "border-line text-ink-muted hover:bg-surface-hover"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            {errorTema && (
              <p role="alert" className="mt-2 text-xs text-danger">
                No se pudo guardar el tema: {errorTema}
              </p>
            )}
          </div>

          <div className="border-t border-line px-4 py-3">
            {!cambiandoPassword ? (
              <button
                type="button"
                onClick={() => setCambiandoPassword(true)}
                className="text-xs font-medium text-ink-muted hover:text-ink"
              >
                Cambiar mi contraseña
              </button>
            ) : exitoPassword ? (
              <div>
                <p className="text-xs text-emerald-500">Contraseña actualizada correctamente.</p>
                <button
                  type="button"
                  onClick={cerrarFormularioPassword}
                  className="mt-2 text-xs font-medium text-ink-muted hover:text-ink"
                >
                  Cerrar
                </button>
              </div>
            ) : (
              <form onSubmit={handleCambiarPassword} className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
                  Cambiar mi contraseña
                </p>
                <input
                  type="password"
                  placeholder="Contraseña actual"
                  value={passwordActual}
                  onChange={(e) => setPasswordActual(e.target.value)}
                  required
                  className="w-full rounded-tremor-small border border-line bg-surface px-2 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
                />
                <input
                  type="password"
                  placeholder="Contraseña nueva"
                  value={passwordNueva}
                  onChange={(e) => setPasswordNueva(e.target.value)}
                  required
                  className="w-full rounded-tremor-small border border-line bg-surface px-2 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
                />
                <input
                  type="password"
                  placeholder="Confirmar contraseña nueva"
                  value={passwordConfirmar}
                  onChange={(e) => setPasswordConfirmar(e.target.value)}
                  required
                  className="w-full rounded-tremor-small border border-line bg-surface px-2 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
                />
                {errorPassword && (
                  <p role="alert" className="text-xs text-danger">
                    {errorPassword}
                  </p>
                )}
                <div className="flex gap-2 pt-1">
                  <button
                    type="submit"
                    disabled={guardandoPassword}
                    className="flex-1 rounded-tremor-small bg-accent px-2 py-1.5 text-xs font-medium text-white transition-colors hover:opacity-90 disabled:opacity-60"
                  >
                    {guardandoPassword ? "Guardando…" : "Guardar"}
                  </button>
                  <button
                    type="button"
                    onClick={cerrarFormularioPassword}
                    disabled={guardandoPassword}
                    className="text-xs text-ink-muted hover:text-ink"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            )}
          </div>

          <div className="border-t border-line p-3">
            <button
              type="button"
              onClick={cerrarSesion}
              className="w-full rounded-tremor-small bg-danger-surface px-3 py-1.5 text-sm font-medium text-danger transition-colors hover:opacity-80"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

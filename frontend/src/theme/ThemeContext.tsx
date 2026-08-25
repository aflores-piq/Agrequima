import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { actualizarPreferencia as guardarPreferenciaEnBackend } from "../api/auth";
import type { Tema } from "../types/auth";

const CLAVE_TEMA = "agrequima_tema";

const TEMA_POR_DEFECTO: Tema = "Claro";

function aplicarAlDocumento(tema: Tema) {
  document.documentElement.classList.toggle("dark", tema === "Oscuro");
}

function leerCache(): Tema {
  return (localStorage.getItem(CLAVE_TEMA) as Tema | null) ?? TEMA_POR_DEFECTO;
}

function guardarCache(tema: Tema) {
  localStorage.setItem(CLAVE_TEMA, tema);
}

interface ThemeContextValue {
  tema: Tema;
  /** Aplica y cachea localmente sin llamar al backend — lo usa
   * AuthContext justo después de iniciar sesión, con el valor que ya
   * vino en la respuesta de /auth/login (fuente de verdad del usuario). */
  aplicarPreferencia: (tema: Tema) => void;
  /** Aplica de inmediato (optimista) y persiste en dbo.Usuarios — lo usa
   * el menú de cuenta cuando el usuario cambia el tema. */
  actualizarPreferencia: (tema: Tema) => Promise<void>;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [tema, setTema] = useState<Tema>(() => {
    const cache = leerCache();
    aplicarAlDocumento(cache);
    return cache;
  });

  const aplicarPreferencia = useCallback((nuevoTema: Tema) => {
    aplicarAlDocumento(nuevoTema);
    guardarCache(nuevoTema);
    setTema(nuevoTema);
  }, []);

  const actualizarPreferencia = useCallback(
    async (nuevoTema: Tema) => {
      const temaAnterior = tema;
      aplicarPreferencia(nuevoTema);
      try {
        await guardarPreferenciaEnBackend(nuevoTema);
      } catch (error) {
        // Si el PATCH no se confirma, no podemos dejar el estado local
        // (y su caché en localStorage) en el tema nuevo: dbo.Usuarios.Tema
        // se queda con el valor anterior, y el próximo login — que confía
        // en la BD — "revertiría" el tema sin explicación aparente. Se
        // revierte aquí mismo y se deja que el error suba para que la UI
        // lo muestre (ver AccountMenu.cambiarTema).
        aplicarPreferencia(temaAnterior);
        throw error;
      }
    },
    [aplicarPreferencia, tema]
  );

  const value = useMemo(
    () => ({ tema, aplicarPreferencia, actualizarPreferencia }),
    [tema, aplicarPreferencia, actualizarPreferencia]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme debe usarse dentro de ThemeProvider");
  return ctx;
}

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { login as loginRequest } from "../api/auth";
import { borrarSesion, guardarSesion, leerSesion } from "../api/client";
import type { Sesion } from "../api/client";
import { useTheme } from "../theme/ThemeContext";

interface AuthContextValue {
  sesion: Sesion | null;
  iniciarSesion: (nombreUsuario: string, password: string) => Promise<void>;
  cerrarSesion: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [sesion, setSesion] = useState<Sesion | null>(() => leerSesion());
  const { aplicarPreferencia } = useTheme();

  const iniciarSesion = useCallback(
    async (nombreUsuario: string, password: string) => {
      const { access_token, tema } = await loginRequest(nombreUsuario, password);
      guardarSesion(access_token);
      setSesion(leerSesion());
      // Tema guardado en dbo.Usuarios se aplica de inmediato al iniciar
      // sesión, sin depender de lo último cacheado en este navegador.
      aplicarPreferencia(tema);
    },
    [aplicarPreferencia]
  );

  const cerrarSesion = useCallback(() => {
    borrarSesion();
    setSesion(null);
  }, []);

  const value = useMemo(() => ({ sesion, iniciarSesion, cerrarSesion }), [sesion, iniciarSesion, cerrarSesion]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}

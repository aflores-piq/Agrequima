import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { aceptarAvisoLegal as aceptarAvisoLegalRequest, login as loginRequest } from "../api/auth";
import {
  avisoLegalYaAceptado,
  borrarSesion,
  guardarSesion,
  leerSesion,
  marcarAvisoLegalAceptado,
} from "../api/client";
import type { Sesion } from "../api/client";
import { useTheme } from "../theme/ThemeContext";

interface AuthContextValue {
  sesion: Sesion | null;
  /** true = todavía no aceptó el aviso legal (ver RequireRole, que
   * bloquea el acceso al dashboard mientras esto sea true). */
  avisoLegalPendiente: boolean;
  iniciarSesion: (nombreUsuario: string, password: string) => Promise<void>;
  aceptarAvisoLegal: () => Promise<void>;
  cerrarSesion: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [sesion, setSesion] = useState<Sesion | null>(() => leerSesion());
  // Al cargar la página con una sesión ya guardada (F5), solo hace falta
  // volver a pedir el aviso si NO hay sesión (nada que proteger) o si
  // hay sesión pero la bandera local todavía no está puesta -- ver
  // AVISO_LEGAL_STORAGE_KEY en client.ts para por qué es una bandera
  // aparte del JWT.
  const [avisoLegalPendiente, setAvisoLegalPendiente] = useState<boolean>(
    () => !!leerSesion() && !avisoLegalYaAceptado()
  );
  const { aplicarPreferencia } = useTheme();

  const iniciarSesion = useCallback(
    async (nombreUsuario: string, password: string) => {
      const { access_token, tema, aviso_legal_aceptado } = await loginRequest(nombreUsuario, password);
      guardarSesion(access_token);
      setSesion(leerSesion());
      // Tema guardado en dbo.Usuarios se aplica de inmediato al iniciar
      // sesión, sin depender de lo último cacheado en este navegador.
      aplicarPreferencia(tema);
      if (aviso_legal_aceptado) {
        marcarAvisoLegalAceptado();
        setAvisoLegalPendiente(false);
      } else {
        setAvisoLegalPendiente(true);
      }
    },
    [aplicarPreferencia]
  );

  const aceptarAvisoLegal = useCallback(async () => {
    await aceptarAvisoLegalRequest();
    marcarAvisoLegalAceptado();
    setAvisoLegalPendiente(false);
  }, []);

  const cerrarSesion = useCallback(() => {
    borrarSesion();
    setSesion(null);
    setAvisoLegalPendiente(false);
  }, []);

  const value = useMemo(
    () => ({ sesion, avisoLegalPendiente, iniciarSesion, aceptarAvisoLegal, cerrarSesion }),
    [sesion, avisoLegalPendiente, iniciarSesion, aceptarAvisoLegal, cerrarSesion]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}

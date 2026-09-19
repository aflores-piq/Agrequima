import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, Card, TextInput, Title, Text } from "@tremor/react";
import { useAuth } from "../auth/AuthContext";
import { destinoPorRol } from "../auth/RequireRole";
import { mensajeError } from "../api/client";
import agrequimaPortada from "../assets/agrequima-portada.jpg";

export function LoginPage() {
  const { sesion, iniciarSesion } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [nombreUsuario, setNombreUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (sesion) {
      navigate(destinoPorRol(sesion.rol), { replace: true });
    }
  }, [sesion, navigate]);

  if (sesion) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      await iniciarSesion(nombreUsuario, password);
      // Si venía rebotado de una ruta protegida, volver ahí. Si fue un
      // login directo (sin "desde"), el useEffect de arriba redirige
      // solo apenas "sesion" se actualiza, usando destinoPorRol() —
      // misma lógica en los dos casos, sin un "/app" fijo de por medio.
      const desde = (location.state as { desde?: string } | null)?.desde;
      if (desde) navigate(desde, { replace: true });
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargando(false);
    }
  }

  return (
    <div
      className="relative flex min-h-screen flex-col items-center px-4"
      style={{
        backgroundImage: `url(${agrequimaPortada})`,
        // "cover" (no dos porcentajes independientes de ancho/alto):
        // eso estiraba la imagen fuera de su relación de aspecto nativa
        // (1536x1024) cada vez que la ventana no coincidía exactamente
        // con esa proporción -- el logo y el eslogan se veían
        // "aplastados". "cover" siempre recorta, nunca deforma; con
        // backgroundPosition "center top" se sigue viendo el logo
        // completo en la parte de arriba, igual que antes.
        backgroundSize: "cover",
        backgroundPosition: "center top",
        backgroundRepeat: "no-repeat",
      }}
    >
      <div
        aria-hidden="true"
        style={{ height: "clamp(16px, calc(49.25vh - 314px), 260px)" }}
      />
      {/* Degradado oscuro semitransparente encima del fondo (la portada
       * oficial de Agrequima, la misma que se usaba en Power BI): solo
       * detrás de la tarjeta, arriba — el logo del ave/hojas y el
       * eslogan quedan visibles completos y sin oscurecer más abajo. */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/65 via-black/15 to-transparent" />

      <Card className="relative z-10 w-full max-w-sm bg-surface ring-1 ring-line">
        <Title className="text-ink">Agrequima</Title>
        <Text className="text-ink-muted">Importaciones de plaguicidas y nutrientes</Text>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <Text className="mb-1 text-ink-muted">Usuario</Text>
            <TextInput
              value={nombreUsuario}
              onValueChange={setNombreUsuario}
              placeholder="nombre.usuario"
              autoFocus
              required
            />
          </div>
          <div>
            <Text className="mb-1 text-ink-muted">Contraseña</Text>
            <TextInput
              type="password"
              value={password}
              onValueChange={setPassword}
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <p role="alert" className="rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" loading={cargando} disabled={cargando}>
            Ingresar
          </Button>
        </form>
      </Card>
    </div>
  );
}

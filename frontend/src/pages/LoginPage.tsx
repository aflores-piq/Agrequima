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
  // Aviso legal: se muestra tapando toda la pantalla al entrar a /login,
  // antes de poder escribir usuario/contraseña -- se acepta una vez por
  // carga de página (estado local, sin persistir en base de datos: no
  // existe hoy ningún mecanismo similar de "confirmación" que reutilizar,
  // así que se vuelve a mostrar en cada acceso, tal como se pidió).
  const [avisoAceptado, setAvisoAceptado] = useState(false);

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

      {/* Aviso legal: tapa toda la pantalla (fondo casi opaco, z-index por
          encima de la tarjeta de login) hasta que se hace clic en el botón
          -- recién ahí se desmonta y queda accesible el formulario de
          usuario/contraseña de abajo. Texto exacto pedido por el cliente,
          sin resumir ni parafrasear. */}
      {!avisoAceptado && (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/80 px-4">
          <Card className="w-full max-w-lg bg-surface ring-1 ring-line">
            <Title className="text-ink">AVISO LEGAL Y CONDICIONES DE USO</Title>
            <div className="mt-4 space-y-3 text-sm text-ink-muted">
              <p>
                La información contenida en esta plataforma es de uso exclusivo de los asociados de AGREQUIMA y se
                proporciona con fines informativos, estadísticos y de análisis sectorial.
              </p>
              <p>
                El usuario se obliga a utilizarla de manera lícita, responsable e independiente, quedando
                expresamente prohibido utilizarla, directa o indirectamente, para fines de competencia desleal,
                prácticas anticompetitivas, coordinación o fijación de precios, condiciones comerciales, clientes,
                mercados, volúmenes, estrategias comerciales o cualquier otra conducta contraria a la legislación
                guatemalteca.
              </p>
              <p>
                AGREQUIMA no será responsable por la interpretación, reproducción, divulgación o utilización
                indebida que el usuario o terceros hagan de la información, siendo el usuario exclusivamente
                responsable por el uso que realice de la misma.
              </p>
              <p>
                Al hacer clic en "ACEPTO", el usuario declara haber leído y aceptado estas condiciones y se
                compromete a utilizar la información de conformidad con las leyes de la República de Guatemala,
                incluyendo la normativa aplicable en materia de competencia y competencia desleal.
              </p>
            </div>
            <Button type="button" className="mt-6 w-full" onClick={() => setAvisoAceptado(true)}>
              ACEPTO Y CONTINUAR
            </Button>
          </Card>
        </div>
      )}

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

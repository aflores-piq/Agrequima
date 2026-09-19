import { useState } from "react";
import { Button, Card, Title } from "@tremor/react";
import { useAuth } from "../auth/AuthContext";
import { mensajeError } from "../api/client";

/** Aviso legal y condiciones de uso: tapa toda la pantalla DESPUÉS de
 * iniciar sesión (ver RequireRole, que lo muestra en vez de las rutas
 * protegidas mientras avisoLegalPendiente sea true), bloqueando el
 * acceso al dashboard hasta que se hace clic en el botón. Se muestra
 * una sola vez por usuario -- ver AuthContext.aceptarAvisoLegal() y
 * dbo.Usuarios.AvisoLegalAceptado. Texto exacto pedido por el cliente,
 * sin resumir ni parafrasear. */
export function AvisoLegalOverlay() {
  const { aceptarAvisoLegal, cerrarSesion } = useAuth();
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAceptar() {
    setError(null);
    setEnviando(true);
    try {
      await aceptarAvisoLegal();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/80 px-4">
      <Card className="w-full max-w-lg bg-surface ring-1 ring-line">
        <Title className="text-ink">AVISO LEGAL Y CONDICIONES DE USO</Title>
        <div className="mt-4 space-y-3 text-sm text-ink-muted">
          <p>
            La información contenida en esta plataforma es de uso exclusivo de los asociados de AGREQUIMA y se
            proporciona con fines informativos, estadísticos y de análisis sectorial.
          </p>
          <p>
            El usuario se obliga a utilizarla de manera lícita, responsable e independiente, quedando expresamente
            prohibido utilizarla, directa o indirectamente, para fines de competencia desleal, prácticas
            anticompetitivas, coordinación o fijación de precios, condiciones comerciales, clientes, mercados,
            volúmenes, estrategias comerciales o cualquier otra conducta contraria a la legislación guatemalteca.
          </p>
          <p>
            AGREQUIMA no será responsable por la interpretación, reproducción, divulgación o utilización indebida
            que el usuario o terceros hagan de la información, siendo el usuario exclusivamente responsable por el
            uso que realice de la misma.
          </p>
          <p>
            Al hacer clic en "ACEPTO", el usuario declara haber leído y aceptado estas condiciones y se compromete
            a utilizar la información de conformidad con las leyes de la República de Guatemala, incluyendo la
            normativa aplicable en materia de competencia y competencia desleal.
          </p>
        </div>

        {error && (
          <p role="alert" className="mt-4 rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}

        <Button type="button" className="mt-6 w-full" loading={enviando} disabled={enviando} onClick={handleAceptar}>
          ACEPTO Y CONTINUAR
        </Button>
        <button
          type="button"
          onClick={cerrarSesion}
          className="mt-3 w-full text-center text-xs text-ink-faint hover:text-ink-muted"
        >
          Cerrar sesión
        </button>
      </Card>
    </div>
  );
}

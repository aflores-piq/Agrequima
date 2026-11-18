import { fechaDMA, num2 } from "./formato";
import type { DetalleRespuesta } from "./tipos";

// Ancho de las columnas (suma 100 %): Fecha Documento, Fecha Inicial, Fecha Final, Técnico, Tipo de Gasto, Motivo,
// Total Factura, Proveedor.
const ANCHOS = [11.5, 11, 11, 17, 12, 10.5, 10.5, 16.5];

/** Tabla de detalle de la página «Resumen General» con las columnas exactas del PBIX. Encabezado y fila «Total» fijos;
 * las filas se desplazan dentro de la tarjeta. */
export function TablaDetalle({ datos }: { datos: DetalleRespuesta | null }) {
  const filas = datos?.filas ?? [];
  return (
    <section className="ind-card ind-tabla" aria-label="Detalle de viáticos">
      <div className="ind-tabla-scroll">
        <table>
          <colgroup>
            {ANCHOS.map((a, i) => (
              <col key={i} style={{ width: `${a}%` }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              <th>Fecha Documento</th>
              <th>Fecha Inicial</th>
              <th>Fecha Final</th>
              <th>Técnico</th>
              <th>Tipo de Gasto</th>
              <th>Motivo</th>
              <th>Total Factura</th>
              <th>Proveedor</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f, i) => (
              <tr key={i}>
                <td className="fecha">{fechaDMA(f.fecha_documento)}</td>
                <td className="fecha">{fechaDMA(f.fecha_inicial)}</td>
                <td className="fecha">{fechaDMA(f.fecha_final)}</td>
                <td title={f.tecnico ?? ""}>{f.tecnico}</td>
                <td title={f.tipo_gasto ?? ""}>{f.tipo_gasto}</td>
                <td title={f.motivo ?? ""}>{f.motivo}</td>
                <td className="num">{num2(f.total_factura)}</td>
                <td title={f.proveedor ?? ""}>{f.proveedor}</td>
              </tr>
            ))}
            {datos && filas.length === 0 && (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", height: 64 }}>
                  Sin registros para el mes elegido
                </td>
              </tr>
            )}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={6}>Total</td>
              <td className="num">{datos ? num2(datos.total_factura) : ""}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}

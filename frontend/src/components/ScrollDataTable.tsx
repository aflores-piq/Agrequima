import type { ReactNode, UIEvent } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "@tremor/react";
import type { Columna } from "./SimpleDataTable";

const UMBRAL_PX = 150;

/** Panel de altura fija con scroll interno: al acercarse al final carga
 * automáticamente el siguiente bloque de filas (estilo Power BI), sin
 * botones "Anterior/Siguiente" ni "página X de Y". */
export function ScrollDataTable<T>({
  columnas,
  filas,
  total,
  cargandoMas,
  hayMas,
  onCargarMas,
  getKey,
  altura = "500px",
}: {
  columnas: Columna<T>[];
  filas: T[];
  total: number;
  cargandoMas: boolean;
  hayMas: boolean;
  onCargarMas: () => void;
  getKey: (row: T, i: number) => string | number;
  altura?: string;
}): ReactNode {
  if (filas.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  function onScroll(e: UIEvent<HTMLDivElement>) {
    const el = e.currentTarget;
    const cercaDelFinal = el.scrollHeight - el.scrollTop - el.clientHeight < UMBRAL_PX;
    if (cercaDelFinal && hayMas && !cargandoMas) {
      onCargarMas();
    }
  }

  return (
    <div>
      {/* overflow-visible en <Table>: Tremor envuelve internamente la tabla
          en su PROPIO div con overflow-auto (hardcodeado en su código
          fuente) — eso crea un SEGUNDO contenedor de scroll anidado
          dentro de este. Con altura fija + scroll vertical aquí afuera,
          la tabla interna mide su alto TOTAL sin recortar (todas las
          filas), así que la barra de scroll horizontal de Tremor queda
          pegada al fondo de ese alto completo — muy por debajo de la
          ventana visible de 500px, nunca alcanzable sin antes scrollear
          verticalmente hasta el final. overflow-visible anula ese
          segundo contenedor para que el único que scrollea (en ambos
          ejes a la vez) sea este de afuera, con su barra horizontal
          siempre pegada al borde inferior de la ventana visible. */}
      <div className="overflow-x-auto overflow-y-auto" style={{ maxHeight: altura }} onScroll={onScroll}>
        <Table className="overflow-visible">
          <TableHead>
            <TableRow>
              {columnas.map((c) => (
                <TableHeaderCell
                  key={c.header}
                  className={`sticky top-0 z-10 bg-surface ${c.align === "right" ? "text-right" : ""}`}
                >
                  {c.header}
                </TableHeaderCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {filas.map((fila, i) => (
              <TableRow key={getKey(fila, i)} className="hover:bg-surface-hover/60">
                {columnas.map((c) => (
                  <TableCell key={c.header} className={c.align === "right" ? "text-right" : undefined}>
                    {c.accessor(fila)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <p className="mt-2 text-center text-xs text-ink-faint">
        {cargandoMas
          ? "Cargando más filas…"
          : hayMas
            ? `Mostrando ${filas.length} de ${total} — desplázate para ver más`
            : `${filas.length} de ${filas.length} filas`}
      </p>
    </div>
  );
}

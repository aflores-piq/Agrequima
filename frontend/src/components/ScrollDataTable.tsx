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
      <div className="overflow-x-auto overflow-y-auto" style={{ maxHeight: altura }} onScroll={onScroll}>
        <Table>
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

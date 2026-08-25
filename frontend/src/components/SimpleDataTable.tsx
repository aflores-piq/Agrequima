import type { ReactNode } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "@tremor/react";

export interface Columna<T> {
  header: string;
  accessor: (row: T) => ReactNode;
  align?: "left" | "right";
}

/** Tabla simple usada como vista alternativa accesible de un gráfico. */
export function SimpleDataTable<T>({
  columnas,
  filas,
  getKey,
}: {
  columnas: Columna<T>[];
  filas: T[];
  getKey: (row: T, i: number) => string | number;
}) {
  if (filas.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  return (
    <div className="max-h-80 overflow-y-auto overflow-x-auto">
      <Table>
        <TableHead>
          <TableRow>
            {columnas.map((c) => (
              <TableHeaderCell key={c.header} className={c.align === "right" ? "text-right" : undefined}>
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
  );
}

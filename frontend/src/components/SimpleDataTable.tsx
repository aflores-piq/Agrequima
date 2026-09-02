import type { ReactNode } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "@tremor/react";

export interface Columna<T> {
  header: string;
  accessor: (row: T, indice?: number) => ReactNode;
  align?: "left" | "right";
  /** Clase Tailwind de ancho máximo (ej. "max-w-[180px]"): trunca el
   * contenido con "…" en vez de forzar scroll horizontal en la tabla.
   * Solo se aplica cuando el llamador la define (no cambia columnas que
   * ya no tenían este problema). */
  ancho?: string;
}

/** Tabla simple usada como vista alternativa accesible de un gráfico. */
export function SimpleDataTable<T>({
  columnas,
  filas,
  getKey,
  sinLimiteAltura,
  compacto,
}: {
  columnas: Columna<T>[];
  filas: T[];
  getKey: (row: T, i: number) => string | number;
  /** Usa el alto real del contenedor (h-full) en vez del tope fijo de
   * max-h-72 — para tablas con más filas de las que max-h-72 alcanza a
   * mostrar. Sigue teniendo scroll vertical de seguridad (overflow-y-
   * auto): dentro de un ChartCard el contenedor tiene flex-1, así que su
   * alto real depende de la fila del grid (ej. la tarjeta vecina de 20
   * elementos) — si el contenido de la tabla no cupiera ahí, debe hacer
   * scroll interno, NUNCA estirar la tarjeta (eso arrastraría también a
   * la tarjeta vecina vía CSS Grid align-items:stretch). */
  sinLimiteAltura?: boolean;
  /** Padding y tipografía reducidos (mismo criterio que RankingTable):
   * cuando hay muchas columnas de texto libre y necesitan caber completas
   * sin scroll horizontal, achicar el padding/fuente de la celda libera
   * más ancho real que cualquier ajuste de `ancho` por columna. `true` usa
   * el padding compacto estándar; un string reemplaza esa clase por
   * completo (para una tabla con más columnas que necesita apretar más,
   * sin afectar a otras tablas que ya usan `compacto` normal). */
  compacto?: boolean | string;
}) {
  if (filas.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  const celda = typeof compacto === "string" ? compacto : compacto ? "px-1 py-1.5 text-xs" : undefined;

  return (
    <div className={sinLimiteAltura ? "h-full overflow-y-auto overflow-x-auto" : "h-full max-h-72 overflow-y-auto overflow-x-auto"}>
      <Table>
        <TableHead>
          <TableRow>
            {columnas.map((c) => (
              <TableHeaderCell
                key={c.header}
                className={[celda, c.align === "right" ? "text-right" : undefined].filter(Boolean).join(" ") || undefined}
              >
                {c.header}
              </TableHeaderCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {filas.map((fila, i) => (
            <TableRow key={getKey(fila, i)} className="hover:bg-surface-hover/60">
              {columnas.map((c) => {
                const valor = c.accessor(fila, i);
                return (
                  <TableCell
                    key={c.header}
                    className={[
                      celda,
                      c.align === "right" ? "text-right" : undefined,
                      c.ancho ? `${c.ancho} overflow-hidden text-ellipsis` : undefined,
                    ]
                      .filter(Boolean)
                      .join(" ") || undefined}
                    title={c.ancho && typeof valor === "string" ? valor : undefined}
                  >
                    {valor}
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

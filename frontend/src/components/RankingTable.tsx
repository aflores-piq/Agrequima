import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "@tremor/react";
import type { ResumenItem } from "../types/dashboard";
import { formatNumber, formatPercent, formatUSDAbrev } from "../utils/format";

/** Tabla numerada (#, nombre, conteo, CIF USD, %) — reemplaza un gráfico
 * de barras horizontal cuando se prefiere ver el ranking como tabla.
 * Filas compactas (padding/tipografía reducidos) para que las 20 filas
 * quepan sin scroll interno, igual que en Power BI — nunca se oculta
 * contenido detrás de un scroll para "ahorrar" alto de fila. */
export function RankingTable({
  filas,
  etiquetaColumna,
  etiquetaConteo,
}: {
  filas: ResumenItem[];
  etiquetaColumna: string;
  etiquetaConteo: string;
}) {
  if (filas.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  const celda = "py-1 text-xs";

  return (
    <div className="h-full overflow-x-auto">
      <Table>
        <TableHead>
          <TableRow>
            <TableHeaderCell className={`w-8 ${celda}`}>#</TableHeaderCell>
            <TableHeaderCell className={celda}>{etiquetaColumna}</TableHeaderCell>
            <TableHeaderCell className={`text-right ${celda}`}>{etiquetaConteo}</TableHeaderCell>
            <TableHeaderCell className={`text-right ${celda}`}>CIF USD</TableHeaderCell>
            <TableHeaderCell className={`text-right ${celda}`}>%</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filas.map((fila, i) => (
            <TableRow
              key={fila.etiqueta}
              className="hover:bg-surface-hover/60"
              title={`${fila.etiqueta}: ${formatUSDAbrev(fila.cif_usd)} (${formatPercent(fila.porcentaje_del_total)})`}
            >
              <TableCell className={`text-ink-faint ${celda}`}>{i + 1}</TableCell>
              <TableCell className={`max-w-[180px] truncate ${celda}`}>{fila.etiqueta}</TableCell>
              <TableCell className={`text-right ${celda}`}>{formatNumber(fila.transacciones)}</TableCell>
              <TableCell className={`text-right ${celda}`}>{formatUSDAbrev(fila.cif_usd)}</TableCell>
              <TableCell className={`text-right ${celda}`}>{formatPercent(fila.porcentaje_del_total)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

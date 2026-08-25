import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "@tremor/react";
import type { ResumenItem } from "../types/dashboard";
import { formatNumber, formatPercent, formatUSDAbrev } from "../utils/format";

/** Tabla numerada (#, nombre, conteo, CIF USD, %) — reemplaza un gráfico
 * de barras horizontal cuando se prefiere ver el ranking como tabla. */
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

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHead>
          <TableRow>
            <TableHeaderCell className="w-10">#</TableHeaderCell>
            <TableHeaderCell>{etiquetaColumna}</TableHeaderCell>
            <TableHeaderCell className="text-right">{etiquetaConteo}</TableHeaderCell>
            <TableHeaderCell className="text-right">CIF USD</TableHeaderCell>
            <TableHeaderCell className="text-right">%</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filas.map((fila, i) => (
            <TableRow
              key={fila.etiqueta}
              className="hover:bg-surface-hover/60"
              title={`${fila.etiqueta}: ${formatUSDAbrev(fila.cif_usd)} (${formatPercent(fila.porcentaje_del_total)})`}
            >
              <TableCell className="text-ink-faint">{i + 1}</TableCell>
              <TableCell>{fila.etiqueta}</TableCell>
              <TableCell className="text-right">{formatNumber(fila.transacciones)}</TableCell>
              <TableCell className="text-right">{formatUSDAbrev(fila.cif_usd)}</TableCell>
              <TableCell className="text-right">{formatPercent(fila.porcentaje_del_total)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

import { ProgressBar, Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "@tremor/react";
import type { ResumenItem } from "../types/dashboard";
import { formatNumber, formatPercent, formatUSD } from "../utils/format";

export function ResumenTable({
  filas,
  etiquetaColumna,
  accentColor,
}: {
  filas: ResumenItem[];
  etiquetaColumna: string;
  /** Nombre de color Tremor, ej. "teal" o "orange". */
  accentColor: string;
}) {
  if (filas.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  return (
    <div className="max-h-96 overflow-y-auto overflow-x-auto">
      <Table>
        <TableHead>
          <TableRow>
            <TableHeaderCell>{etiquetaColumna}</TableHeaderCell>
            <TableHeaderCell className="text-right">Transacciones</TableHeaderCell>
            <TableHeaderCell className="text-right">CIF USD</TableHeaderCell>
            <TableHeaderCell>% del total</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filas.map((fila) => (
            <TableRow
              key={fila.etiqueta}
              className="hover:bg-surface-hover/60"
              title={`${fila.etiqueta}: ${formatUSD(fila.cif_usd)} (${formatPercent(fila.porcentaje_del_total)})`}
            >
              <TableCell className="max-w-xs truncate">{fila.etiqueta}</TableCell>
              <TableCell className="text-right">{formatNumber(fila.transacciones)}</TableCell>
              <TableCell className="text-right">{formatUSD(fila.cif_usd)}</TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <ProgressBar value={fila.porcentaje_del_total} color={accentColor} className="w-28" />
                  <span className="w-12 text-xs text-ink-muted">{formatPercent(fila.porcentaje_del_total)}</span>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

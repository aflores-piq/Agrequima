import { Button } from "@tremor/react";
import type { Columna } from "./SimpleDataTable";
import { SimpleDataTable } from "./SimpleDataTable";
import { formatNumber } from "../utils/format";

export function PaginatedTable<T>({
  columnas,
  filas,
  total,
  pagina,
  tamanoPagina,
  onCambiarPagina,
  getKey,
}: {
  columnas: Columna<T>[];
  filas: T[];
  total: number;
  pagina: number;
  tamanoPagina: number;
  onCambiarPagina: (pagina: number) => void;
  getKey: (row: T, i: number) => string | number;
}) {
  const totalPaginas = Math.max(1, Math.ceil(total / tamanoPagina));

  return (
    <div>
      <SimpleDataTable columnas={columnas} filas={filas} getKey={getKey} />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-ink-muted">
        <span>
          {formatNumber(total)} filas — página {pagina} de {formatNumber(totalPaginas)}
        </span>
        <div className="flex gap-2">
          <Button
            size="xs"
            variant="secondary"
            disabled={pagina <= 1}
            onClick={() => onCambiarPagina(pagina - 1)}
          >
            Anterior
          </Button>
          <Button
            size="xs"
            variant="secondary"
            disabled={pagina >= totalPaginas}
            onClick={() => onCambiarPagina(pagina + 1)}
          >
            Siguiente
          </Button>
        </div>
      </div>
    </div>
  );
}

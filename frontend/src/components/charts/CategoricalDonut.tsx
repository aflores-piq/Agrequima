import { DonutChart, Legend } from "@tremor/react";
import { colorParaCategoria, ordenarCategorias } from "../../theme/colors";
import { formatUSD } from "../../utils/format";
import type { RankingItem } from "../../types/dashboard";

/** Dona de diversificación por categoría (tipo de aplicación). El orden
 * y el color de cada categoría son FIJOS (theme/colors.ts) — nunca se
 * reasignan dinámicamente según qué categorías trae el filtro activo. */
export function CategoricalDonut({ data }: { data: RankingItem[] }) {
  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  const categorias = ordenarCategorias(data.map((d) => d.etiqueta));
  const dataOrdenada = categorias
    .map((c) => data.find((d) => d.etiqueta === c))
    .filter((d): d is RankingItem => d !== undefined);
  const colores = categorias.map(colorParaCategoria);

  return (
    <div>
      <DonutChart
        data={dataOrdenada}
        category="cif_usd"
        index="etiqueta"
        colors={colores}
        valueFormatter={formatUSD}
        className="h-64"
      />
      <Legend categories={categorias} colors={colores} className="mt-3 justify-center" />
    </div>
  );
}

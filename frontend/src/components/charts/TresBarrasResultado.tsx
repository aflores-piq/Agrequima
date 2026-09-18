import {
  Bar,
  BarChart as RechartsBarChart,
  Cell,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatQ } from "../../utils/format";
import { FINANCIERO_SURFACE } from "../TablaGrupoExpandible";

// Colores reales leídos de las capturas del reporte viejo (no
// inventados): Ingresos = #3f6f6b, Egresos = #e87471, Resultado =
// #507eaa -- mismos 3 colores en los 2 gráficos de esta página (mes
// filtrado y acumulado del año), cada uno de un solo período (por eso
// 3 barras de un color fijo cada una, no una serie por año).
const COLOR_INGRESOS = "#3f6f6b";
const COLOR_EGRESOS = "#e87471";
const COLOR_RESULTADO = "#507eaa";

/** 3 barras de un solo período: Ingresos netos / Egresos / Resultado --
 * páginas 1 (mes filtrado y acumulado del año) del dashboard Financiero. */
export function TresBarrasResultado({
  ingresos,
  egresos,
  resultado,
  altura = 288,
}: {
  ingresos: number;
  egresos: number;
  resultado: number;
  altura?: number;
}) {
  // La barra de Egresos usa el VALOR ABSOLUTO para la altura (misma
  // escala que Ingresos/Resultado, igual que en la captura real) --
  // solo la etiqueta de encima muestra el signo negativo (egreso =
  // salida de dinero), vía `etiqueta` por separado de `monto`.
  const data = [
    { categoria: "Ingresos netos", monto: ingresos, etiqueta: ingresos, color: COLOR_INGRESOS },
    { categoria: "Egresos", monto: Math.abs(egresos), etiqueta: -Math.abs(egresos), color: COLOR_EGRESOS },
    { categoria: "Resultado", monto: resultado, etiqueta: resultado, color: COLOR_RESULTADO },
  ];

  return (
    // Envoltorio propio w-full/h-full: Recharts mide su contenedor
    // inmediato una sola vez al montar (ver RankingBarChart.tsx) -- sin
    // este div, si el ancho heredado por flex/grid todavía no se
    // resolvió en ese instante, el SVG puede quedar en 0px sin que un
    // resize posterior lo corrija.
    <div className="h-full w-full" style={{ minHeight: altura }}>
      <ResponsiveContainer width="100%" height="100%" minHeight={altura}>
        <RechartsBarChart data={data} margin={{ top: 28, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--color-line))" vertical={false} />
        <XAxis dataKey="categoria" stroke="rgb(var(--color-ink))" fontSize={12} tickLine={false} />
        <YAxis
          tickFormatter={(v: number) => formatQ(v)}
          stroke="rgb(var(--color-ink))"
          fontSize={12}
          tickLine={false}
          width={95}
        />
        <Tooltip
          cursor={{ fill: "rgb(var(--color-ink-faint) / 0.08)" }}
          contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
          labelStyle={{ color: "rgb(var(--color-ink))" }}
          itemStyle={{ color: "rgb(var(--color-ink))" }}
          formatter={(_value: number, _name: string, item: any) => formatQ(item?.payload?.etiqueta ?? _value)}
        />
        <Bar dataKey="monto" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.categoria} fill={d.color} />
          ))}
          <LabelList
            dataKey="etiqueta"
            position="top"
            formatter={(v: number) => formatQ(v)}
            fill="rgb(var(--color-ink))"
            fontSize={14}
            fontWeight={600}
          />
        </Bar>
      </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}

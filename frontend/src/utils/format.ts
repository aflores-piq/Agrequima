const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const qFormatter = new Intl.NumberFormat("es-GT", {
  style: "currency",
  currency: "GTQ",
  maximumFractionDigits: 0,
});

const numberFormatter = new Intl.NumberFormat("es-GT");

export function formatUSD(v: number): string {
  return usdFormatter.format(v);
}

export function formatQ(v: number): string {
  return qFormatter.format(v);
}

export function formatNumber(v: number): string {
  return numberFormatter.format(v);
}

export function formatPercent(v: number): string {
  return `${v.toFixed(1)}%`;
}

function abreviarNumero(valor: number): string {
  const abs = Math.abs(valor);
  const signo = valor < 0 ? "-" : "";
  if (abs >= 1e9) return `${signo}${(abs / 1e9).toFixed(2)} mil M`;
  if (abs >= 1e6) return `${signo}${(abs / 1e6).toFixed(2)} mill`;
  if (abs >= 1e3) return `${signo}${(abs / 1e3).toFixed(2)} mil`;
  return `${signo}${abs.toFixed(0)}`;
}

/** Formato abreviado para montos grandes en tarjetas KPI y etiquetas de
 * gráficos, ej. "$137.82 mill", "$1.05 mil M". */
export function formatUSDAbrev(v: number): string {
  return `$${abreviarNumero(v)}`;
}

/** Igual que formatUSDAbrev pero con el símbolo de Quetzales, ej. "Q1.05 mil M". */
export function formatQAbrev(v: number): string {
  return `Q${abreviarNumero(v)}`;
}

/** "$43.6M" / "$633.4K" — un decimal, con abreviatura de una letra (M/K)
 * en vez de "mil"/"mill": formato corto calcado del spec de Power BI,
 * usado en la dona de aplicación y en las etiquetas de valor por barra
 * de RankingBarChart — mucho más angosto que formatUSDAbrev, necesario
 * porque ahí compite por espacio horizontal con el nombre y la barra. */
export function formatUSDCorto(valor: number): string {
  if (valor >= 1_000_000) return `$${(valor / 1_000_000).toFixed(1)}M`;
  return `$${(valor / 1_000).toFixed(1)}K`;
}

export const MESES = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
];

export const MESES_LARGOS = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

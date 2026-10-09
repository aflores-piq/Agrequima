const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

// currencySign:"accounting" -- formato contable real de Intl: negativos
// entre paréntesis en vez de con signo "-" ("($10,239,048)" en vez de
// "-$10,239,048"), usado en las tablas de "Importaciones" del
// Financiero (Variación/VAR), calcado del formato real del .pbix.
const usdContableFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
  currencySign: "accounting",
});

const usd2Formatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const numberFormatter = new Intl.NumberFormat("es-GT");

export function formatUSD(v: number): string {
  return usdFormatter.format(v);
}

export function formatUSDParen(v: number): string {
  return usdContableFormatter.format(v);
}

/** USD con 2 decimales fijos -- precio por kilolitro ("$6.83"). */
export function formatUSD2(v: number): string {
  return usd2Formatter.format(v);
}

// Intl.NumberFormat con currency:"GTQ" inserta un espacio entre "Q" y el
// monto ("Q 930") -- el reporte real de Power BI no lleva ese espacio
// ("Q930", "-Q19,320", con el signo ANTES de la Q). Se arma el string a
// mano en vez de confiar en el formateador de moneda del Intl.
export function formatQ(v: number): string {
  const signo = v < 0 ? "-" : "";
  return `${signo}Q${Math.round(Math.abs(v)).toLocaleString("es-GT")}`;
}

// Igual que formatQ pero con 2 decimales fijos -- usado en Conciliación
// Bancaria, calcado del spec Deneb real ("Q2,975,052.10", con 2
// decimales, a diferencia del resto del módulo que usa formatQ sin
// decimales).
export function formatQ2(v: number): string {
  const signo = v < 0 ? "-" : "";
  return `${signo}Q${Math.abs(v).toLocaleString("es-GT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatNumber(v: number): string {
  return numberFormatter.format(v);
}

export function formatPercent(v: number): string {
  return `${v.toFixed(1)}%`;
}

// % seguro = numerador/base * 100, protegido contra división por cero
// (0 en vez de NaN/Infinity) -- mismo criterio DIVIDE(...,...,0) que ya
// usa el backend para sus propios % (ver dashboard_otro_ingreso.py,
// dashboard_importaciones_financiero.py). Para columnas/tarjetas nuevas
// calculadas en el frontend a partir de valores que ya trae el backend.
export function pctSeguro(numerador: number, base: number): number {
  return base === 0 ? 0 : (numerador / base) * 100;
}

// Igual que formatPercent pero con 2 decimales fijos -- usado en
// "Comparativo ejecutado" (Presupuestos), calcado del spec real
// ("46.02%", a diferencia del resto del módulo que usa 1 decimal).
export function formatPercent2(v: number): string {
  return `${v.toFixed(2)}%`;
}

// Igual que formatPercent pero sin decimales -- usado en la tabla de
// precio por kilolitro de "Comparación importaciones Kilolitros"
// ("-1%", "18%", calcado del FORMAT("0") real del .pbix).
export function formatPercentEntero(v: number): string {
  return `${Math.round(v)}%`;
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

/** Igual que formatUSDCorto pero sin símbolo de moneda, para métricas que
 * no son montos monetarios (ej. Kilolitros en RankingBarChart). */
export function formatNumeroCorto(valor: number): string {
  if (valor >= 1_000_000) return `${(valor / 1_000_000).toFixed(1)}M`;
  return `${(valor / 1_000).toFixed(1)}K`;
}

/** Igual que formatUSDAbrev/formatQAbrev pero sin símbolo de moneda. */
export function formatNumeroAbrev(v: number): string {
  return abreviarNumero(v);
}

export const MESES = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
];

export const MESES_LARGOS = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

/** Texto del periodo en el subtítulo de la página ("2026 + <periodo> · …").
 * Con Desde=Enero es solo el mes final (como siempre); con otro Desde, el
 * rango ("Abril – Junio") o, si Desde=Hasta, ese único mes. */
export function periodoMesesPagina(mesDesde: number, mesHasta: number): string {
  if (mesDesde <= 1 || mesDesde === mesHasta) return MESES_LARGOS[mesHasta - 1];
  return `${MESES_LARGOS[mesDesde - 1]} – ${MESES_LARGOS[mesHasta - 1]}`;
}

/** Texto del periodo en el subtítulo de las gráficas. Con Desde=Enero es
 * "hasta <mes>" (como siempre); con otro Desde, "de Abril a Junio" o, si
 * Desde=Hasta, solo ese mes. */
export function periodoMesesGrafica(mesDesde: number, mesHasta: number): string {
  if (mesDesde <= 1) return `hasta ${MESES_LARGOS[mesHasta - 1]}`;
  if (mesDesde === mesHasta) return MESES_LARGOS[mesHasta - 1];
  return `de ${MESES_LARGOS[mesDesde - 1]} a ${MESES_LARGOS[mesHasta - 1]}`;
}

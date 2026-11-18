/** Formatos de número y fecha de Indicadores (los del PBIX: "Q"#,0 para dinero, entero para conteos). */

const LOCALE = "en-US";

/** `"Q"#,0` del PBIX: Q29,661 */
export function q0(n: number): string {
  return "Q" + Math.round(n).toLocaleString(LOCALE);
}

export function entero(n: number): string {
  return Math.round(n).toLocaleString(LOCALE);
}

/** Número general con separador de miles y hasta 2 decimales. */
export function num2(n: number): string {
  return n.toLocaleString(LOCALE, { maximumFractionDigits: 2 });
}

/** Escala del eje: Q1.2M / Q200K / Q0 */
export function qCorto(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return "Q" + (n / 1_000_000).toLocaleString(LOCALE, { maximumFractionDigits: 2 }) + "M";
  if (abs >= 1_000) return "Q" + (n / 1_000).toLocaleString(LOCALE, { maximumFractionDigits: 0 }) + "K";
  return "Q" + Math.round(n).toLocaleString(LOCALE);
}

/** 2026-11-05 -> 05/11/2026 */
export function fechaDMA(iso: string | null): string {
  if (!iso) return "";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

/** Puntos de corte «bonitos» para un eje que va de 0 a `max` con ~`pasos` divisiones. */
export function escalaNice(max: number, pasos = 5): { tope: number; ticks: number[] } {
  if (!(max > 0)) return { tope: 1, ticks: [0, 1] };
  const bruto = max / pasos;
  const pot = Math.pow(10, Math.floor(Math.log10(bruto)));
  const f = bruto / pot;
  const paso = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * pot;
  const tope = Math.ceil(max / paso) * paso;
  const ticks: number[] = [];
  for (let v = 0; v <= tope + paso / 1000; v += paso) ticks.push(v);
  return { tope, ticks };
}

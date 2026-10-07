// Títulos dinámicos del módulo Financiero, calcados de las medidas DAX del
// .pbix real (PIQ_AGREQUIMA.pbix). Cada función dice, en su comentario, la
// medida de Power BI que replica. Todos se calculan con el año y el mes que
// el usuario tiene elegidos: nada de fechas, meses ni días escritos a mano
// (el último día del mes se calcula: 28, 29, 30 o 31 según mes y año).
import { MESES_LARGOS } from "./format";

/** Último día del mes (equivale a FORMAT(EOMONTH(MAX(MiCalendario[Date]), 0), "dd")). */
export function ultimoDiaDelMes(anio: number, mes: number): number {
  return new Date(anio, mes, 0).getDate();
}

function nombreMes(mes: number): string {
  return MESES_LARGOS[mes - 1];
}

function alDiaDeMes(anio: number, mes: number): string {
  return `${ultimoDiaDelMes(anio, mes)} de ${nombreMes(mes)} de ${anio}`;
}

/** _Calculos.ERComparativo (título de la página "Estado de ingresos y desembolsos mensual"). */
export function tituloEstadoComparativo(anio: number, mes: number): string {
  return `Estado de Ingresos y Desembolsos Comparativo Al ${alDiaDeMes(anio, mes)} vs ${anio - 1}`;
}

/** _Calculos.ERMensual (título de la página "Estado de ingresos y desembolsos acumulado"). */
export function tituloEstadoAcumulado(anio: number, mes: number): string {
  return `Estado de Ingresos y Desembolsos Acumulado a ${nombreMes(mes)} ${anio}`;
}

/** _Calculos.TituloEstadoMensualAcumulado (gráfica de la derecha de "Estado ... mensual"). */
export function tituloGraficaAcumuladoAl(anio: number, mes: number): string {
  return `Acumulado al ${alDiaDeMes(anio, mes)}`;
}

/** _Calculos_Balance.BalanceMensual (título de la página "Balance general acumulado mensual"). */
export function tituloBalanceAcumuladoAl(anio: number, mes: number): string {
  return `Balance General Acumulado al ${alDiaDeMes(anio, mes)}`;
}

/** _Calculos.TituloBalanceMensual (dona de "Balance general acumulado mensual"). */
export function tituloBalanceAl(anio: number, mes: number): string {
  return `Balance General al ${alDiaDeMes(anio, mes)}`;
}

/** _Calculos_Balance.BalanceAcumulado (título de la página "Balance general acumulado comparativo"). */
export function tituloBalanceAcumuladoComparativo(anio: number, mes: number): string {
  return `Balance General Acumulado comparativo ${nombreMes(mes)} ${anio} vs ${anio - 1}`;
}

/**
 * _Calculos_Balance.TituloPorcentajesActivo / Pasivo / Patrimonio (tarjetas A, PA y PT
 * del "Balance general acumulado comparativo"): dos líneas.
 */
export function tituloDiferenciaPorcentual(
  cuenta: "Activo" | "Pasivo" | "Patrimonio",
  anio: number,
  mes: number
): { linea1: string; linea2: string } {
  return { linea1: `Diferencia porcentual ${cuenta}`, linea2: `${nombreMes(mes)} ${anio} vs ${anio - 1}` };
}

/** Asociados.TituloCuotaAsociados (título de la página "Cuotas asociados"). */
export function tituloCuotaAsociados(anio: number): string {
  return `Cuota Asociados Año ${anio}`;
}

/** _Calculos.TituloFlujoCaja (encabezado de "Flujo de caja"): tres líneas. */
export function lineasTituloFlujoCaja(anio: number, mes: number): [string, string, string] {
  return ["Flujo de Caja", "Cifras Expresadas en Quetzales", `Al ${alDiaDeMes(anio, mes)}`];
}

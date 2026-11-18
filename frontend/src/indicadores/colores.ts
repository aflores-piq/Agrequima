/** Colores de datos del PBIX (inventario_pbix.md, página «Resumen General»); iguales en claro y oscuro. */

export const COLOR_GASTO: Record<string, string> = {
  Hospedaje: "#6A1B9A",
  Alimentacion: "#2E7D32",
  "Caja Chica": "#00838F",
  Combustible: "#C62828",
  "Gasto Centro de Acopio": "#EF6C00",
};

/** Respaldo para un tipo de gasto nuevo que el PBIX no conoce. */
const RESPALDO = ["#1565C0", "#6D4C41", "#AD1457", "#5E35B1", "#455A64", "#9E9D24"];

export function colorGasto(nombre: string, indice: number): string {
  return COLOR_GASTO[nombre] ?? RESPALDO[indice % RESPALDO.length];
}

/** «Viáticos Totales por Colaborador»: todas las barras del mismo color. */
export const COLOR_BARRA = "#00897B";

/** Íconos de las 4 tarjetas KPI (maqueta / imagen del nuevo diseño). */
export const COLOR_KPI: Record<string, string> = {
  total_viaticos: "#2B8FE0",
  tecnicos_conductores: "#7D4AFE",
  total_documentos: "#05AA68",
  total_proveedores: "#FF990C",
};

export const COLOR_SUBE = "#05AA68";
export const COLOR_BAJA = "#E5484D";

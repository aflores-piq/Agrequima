import { useMemo, useState } from "react";
import { MESES_LARGOS } from "../utils/format";

/** Hook reutilizable de orden por encabezado para las tablas de tipo
 * "listado" del Financiero (ver PARTE A, punto 2 del pedido del
 * usuario): 1er clic en un encabezado -> ascendente, 2do clic ->
 * descendente, 3er clic -> vuelve al orden ORIGINAL (el de Power BI) y
 * se desactiva. Clic en OTRO encabezado reinicia el ciclo en esa
 * columna nueva.
 *
 * NO usar en tablas donde el orden es parte del reporte real (jerarquías,
 * Conciliación bancaria, Flujo de caja, el cuadro de precios de
 * Kilolitros, la tabla transpuesta de Otros ingresos, los estados
 * financieros) -- ver la lista de exclusiones documentada en el informe
 * de esta ronda.
 *
 * La fila de Total (o de resumen, ej. "Presupuesto"/"Ejecución" en
 * Otros informes) NUNCA se pasa a `filas`: el llamador la agrega aparte,
 * siempre al final, fuera de este hook.
 */

export type TipoColumnaOrdenable = "numero" | "mes" | "texto";
export type DireccionOrden = "asc" | "desc" | "original";

export interface ColumnaOrdenable<T> {
  clave: string;
  tipo: TipoColumnaOrdenable;
  /** null (o "" / "—" para texto) se interpreta como vacío: siempre va
   * al final, sea cual sea la dirección. */
  valor: (fila: T) => number | string | null;
}

function esVacio(v: number | string | null): boolean {
  return v === null || v === "" || v === "—";
}

function comparar(a: number | string, b: number | string, tipo: TipoColumnaOrdenable): number {
  if (tipo === "numero") return (a as number) - (b as number);
  if (tipo === "mes") return MESES_LARGOS.indexOf(a as string) - MESES_LARGOS.indexOf(b as string);
  return String(a).localeCompare(String(b), "es");
}

export function useTablaOrdenable<T>(filasOriginales: T[], columnas: ColumnaOrdenable<T>[]) {
  const [columnaActiva, setColumnaActiva] = useState<string | null>(null);
  const [direccion, setDireccion] = useState<DireccionOrden>("original");

  function alClickEncabezado(clave: string) {
    if (columnaActiva !== clave) {
      setColumnaActiva(clave);
      setDireccion("asc");
      return;
    }
    if (direccion === "asc") setDireccion("desc");
    else {
      setDireccion("original");
      setColumnaActiva(null);
    }
  }

  const filas = useMemo(() => {
    if (!columnaActiva || direccion === "original") return filasOriginales;
    const columna = columnas.find((c) => c.clave === columnaActiva);
    if (!columna) return filasOriginales;
    const conIndice = filasOriginales.map((fila, indice) => ({ fila, indice, valor: columna.valor(fila) }));
    conIndice.sort((a, b) => {
      const aVacio = esVacio(a.valor);
      const bVacio = esVacio(b.valor);
      // "—" y vacíos SIEMPRE al final, sea cual sea la dirección.
      if (aVacio && bVacio) return a.indice - b.indice;
      if (aVacio) return 1;
      if (bVacio) return -1;
      let cmp = comparar(a.valor as number | string, b.valor as number | string, columna.tipo);
      if (cmp === 0) cmp = a.indice - b.indice; // orden estable en empates
      return direccion === "asc" ? cmp : -cmp;
    });
    return conIndice.map((c) => c.fila);
  }, [filasOriginales, columnaActiva, direccion, columnas]);

  function flechaColumna(clave: string): "▲" | "▼" | null {
    if (columnaActiva !== clave || direccion === "original") return null;
    return direccion === "asc" ? "▲" : "▼";
  }

  return { filas, alClickEncabezado, columnaActiva, direccion, flechaColumna };
}

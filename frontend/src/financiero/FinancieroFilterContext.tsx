import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

/** Sincroniza el filtro "Año y Mes" (o solo "Año") entre pantallas del
 * módulo Financiero, calcando la sincronización de slicers real del
 * .pbix:
 * - Grupo 1 (Año+Mes): las 4 de Estados financieros, las 5 de Otros
 *   informes financieros y, cuando existan, las 3 de Presupuestos y
 *   "Comparación importaciones kilolitros".
 * - Grupo 2 (solo Año): "Ingresos por importación" e "Ingresos por
 *   importación comparativo" -- páginas todavía no construidas, este
 *   grupo queda listo para cuando existan.
 * Las pantallas independientes ("Ingresos por contribución 4.5 por
 * millar", "Otros ingresos generados") NO usan este contexto.
 *
 * Cada pantalla del Grupo 1 puede tener su propio rango real de
 * períodos (tablas distintas) -- este contexto solo guarda la
 * INTENCIÓN del usuario (el último año+mes elegido en cualquier
 * pantalla del grupo). `useFinancieroFilterGrupo1` recorta ese mes al
 * último disponible de cada pantalla cuando no existe en sus propios
 * datos, sin sobrescribir el valor compartido -- así no se rompe el mes
 * elegido para las demás pantallas del grupo. */
interface FinancieroFilterContextValue {
  grupo1Anio: string;
  grupo1Mes: string;
  setGrupo1: (anio: string, mes: string) => void;
  grupo2Anio: string;
  setGrupo2Anio: (anio: string) => void;
}

const FinancieroFilterContext = createContext<FinancieroFilterContextValue | undefined>(undefined);

export function FinancieroFilterProvider({ children }: { children: ReactNode }) {
  const [grupo1Anio, setGrupo1Anio] = useState("");
  const [grupo1Mes, setGrupo1Mes] = useState("");
  const [grupo2Anio, setGrupo2Anio] = useState("");

  const setGrupo1 = useCallback((anio: string, mes: string) => {
    setGrupo1Anio(anio);
    setGrupo1Mes(mes);
  }, []);

  const value = useMemo(
    () => ({ grupo1Anio, grupo1Mes, setGrupo1, grupo2Anio, setGrupo2Anio }),
    [grupo1Anio, grupo1Mes, setGrupo1, grupo2Anio]
  );

  return <FinancieroFilterContext.Provider value={value}>{children}</FinancieroFilterContext.Provider>;
}

function useFinancieroFilterContext(): FinancieroFilterContextValue {
  const ctx = useContext(FinancieroFilterContext);
  if (!ctx) throw new Error("useFinancieroFilterGrupo1/2 deben usarse dentro de FinancieroFilterProvider");
  return ctx;
}

/** Hook para las pantallas del Grupo 1 (Año+Mes sincronizado). `periodos`
 * son los pares año+mes reales de ESTA pantalla (de su propia respuesta
 * del backend, `data.periodos_disponibles` mientras no haya datos
 * todavía se le pasa `[]`) -- devuelve el año/mes "efectivo" ya
 * recortado a lo que esta pantalla realmente tiene, sin tocar el valor
 * compartido si otra pantalla del grupo dejó un mes que acá no existe. */
export function useFinancieroFilterGrupo1(periodos: { anio: number; mes: number }[]) {
  const { grupo1Anio, grupo1Mes, setGrupo1 } = useFinancieroFilterContext();

  const mesesDelAnio = periodos
    .filter((p) => String(p.anio) === grupo1Anio)
    .map((p) => p.mes)
    .sort((a, b) => a - b);

  // Sin info todavía de esta pantalla (antes del primer fetch) o el año
  // compartido no existe en sus propios datos: se deja pasar el mes
  // compartido tal cual -- el backend resuelve su propio default y el
  // siguiente render ya trae `periodos` reales para recortar bien.
  const mesEfectivo =
    mesesDelAnio.length === 0
      ? grupo1Mes
      : mesesDelAnio.includes(Number(grupo1Mes))
        ? grupo1Mes
        : String(Math.max(...mesesDelAnio));

  function cambiarAnio(nuevoAnio: string) {
    const mesesDelNuevoAnio = periodos.filter((p) => String(p.anio) === nuevoAnio).map((p) => p.mes);
    const nuevoMes = mesesDelNuevoAnio.includes(Number(grupo1Mes)) ? grupo1Mes : String(Math.max(...mesesDelNuevoAnio));
    setGrupo1(nuevoAnio, nuevoMes);
  }

  function cambiarMes(nuevoMes: string) {
    setGrupo1(grupo1Anio, nuevoMes);
  }

  return { anio: grupo1Anio, mes: mesEfectivo, setAnioMes: setGrupo1, cambiarAnio, cambiarMes };
}

/** Hook para las pantallas del Grupo 2 (solo Año sincronizado) --
 * todavía sin pantallas propias construidas, listo para cuando existan. */
export function useFinancieroFilterGrupo2() {
  const { grupo2Anio, setGrupo2Anio } = useFinancieroFilterContext();
  return { anio: grupo2Anio, setAnio: setGrupo2Anio };
}

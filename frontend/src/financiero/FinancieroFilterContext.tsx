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
  // Pantallas independientes (NO sincronizadas entre sí ni con los 2
  // grupos de arriba): cada una guarda su PROPIA selección acá en vez de
  // en un useState local del componente, para que sobreviva al
  // desmontar/remontar (navegar a otra pantalla y volver dentro de la
  // misma sesión) -- antes, al ser estado local, la selección manual del
  // usuario se perdía y volvía al default del backend.
  contribucionAnio: string;
  contribucionMes: string;
  setContribucion: (anio: string, mes: string) => void;
  otrosIngresosAnio: string;
  setOtrosIngresosAnio: (anio: string) => void;
}

const FinancieroFilterContext = createContext<FinancieroFilterContextValue | undefined>(undefined);

export function FinancieroFilterProvider({ children }: { children: ReactNode }) {
  const [grupo1Anio, setGrupo1Anio] = useState("");
  const [grupo1Mes, setGrupo1Mes] = useState("");
  const [grupo2Anio, setGrupo2Anio] = useState("");
  const [contribucionAnio, setContribucionAnio] = useState("");
  const [contribucionMes, setContribucionMes] = useState("");
  const [otrosIngresosAnio, setOtrosIngresosAnio] = useState("");

  const setGrupo1 = useCallback((anio: string, mes: string) => {
    setGrupo1Anio(anio);
    setGrupo1Mes(mes);
  }, []);

  const setContribucion = useCallback((anio: string, mes: string) => {
    setContribucionAnio(anio);
    setContribucionMes(mes);
  }, []);

  const value = useMemo(
    () => ({
      grupo1Anio,
      grupo1Mes,
      setGrupo1,
      grupo2Anio,
      setGrupo2Anio,
      contribucionAnio,
      contribucionMes,
      setContribucion,
      otrosIngresosAnio,
      setOtrosIngresosAnio,
    }),
    [grupo1Anio, grupo1Mes, setGrupo1, grupo2Anio, contribucionAnio, contribucionMes, setContribucion, otrosIngresosAnio]
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
 * compartido si otra pantalla del grupo dejó un año o un mes que acá no
 * existe (p.ej. Grupo 1 en 2023, año que SaldosBancos/SaldoBancario -- y
 * por lo tanto Flujo de caja/Conciliación bancaria -- no tienen, solo
 * arrancan en 2024). */
export function useFinancieroFilterGrupo1(periodos: { anio: number; mes: number }[]) {
  const { grupo1Anio, grupo1Mes, setGrupo1 } = useFinancieroFilterContext();

  const aniosDisponibles = Array.from(new Set(periodos.map((p) => p.anio))).sort((a, b) => a - b);

  // Año efectivo: si el año compartido no existe en los datos propios de
  // esta pantalla, se usa el año disponible más cercano (el mayor que
  // sea <= al compartido; si no hay ninguno menor -- el compartido es
  // anterior a todo lo que esta pantalla tiene -- se usa el menor
  // disponible). El selector de año NUNCA muestra un valor que no esté
  // entre sus propias opciones.
  const anioEfectivo = (() => {
    if (periodos.length === 0) return grupo1Anio; // sin datos todavía (antes del primer fetch): se deja pasar tal cual
    if (aniosDisponibles.includes(Number(grupo1Anio))) return grupo1Anio;
    const anioNum = Number(grupo1Anio);
    const masCercanoMenor = [...aniosDisponibles].reverse().find((a) => a <= anioNum);
    return String(masCercanoMenor ?? aniosDisponibles[0]);
  })();

  const mesesDelAnio = periodos
    .filter((p) => String(p.anio) === anioEfectivo)
    .map((p) => p.mes)
    .sort((a, b) => a - b);

  // Si el año tuvo que recortarse (anioEfectivo !== grupo1Anio), el mes
  // compartido no aplica a ese otro año -- se usa directo el último mes
  // disponible del año efectivo, nunca un selector vacío.
  const mesEfectivo =
    mesesDelAnio.length === 0
      ? grupo1Mes
      : anioEfectivo === grupo1Anio && mesesDelAnio.includes(Number(grupo1Mes))
        ? grupo1Mes
        : String(Math.max(...mesesDelAnio));

  function cambiarAnio(nuevoAnio: string) {
    const mesesDelNuevoAnio = periodos.filter((p) => String(p.anio) === nuevoAnio).map((p) => p.mes);
    const nuevoMes = mesesDelNuevoAnio.includes(Number(grupo1Mes)) ? grupo1Mes : String(Math.max(...mesesDelNuevoAnio));
    setGrupo1(nuevoAnio, nuevoMes);
  }

  function cambiarMes(nuevoMes: string) {
    setGrupo1(anioEfectivo, nuevoMes);
  }

  return { anio: anioEfectivo, mes: mesEfectivo, setAnioMes: setGrupo1, cambiarAnio, cambiarMes };
}

/** Hook para las pantallas del Grupo 2 (solo Año sincronizado) --
 * todavía sin pantallas propias construidas, listo para cuando existan. */
export function useFinancieroFilterGrupo2() {
  const { grupo2Anio, setGrupo2Anio } = useFinancieroFilterContext();
  return { anio: grupo2Anio, setAnio: setGrupo2Anio };
}

/** Hook para "Ingresos por contribución 4.5 por millar" -- independiente,
 * sin sincronizar con ningún otro grupo, pero con memoria propia dentro
 * de la sesión (sobrevive a navegar a otra pantalla y volver). */
export function useFinancieroFilterContribucion() {
  const { contribucionAnio, contribucionMes, setContribucion } = useFinancieroFilterContext();
  return { anio: contribucionAnio, mes: contribucionMes, setAnioMes: setContribucion };
}

/** Hook para "Otros ingresos generados" -- independiente (solo Año), con
 * la misma memoria propia dentro de la sesión que useFinancieroFilterContribucion. */
export function useFinancieroFilterOtrosIngresos() {
  const { otrosIngresosAnio, setOtrosIngresosAnio } = useFinancieroFilterContext();
  return { anio: otrosIngresosAnio, setAnio: setOtrosIngresosAnio };
}

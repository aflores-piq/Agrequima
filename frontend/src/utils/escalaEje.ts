// Escala de eje calculada SOLO a partir de los datos que se muestran -- ningún
// tope ni marca escrita a mano. Reemplaza los ejes fijos que tenían varias
// gráficas del Financiero (Flujo de caja Q0-Q8,000,000, Presupuestos,
// Ingresos por importación, Ejecución gastos mensual...), que cortaban la
// barra o la línea apenas el dato pasaba del tope.
//
// Reglas:
//  - el máximo es el valor más alto de los datos + un margen chico (8 %),
//    redondeado HACIA ARRIBA al siguiente múltiplo de un paso "limpio"
//    (1, 2, 2.5 o 5 x 10^k), así la barra/línea más alta nunca toca el borde;
//  - si hay valores negativos, el mínimo se calcula igual hacia abajo; si no
//    hay negativos, el eje empieza en 0;
//  - el paso se elige para dejar entre 4 y 6 intervalos (si los datos no
//    permiten eso, se abre el rango poco a poco) con el techo MÁS BAJO
//    posible, y a igual techo el paso más grande (menos marcas).
// Cualquier cambio de datos (año, mes, filtro) vuelve a calcularla porque se
// invoca en cada render con los datos de ese momento.

export interface EscalaEje {
  min: number;
  max: number;
  dominio: [number, number];
  ticks: number[];
}

const MARGEN_POR_DEFECTO = 0.08;
const PASOS_BASE = [1, 2, 2.5, 5];
// Rangos de cantidad de intervalos que se intentan, en orden.
const RANGOS_INTERVALOS: Array<[number, number]> = [
  [4, 6],
  [3, 8],
  [2, 14],
];
const EPSILON = 1e-9;

// Evita arrastrar ruido de punto flotante (0.1 + 0.2) a las marcas del eje.
function limpiar(x: number): number {
  return Number(x.toPrecision(12));
}

export function calcularEscalaEje(
  valores: ReadonlyArray<number | null | undefined>,
  margen: number = MARGEN_POR_DEFECTO
): EscalaEje {
  const datos = valores.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  const maximo = Math.max(0, ...datos);
  const minimo = Math.min(0, ...datos);
  if (maximo === 0 && minimo === 0) {
    // Sin datos (o todo en 0): eje 0-1 con solo sus 2 extremos, para que un
    // formateador de moneda sin decimales no muestre "Q1 / Q1" (0.5 -> 1).
    return { min: 0, max: 1, dominio: [0, 1], ticks: [0, 1] };
  }
  const topeSuperior = maximo * (1 + margen);
  const topeInferior = minimo * (1 + margen);

  const candidatos: Array<{ paso: number; min: number; max: number; intervalos: number }> = [];
  for (let k = -6; k <= 14; k++) {
    for (const base of PASOS_BASE) {
      const paso = limpiar(base * Math.pow(10, k));
      const max = maximo > 0 ? limpiar(Math.ceil(topeSuperior / paso - EPSILON) * paso) : 0;
      const min = minimo < 0 ? limpiar(Math.floor(topeInferior / paso + EPSILON) * paso) : 0;
      const intervalos = Math.round((max - min) / paso);
      if (intervalos >= 1) candidatos.push({ paso, min, max, intervalos });
    }
  }

  for (const [desde, hasta] of RANGOS_INTERVALOS) {
    const aptos = candidatos.filter((c) => c.intervalos >= desde && c.intervalos <= hasta);
    if (aptos.length === 0) continue;
    const mejor = aptos.reduce((a, b) => {
      const spanA = a.max - a.min;
      const spanB = b.max - b.min;
      if (Math.abs(spanA - spanB) > EPSILON * Math.max(1, Math.abs(spanA))) return spanA < spanB ? a : b;
      return a.paso >= b.paso ? a : b;
    });
    const ticks: number[] = [];
    for (let i = 0; i <= mejor.intervalos; i++) ticks.push(limpiar(mejor.min + i * mejor.paso));
    return { min: mejor.min, max: mejor.max, dominio: [mejor.min, mejor.max], ticks };
  }

  // No debería pasar (los pasos cubren de 1e-6 a 5e14), pero nunca se deja un
  // eje sin definir: dominio exacto de los datos con margen.
  const min = minimo < 0 ? topeInferior : 0;
  const max = maximo > 0 ? topeSuperior : 0;
  return { min, max, dominio: [min, max], ticks: [min, max] };
}

// Dominio para ejes que dejan a Recharts elegir el máximo ("auto") pero que
// NUNCA recortan valores negativos: el mínimo es 0 salvo que algún dato sea
// menor, en cuyo caso baja hasta ese dato.
export const DOMINIO_AUTO_SIN_RECORTAR_NEGATIVOS: [(dataMin: number) => number, "auto"] = [
  (dataMin: number) => Math.min(0, dataMin),
  "auto",
];

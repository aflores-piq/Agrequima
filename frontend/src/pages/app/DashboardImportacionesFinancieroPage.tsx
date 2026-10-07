import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Title } from "@tremor/react";
import { Bar, BarChart, Customized, LabelList, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { LabelProps } from "recharts";
import {
  obtenerContribucionMillar,
  obtenerIngresosImportacion,
  obtenerIngresosImportacionComparativo,
  obtenerKilolitros,
} from "../../api/dashboardImportacionesFinanciero";
import { mensajeError } from "../../api/client";
import { useFinancieroFilterGrupo1, useFinancieroFilterGrupo2, useFinancieroFilterContribucion } from "../../financiero/FinancieroFilterContext";
import { FilterYear, FilterYearMonth } from "../../components/filters/PowerBiFilter";
import { EncabezadoOrdenable } from "../../components/EncabezadoOrdenable";
import { useTablaOrdenable, type ColumnaOrdenable } from "../../hooks/useTablaOrdenable";
import { FINANCIERO_SURFACE, GAP_TITULO_PRIMER_ELEMENTO, VERDE_ENCABEZADO } from "../../components/TablaGrupoExpandible";
import { COLOR_EJECUTADO, COLOR_PRESUPUESTO, ultimoDiaDelMes } from "./DashboardOtrosInformesPage";
import { useTheme } from "../../theme/ThemeContext";
import { calcularEscalaEje } from "../../utils/escalaEje";
import {
  formatPercent2,
  formatPercentEntero,
  formatQ,
  formatUSD,
  formatUSD2,
  formatUSDParen,
  MESES,
  MESES_LARGOS,
} from "../../utils/format";
import type {
  BloqueComparativoInstitucion,
  ContribucionMillarResponse,
  FilaCIFMes,
  FilaPrecioKilolitro,
  ImportacionComparativoResponse,
  IngresosImportacionResponse,
  KilolitrosResponse,
  PuntoCIFMes,
  PuntoContribucionMes,
  PuntoPrecioMes,
} from "../../types/dashboardImportacionesFinanciero";

// Ancho real medido del ancho de la tarjeta (para barSize/leyenda propia
// y para el clamp de las cajitas de valor) -- mismo patrón que
// Presupuestos.
function useAnchoElemento<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [ancho, setAncho] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setAncho(entry.contentRect.width);
    });
    observer.observe(el);
    setAncho(el.getBoundingClientRect().width);
    return () => observer.disconnect();
  }, []);
  return [ref, ancho] as const;
}

// Relación alto/ancho de CADA TARJETA completa (título+gráfica+leyenda) --
// decisión de diseño propia del usuario para las 2 gráficas de líneas de
// "Ingresos por importación" (0.40, la del Layout real es 0.52). Mismo
// mecanismo que Presupuestos: el `aspect` de ResponsiveContainer solo
// controla el <svg>, así que hay que despejar su alto para que la
// TARJETA completa (con el título y la leyenda propia arriba/abajo del
// <svg>) dé exactamente la proporción pedida.
const PROPORCION_ALTO_ANCHO_IMPORTACION = 0.4;
const ALTO_EXTRA_TITULO_LEYENDA = 60; // px: ~32 (título) + 28 (leyenda)

function calcularAspectoSvg(anchoTarjeta: number, proporcion: number): number {
  if (!anchoTarjeta) return 1 / proporcion;
  const altoSvgDeseado = proporcion * anchoTarjeta - ALTO_EXTRA_TITULO_LEYENDA;
  return anchoTarjeta / Math.max(altoSvgDeseado, 1);
}

// Leyenda propia centrada sobre el ÁREA DE DATOS (no el <svg> completo) --
// mismo problema/solución que Presupuestos: con el eje Y ocupando espacio
// solo a la izquierda, el <Legend> de Recharts (centrado en el SVG
// completo) no coincide con el centro real de las barras/líneas.
function LeyendaCentrada({
  anchoTarjeta,
  gutterIzquierdo,
  gutterDerecho,
  items,
}: {
  anchoTarjeta: number;
  gutterIzquierdo: number;
  gutterDerecho: number;
  items: { etiqueta: string; color: string }[];
}) {
  const centro = gutterIzquierdo + (anchoTarjeta - gutterIzquierdo - gutterDerecho) / 2;
  return (
    <div className="relative h-7">
      <div
        className="absolute top-0 flex items-center gap-4 whitespace-nowrap text-sm font-bold text-ink"
        style={{ left: centro || "50%", transform: "translateX(-50%)" }}
      >
        {items.map((it) => (
          <span key={it.etiqueta} className="flex items-center gap-1.5">
            <span aria-hidden="true" className="inline-block h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: it.color }} />
            {it.etiqueta}
          </span>
        ))}
      </div>
    </div>
  );
}

// Ancho del eje Y en px, calculado a partir del tick más largo ya
// formateado (mismo criterio que Presupuestos: `anchoEjeY`).
function calcularAnchoEjeY(ticksFormateados: string[], fontSizeEje = 12): number {
  const masLargo = Math.max(0, ...ticksFormateados.map((t) => t.length));
  return Math.max(60, 14 + masLargo * (fontSizeEje * 0.62));
}

// Posición X de la cajita de valor, recortada para no invadir el gutter
// del eje Y (izquierda) ni salirse del área de la tarjeta (derecha) --
// ver bitácora: el punto más cercano a cada borde queda con su cajita
// centrada normalmente saliéndose de la tarjeta.
function calcularXCaja(x: number, ancho: number, gutterIzquierdo?: number, gutterDerecho?: number): number {
  let xCaja = x - ancho / 2;
  if (gutterIzquierdo !== undefined) xCaja = Math.max(xCaja, gutterIzquierdo);
  if (gutterDerecho !== undefined) xCaja = Math.min(xCaja, gutterDerecho - ancho);
  return xCaja;
}

// Dominio "nice" ajustado a los datos (NO forzado a incluir 0): mínimo
// redondeado hacia abajo y máximo hacia arriba al múltiplo "redondo" más
// cercano de un paso candidato (1, 2, 3, 5 o 10 * 10^k), buscando el
// paso MÁS CHICO (más marcas, más preciso) que deje el resultado entre 5
// y 7 marcas -- decisión propia del usuario, apartándose de Power BI
// (que en este spec real SÍ arranca en 0) porque con datos lejos de 0 la
// mitad de la gráfica queda vacía. Si el margen que deja el techo
// redondeado sobre el valor más alto real es chico, se suma un paso
// completo más, para que la cajita de etiqueta del punto más alto no
// quede pegada/cortada contra el borde superior.
const PASOS_BASE_DOMINIO = [1, 2, 3, 5, 10];
const UMBRAL_MARGEN_SUPERIOR = 0.3;

function calcularDominioNice(valores: number[]): { dominio: [number, number]; ticks: number[] } {
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  const candidatos: number[] = [];
  for (let k = -2; k <= 9; k++) {
    for (const base of PASOS_BASE_DOMINIO) candidatos.push(base * Math.pow(10, k));
  }
  candidatos.sort((a, b) => a - b);

  let mejorFallback: { domMin: number; domMax: number; paso: number; numMarcas: number } | null = null;
  let mejorPuntaje = Infinity;

  // Límite de seguridad: un paso candidato demasiado chico frente a la
  // escala real de los datos generaría millones de marcas (y un array
  // de ese tamaño revienta el navegador) -- se descarta ANTES de armar
  // ningún array, sin esperar a filtrar por la banda 5-7.
  const LIMITE_MARCAS = 60;

  for (const paso of candidatos) {
    const domMin = Math.floor(min / paso) * paso;
    let domMax = Math.ceil(max / paso) * paso;
    if (domMax - max < paso * UMBRAL_MARGEN_SUPERIOR) domMax += paso;
    const numMarcas = Math.round((domMax - domMin) / paso) + 1;
    if (numMarcas < 2 || numMarcas > LIMITE_MARCAS) continue;
    if (numMarcas >= 5 && numMarcas <= 7) {
      const ticks: number[] = [];
      for (let i = 0; i < numMarcas; i++) ticks.push(Math.round(domMin + i * paso));
      return { dominio: [Math.round(domMin), Math.round(domMax)], ticks };
    }
    const puntaje = Math.abs(numMarcas - 6);
    if (puntaje < mejorPuntaje) {
      mejorPuntaje = puntaje;
      mejorFallback = { domMin: Math.round(domMin), domMax: Math.round(domMax), paso, numMarcas };
    }
  }
  if (mejorFallback) {
    const { domMin, paso, numMarcas } = mejorFallback;
    const ticks: number[] = [];
    for (let i = 0; i < numMarcas; i++) ticks.push(Math.round(domMin + i * paso));
    return { dominio: [mejorFallback.domMin, mejorFallback.domMax], ticks };
  }
  return { dominio: [min, max], ticks: [min, max] };
}

// Cuando dos cajitas de etiqueta quedarían pisadas -- ya sea porque los
// puntos de las 2 series de un mismo mes caen cerca en Y, o porque los
// meses son tantos que las cajas (más anchas que la separación entre
// puntos) invaden a las del mes vecino -- se resuelve poniendo cada
// etiqueta arriba o abajo de su propio punto según lo que YA se colocó:
// se procesan los 2*N puntos de izquierda a derecha (y, dentro del
// mismo mes, primero el de valor MAYOR) probando primero "arriba"
// (comportamiento normal); si esa caja pisa alguna ya colocada, se
// prueba "abajo"; si ninguna de las 2 alcanza, se deja "arriba" (no hay
// mejor opción posible con solo 2 posiciones).
//
// Las posiciones X se recalculan acá con la MISMA fórmula que usa
// Recharts para un eje de categorías sin padding extra (confirmado
// midiendo con getBoundingClientRect: el primer punto cae exactamente
// en `gutterIzquierdo` y el último en `anchoSvg - margin.right`,
// espaciados en partes iguales) -- necesario para poder decidir la
// posición de TODOS los puntos de una sola pasada, antes de que Recharts
// renderice ninguna etiqueta (el callback `label` de cada serie por
// separado no tiene forma de saber qué hizo la otra serie).
// Desplazamiento Y (respecto del punto) del TOPE de la caja, en orden
// de preferencia: arriba normal, abajo normal, arriba "apilado" un
// escalón más, abajo apilado un escalón más, etc. Con solo 2 opciones
// (arriba/abajo), un grupo de 3+ puntos muy juntos en valores bajos
// (donde "abajo" ya no cabe sin tocar el eje X) no tenía forma de
// separarse entre sí -- con más variantes, cada uno prueba la primera
// que no choque ni se salga de los límites.
const OFFSETS_CANDIDATOS = [-32, 12, -56, 36, -80, 60, -104, 84];

// Escalas X/Y analíticas para un eje de categorías de N puntos sin
// padding extra (confirmado midiendo con getBoundingClientRect: el
// primer punto cae exactamente en `gutterIzquierdo` y el último en
// `anchoSvg - margin.right`, espaciados en partes iguales) -- las mismas
// que usa Recharts internamente. Se factorizan acá porque las necesitan
// tanto calcularPosicionesEtiquetas (para decidir colisiones ANTES de
// que Recharts renderice nada) como la capa de etiquetas por encima de
// las líneas (Customized, ver GraficoCIFLineas) -- ambas tienen que
// coincidir en la posición exacta de cada punto.
function crearEscalas(
  n: number,
  dominio: [number, number],
  anchoSvg: number,
  altoSvg: number,
  margin: { top: number; right: number; bottom: number },
  gutterIzquierdo: number
) {
  const altoPlot = Math.max(altoSvg - margin.top - margin.bottom, 1);
  const escalaY = (v: number) => margin.top + ((dominio[1] - v) / (dominio[1] - dominio[0] || 1)) * altoPlot;
  const plotAncho = Math.max(anchoSvg - margin.right - gutterIzquierdo, 1);
  const escalaX = (i: number) => (n > 1 ? gutterIzquierdo + (i * plotAncho) / (n - 1) : gutterIzquierdo);
  return { escalaX, escalaY };
}

function calcularPosicionesEtiquetas(
  datos: PuntoCIFMes[],
  dominio: [number, number],
  anchoSvg: number,
  altoSvg: number,
  margin: { top: number; right: number; bottom: number },
  gutterIzquierdo: number,
  gutterDerecho: number | undefined
): { anterior: number[]; actual: number[] } {
  const n = datos.length;
  const anterior: number[] = new Array(n).fill(OFFSETS_CANDIDATOS[0]);
  const actual: number[] = new Array(n).fill(OFFSETS_CANDIDATOS[0]);
  if (n === 0 || !anchoSvg || !altoSvg) return { anterior, actual };

  const { escalaX, escalaY } = crearEscalas(n, dominio, anchoSvg, altoSvg, margin, gutterIzquierdo);

  type Candidato = { serie: "anterior" | "actual"; idx: number; x: number; y: number; valor: number; ancho: number };
  const candidatos: Candidato[] = [];
  datos.forEach((d, i) => {
    const x = escalaX(i);
    // Si el año anterior no tiene datos, esa serie no se dibuja -- no
    // hay candidato que colocar para ella.
    if (d.cif_anio_anterior !== null) {
      candidatos.push({
        serie: "anterior",
        idx: i,
        x,
        y: escalaY(d.cif_anio_anterior),
        valor: d.cif_anio_anterior,
        ancho: Math.max(70, formatUSD(d.cif_anio_anterior).length * 8.5),
      });
    }
    candidatos.push({
      serie: "actual",
      idx: i,
      x,
      y: escalaY(d.cif_anio_actual),
      valor: d.cif_anio_actual,
      ancho: Math.max(70, formatUSD(d.cif_anio_actual).length * 8.5),
    });
  });
  candidatos.sort((a, b) => a.x - b.x || b.valor - a.valor);

  // Límites: además de no chocar con otra caja ya colocada, ninguna caja
  // puede invadir la franja inferior donde Recharts dibuja los nombres
  // de los meses (debajo de margin.bottom) ni el techo de la tarjeta.
  const limiteSuperior = margin.top - 4;
  const limiteInferior = altoSvg - margin.bottom;

  const colocados: { left: number; right: number; top: number; bottom: number }[] = [];
  function caja(c: Candidato, offset: number) {
    // Mismo recorte que el render real (calcularXCaja): sin esto, dos
    // puntos cercanos al borde derecho podrían recortarse a la MISMA
    // posición final y superponerse aunque acá parecieran no chocar.
    const left = calcularXCaja(c.x, c.ancho, gutterIzquierdo, gutterDerecho);
    const top = c.y + offset;
    return { left, right: left + c.ancho, top, bottom: top + 20 };
  }
  function fueraDeLimites(box: { top: number; bottom: number }) {
    return box.top < limiteSuperior || box.bottom > limiteInferior;
  }
  function choca(box: { left: number; right: number; top: number; bottom: number }) {
    return colocados.some((o) => box.left < o.right && o.left < box.right && box.top < o.bottom && o.top < box.bottom);
  }

  for (const c of candidatos) {
    let offsetElegido = OFFSETS_CANDIDATOS[0];
    let box = caja(c, offsetElegido);
    if (choca(box) || fueraDeLimites(box)) {
      let encontrado = false;
      for (const offset of OFFSETS_CANDIDATOS.slice(1)) {
        const candidata = caja(c, offset);
        if (!choca(candidata) && !fueraDeLimites(candidata)) {
          offsetElegido = offset;
          box = candidata;
          encontrado = true;
          break;
        }
      }
      // Si ninguna variante alcanza (caso raro), se deja la primera
      // igual -- no hay más opciones posibles.
      void encontrado;
    }
    colocados.push(box);
    if (c.serie === "anterior") anterior[c.idx] = offsetElegido;
    else actual[c.idx] = offsetElegido;
  }
  return { anterior, actual };
}

// --- Tabla CIF por mes (7 columnas) -- compartida entre "Ingresos por
// importación" y los 2 bloques de "Ingresos por importación
// comparativo". ------------------------------------------------------

// Meses/CIF-año-anterior/CIF-año-actual más anchos que antes: "CIF US$
// 2024" (12 caracteres) se partía en 2 renglones con el 15% original --
// se le quita esos puntos a "Meses" (los nombres de mes, incluido
// "Septiembre", entran sobrados en 20%).
const ANCHOS_COLUMNA_CIF = ["20%", "17%", "9%", "17%", "9%", "16%", "12%"];

function ColgroupCIF() {
  return (
    <colgroup>
      {ANCHOS_COLUMNA_CIF.map((a, i) => (
        <col key={i} style={{ width: a }} />
      ))}
    </colgroup>
  );
}

function FilaTablaCIF({ fila }: { fila: FilaCIFMes }) {
  const claseCelda = `px-2 py-1.5 text-sm text-ink ${fila.negrita ? "font-bold" : ""}`;
  return (
    <tr style={{ backgroundColor: FINANCIERO_SURFACE }} className={fila.negrita ? "border-t border-line" : undefined}>
      <td className={claseCelda}>{fila.mes}</td>
      <td className={`${claseCelda} text-right`}>{fila.cif_anio_anterior === null ? "—" : formatUSD(fila.cif_anio_anterior)}</td>
      <td className={`${claseCelda} text-right`}>{fila.pct_anio_anterior === null ? "—" : formatPercent2(fila.pct_anio_anterior)}</td>
      <td className={`${claseCelda} text-right`}>{formatUSD(fila.cif_anio_actual)}</td>
      <td className={`${claseCelda} text-right`}>{formatPercent2(fila.pct_anio_actual)}</td>
      <td className={`${claseCelda} text-right`}>{fila.variacion === null ? "—" : formatUSDParen(fila.variacion)}</td>
      <td className={`${claseCelda} text-right`}>{fila.variacion_pct === null ? "—" : formatPercent2(fila.variacion_pct)}</td>
    </tr>
  );
}

// `alturaCompleta`: cuando la tabla va al lado de una gráfica más alta
// (bloques de "Ingresos por importación comparativo"), el recuadro debe
// estirarse al mismo alto que la gráfica -- ver BloqueComparativo. Con
// `height:100%` en CSS, un hijo SOLO se estira si su ancestro tiene un
// alto explícito (no "auto"): en "Ingresos por importación" (uso normal,
// sin flex-stretch alrededor) el ancestro es "auto" y esta clase no hace
// nada, así que es seguro dejarla puesta siempre.
//
// El fondo gris de las FILAS (FilaTablaCIF, backgroundColor puesto en
// cada <tr>) NO llena el espacio vacío que queda debajo de la última
// fila cuando el <div> se estira más alto que el contenido real de la
// tabla -- ese espacio se queda con el fondo de la PÁGINA, y el `ring`
// alrededor del <div> (que sí ocupa todo el alto estirado) se ve como un
// borde de color rodeando un hueco sin relleno. Con `alturaCompleta`, el
// fondo gris se pone en el propio <div> (para que el hueco también quede
// gris) y se saca el `ring` (Power BI no lo tiene ahí).
const COLUMNAS_ORDENABLES_CIF: ColumnaOrdenable<FilaCIFMes>[] = [
  { clave: "mes", tipo: "mes", valor: (f) => f.mes },
  { clave: "cif_anio_anterior", tipo: "numero", valor: (f) => f.cif_anio_anterior },
  { clave: "pct_anio_anterior", tipo: "numero", valor: (f) => f.pct_anio_anterior },
  { clave: "cif_anio_actual", tipo: "numero", valor: (f) => f.cif_anio_actual },
  { clave: "pct_anio_actual", tipo: "numero", valor: (f) => f.pct_anio_actual },
  { clave: "variacion", tipo: "numero", valor: (f) => f.variacion },
  { clave: "variacion_pct", tipo: "numero", valor: (f) => f.variacion_pct },
];

function TablaCIFMes({
  filas,
  filaTotal,
  anioAnterior,
  anioActual,
  alturaCompleta = false,
}: {
  filas: FilaCIFMes[];
  filaTotal: FilaCIFMes;
  anioAnterior: number;
  anioActual: number;
  alturaCompleta?: boolean;
}) {
  const { filas: filasOrdenadas, alClickEncabezado, flechaColumna } = useTablaOrdenable(filas, COLUMNAS_ORDENABLES_CIF);
  const claseHeaderTexto = "px-2 py-1.5 text-left text-white font-normal whitespace-nowrap";
  const claseHeaderNumero = "px-2 py-1.5 text-right text-white font-normal whitespace-nowrap";
  return (
    <div
      className={`overflow-hidden rounded-tremor-default ${alturaCompleta ? "h-full" : "ring-1 ring-line"}`}
      style={alturaCompleta ? { backgroundColor: FINANCIERO_SURFACE } : undefined}
    >
      <table className="w-full text-sm">
        <ColgroupCIF />
        <thead>
          <tr style={{ backgroundColor: VERDE_ENCABEZADO }}>
            <EncabezadoOrdenable className={claseHeaderTexto} flecha={flechaColumna("mes")} onClick={() => alClickEncabezado("mes")}>
              Meses
            </EncabezadoOrdenable>
            <EncabezadoOrdenable
              className={claseHeaderNumero}
              flecha={flechaColumna("cif_anio_anterior")}
              onClick={() => alClickEncabezado("cif_anio_anterior")}
            >
              CIF US$ {anioAnterior}
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("pct_anio_anterior")} onClick={() => alClickEncabezado("pct_anio_anterior")}>
              %
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("cif_anio_actual")} onClick={() => alClickEncabezado("cif_anio_actual")}>
              CIF US$ {anioActual}
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("pct_anio_actual")} onClick={() => alClickEncabezado("pct_anio_actual")}>
              %
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("variacion")} onClick={() => alClickEncabezado("variacion")}>
              VAR
            </EncabezadoOrdenable>
            <EncabezadoOrdenable className={claseHeaderNumero} flecha={flechaColumna("variacion_pct")} onClick={() => alClickEncabezado("variacion_pct")}>
              %
            </EncabezadoOrdenable>
          </tr>
        </thead>
        <tbody>
          {filasOrdenadas.map((f) => (
            <FilaTablaCIF key={f.mes} fila={f} />
          ))}
          <FilaTablaCIF fila={filaTotal} />
        </tbody>
      </table>
    </div>
  );
}

// --- Gráfica Deneb de líneas CIF por mes (año-1 vs año) -------------------
//
// Calcado del spec Deneb real del .pbix: 2 líneas rectas (#5B7FAE año-1,
// #43B0A6 año actual), puntos marcados, etiqueta en caja blanca (con
// borde de 1px del color de la serie en modo claro, para que se vea
// sobre el fondo blanco de la tarjeta -- en oscuro, igual que Power BI,
// sin borde) con el valor COMPLETO sin abreviar, eje Y con dominio fijo
// dado por el usuario (distinto por pantalla), leyenda abajo centrada
// con círculos, sin cuadrícula ni línea de eje.

const COLOR_ANIO_ANTERIOR_CIF = "#5B7FAE";
const COLOR_ANIO_ACTUAL_CIF = "#43B0A6";

function EtiquetaCajaCIF({
  x,
  y,
  value,
  color,
  gutterIzquierdo,
  gutterDerecho,
  esClaro,
  desplazamientoY = -32,
}: LabelProps & {
  color: string;
  gutterIzquierdo?: number;
  gutterDerecho?: number;
  esClaro: boolean;
  desplazamientoY?: number;
}) {
  if (typeof x !== "number" || typeof y !== "number" || typeof value !== "number") return null;
  const texto = formatUSD(value);
  const ancho = Math.max(70, texto.length * 8.5);
  const xCaja = calcularXCaja(x, ancho, gutterIzquierdo, gutterDerecho);
  const yCaja = y + desplazamientoY;
  const yTexto = yCaja + 15;
  return (
    <g>
      <rect
        x={xCaja}
        y={yCaja}
        width={ancho}
        height={20}
        rx={2}
        fill="white"
        stroke={esClaro ? color : "none"}
        strokeWidth={esClaro ? 1 : 0}
      />
      <text x={xCaja + ancho / 2} y={yTexto} textAnchor="middle" fontSize={12} fontWeight={700} fill={color}>
        {texto}
      </text>
    </g>
  );
}

// Con muchos meses (año completo, 12) en una gráfica angosta, los
// nombres completos se encimarían en el eje X -- a partir de este
// umbral se usan abreviaturas de 3 letras (MESES), igual que el resto
// de la app; con pocos meses (el caso normal, año en curso) se dejan los
// nombres completos.
const UMBRAL_MESES_ABREVIADOS = 7;

function abreviarMes(mes: string): string {
  const idx = MESES_LARGOS.indexOf(mes);
  return idx >= 0 ? MESES[idx] : mes;
}

function GraficoCIFLineas({
  titulo,
  datos,
  anioAnterior,
  anioActual,
  dominioY,
  ticksY,
  proporcionAltoAncho,
  anioAnteriorSinDatos = false,
}: {
  titulo: string;
  datos: PuntoCIFMes[];
  anioAnterior: number;
  anioActual: number;
  // Sin dominio/ticks fijos: se recalculan de los propios datos (ver
  // calcularDominioNice) -- usado por "Ingresos por importación
  // comparativo", donde el usuario decidió apartarse de Power BI
  // (arranca en $0 ahí) porque con datos lejos de 0 media gráfica queda
  // vacía. La pantalla 1 sigue pasando un dominio fijo, ya aprobado --
  // salvo que el año anterior no tenga datos (ver anioAnteriorSinDatos),
  // caso en el que el dominio SIEMPRE se recalcula solo con el actual.
  dominioY?: [number, number];
  ticksY?: number[];
  proporcionAltoAncho?: number;
  anioAnteriorSinDatos?: boolean;
}) {
  const { tema } = useTheme();
  const esClaro = tema === "Claro";
  const [refTarjeta, anchoTarjeta] = useAnchoElemento<HTMLDivElement>();
  const { dominio, ticks } = anioAnteriorSinDatos
    ? calcularDominioNice(datos.map((d) => d.cif_anio_actual))
    : dominioY && ticksY
      ? { dominio: dominioY, ticks: ticksY }
      : calcularDominioNice(datos.flatMap((d) => [d.cif_anio_anterior ?? 0, d.cif_anio_actual]));
  const anchoEjeY = calcularAnchoEjeY(ticks.map((v) => formatUSD(v)));
  // bottom:22 (antes 4) -- deja lugar reservado para los nombres de mes
  // del eje X; sin esto, una etiqueta puesta "abajo" del punto más bajo
  // podía terminar tapándolos (quedaban fuera del área que Recharts
  // reserva para el eje, en la franja de overflow del SVG).
  const margin = { top: 36, right: 16, bottom: 22, left: 4 };
  const gutterIzquierdo = margin.left + anchoEjeY;
  const gutterDerecho = anchoTarjeta ? anchoTarjeta - margin.right : undefined;
  const aspecto = proporcionAltoAncho
    ? calcularAspectoSvg(anchoTarjeta, proporcionAltoAncho)
    : 1300 / 680;
  const altoSvg = anchoTarjeta ? anchoTarjeta / aspecto : 0;
  const posiciones = calcularPosicionesEtiquetas(datos, dominio, anchoTarjeta, altoSvg, margin, gutterIzquierdo, gutterDerecho);
  const { escalaX, escalaY } = crearEscalas(datos.length, dominio, anchoTarjeta, altoSvg, margin, gutterIzquierdo);
  const etiquetaAnterior = `${anioAnterior}${anioAnteriorSinDatos ? " (sin datos)" : ""}`;
  return (
    <div
      ref={refTarjeta}
      className="overflow-hidden rounded-tremor-default pt-2 ring-1 ring-line"
      style={{ backgroundColor: FINANCIERO_SURFACE }}
    >
      <p className="text-center text-base font-bold text-ink">{titulo}</p>
      <ResponsiveContainer width="100%" aspect={aspecto}>
        <LineChart data={datos} margin={margin}>
          <XAxis
            dataKey="mes"
            tickFormatter={(v: string) => (datos.length > UMBRAL_MESES_ABREVIADOS ? abreviarMes(v) : v)}
            tick={{ fontSize: 13, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="number"
            domain={dominio}
            ticks={ticks}
            tickFormatter={(v: number) => formatUSD(v)}
            tick={{ fontSize: 12, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
            width={anchoEjeY}
          />
          <Tooltip
            formatter={(v: number) => formatUSD(v)}
            contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
            labelStyle={{ color: "rgb(var(--color-ink))" }}
          />
          {!anioAnteriorSinDatos && (
            <Line
              type="linear"
              dataKey="cif_anio_anterior"
              name={etiquetaAnterior}
              stroke={COLOR_ANIO_ANTERIOR_CIF}
              strokeWidth={3}
              dot={{ r: 5, fill: COLOR_ANIO_ANTERIOR_CIF }}
              isAnimationActive={false}
            />
          )}
          <Line
            type="linear"
            dataKey="cif_anio_actual"
            name={String(anioActual)}
            stroke={COLOR_ANIO_ACTUAL_CIF}
            strokeWidth={3}
            dot={{ r: 5, fill: COLOR_ANIO_ACTUAL_CIF }}
            isAnimationActive={false}
          />
          {/* Capa de etiquetas dibujada AL FINAL (Customized siempre
              renderiza por encima de todas las series) -- antes cada
              caja era hija de su propia <Line>, así que una línea
              dibujada DESPUÉS (más arriba en el orden del JSX) podía
              tachar la etiqueta de la línea anterior al cruzarla
              (confirmado: Comparativo 2026 Gremiagro, Julio,
              "$3,871,197"). Las posiciones se recalculan con las MISMAS
              escalas analíticas que ya usa calcularPosicionesEtiquetas,
              no con props.x/y de Recharts (que ya no vienen por acá). */}
          <Customized
            component={() => (
              <g>
                {!anioAnteriorSinDatos &&
                  datos.map((d, i) => {
                    if (d.cif_anio_anterior === null) return null;
                    return (
                      <EtiquetaCajaCIF
                        key={`ant-${i}`}
                        x={escalaX(i)}
                        y={escalaY(d.cif_anio_anterior)}
                        value={d.cif_anio_anterior}
                        color={COLOR_ANIO_ANTERIOR_CIF}
                        gutterIzquierdo={gutterIzquierdo}
                        gutterDerecho={gutterDerecho}
                        esClaro={esClaro}
                        desplazamientoY={posiciones.anterior[i]}
                      />
                    );
                  })}
                {datos.map((d, i) => (
                  <EtiquetaCajaCIF
                    key={`act-${i}`}
                    x={escalaX(i)}
                    y={escalaY(d.cif_anio_actual)}
                    value={d.cif_anio_actual}
                    color={COLOR_ANIO_ACTUAL_CIF}
                    gutterIzquierdo={gutterIzquierdo}
                    gutterDerecho={gutterDerecho}
                    esClaro={esClaro}
                    desplazamientoY={posiciones.actual[i]}
                  />
                ))}
              </g>
            )}
          />
        </LineChart>
      </ResponsiveContainer>
      <LeyendaCentrada
        anchoTarjeta={anchoTarjeta}
        gutterIzquierdo={gutterIzquierdo}
        gutterDerecho={margin.right}
        items={[
          { etiqueta: etiquetaAnterior, color: COLOR_ANIO_ANTERIOR_CIF },
          { etiqueta: String(anioActual), color: COLOR_ANIO_ACTUAL_CIF },
        ]}
      />
    </div>
  );
}

// --- Gráfica de líneas de precio acumulado (Agrequima/Gremiagro/Total) ---

const COLOR_PRECIO_AGREQUIMA = "#2C786C";
const COLOR_PRECIO_GREMIAGRO = "#4DB6AC";
const COLOR_PRECIO_TOTAL = "#3182BD";
// El eje Y de esta gráfica (antes fijo 4-12) se calcula de los datos que
// muestra (utils/escalaEje.ts) dentro de GraficoPrecioLineas.

function EtiquetaCajaPrecio({
  x,
  y,
  value,
  color,
  esClaro,
  gutterIzquierdo,
  gutterDerecho,
}: LabelProps & { color: string; esClaro: boolean; gutterIzquierdo?: number; gutterDerecho?: number }) {
  if (typeof x !== "number" || typeof y !== "number" || typeof value !== "number") return null;
  const texto = value.toFixed(2);
  const ancho = Math.max(36, texto.length * 8);
  const xCaja = calcularXCaja(x, ancho, gutterIzquierdo, gutterDerecho);
  return (
    <g>
      <rect
        x={xCaja}
        y={y - 30}
        width={ancho}
        height={18}
        rx={2}
        fill="white"
        stroke={esClaro ? color : "none"}
        strokeWidth={esClaro ? 1 : 0}
      />
      <text x={xCaja + ancho / 2} y={y - 17} textAnchor="middle" fontSize={11} fontWeight={700} fill={color}>
        {texto}
      </text>
    </g>
  );
}

function GraficoPrecioLineas({ titulo, datos }: { titulo: string; datos: PuntoPrecioMes[] }) {
  const { tema } = useTheme();
  const esClaro = tema === "Claro";
  const [refTarjeta, anchoTarjeta] = useAnchoElemento<HTMLDivElement>();
  const aspecto = calcularAspectoSvg(anchoTarjeta, PROPORCION_ALTO_ANCHO_IMPORTACION);
  const margin = { top: 30, right: 16, bottom: 22, left: 4 };
  const anchoEjeYPrecio = 32;
  const gutterIzquierdo = margin.left + anchoEjeYPrecio;
  const gutterDerecho = anchoTarjeta ? anchoTarjeta - margin.right : undefined;
  const altoSvg = anchoTarjeta ? anchoTarjeta / aspecto : 0;
  const escalaPrecio = calcularEscalaEje(datos.flatMap((d) => [d.agrequima, d.gremiagro, d.total]));
  const { escalaX, escalaY } = crearEscalas(datos.length, escalaPrecio.dominio, anchoTarjeta, altoSvg, margin, gutterIzquierdo);
  return (
    <div
      ref={refTarjeta}
      className="overflow-hidden rounded-tremor-default pt-2 ring-1 ring-line"
      style={{ backgroundColor: FINANCIERO_SURFACE }}
    >
      <p className="text-center text-base font-bold text-ink">{titulo}</p>
      <ResponsiveContainer width="100%" aspect={aspecto}>
        <LineChart data={datos} margin={margin}>
          <XAxis
            dataKey="mes"
            tickFormatter={(v: string) => (datos.length > UMBRAL_MESES_ABREVIADOS ? abreviarMes(v) : v)}
            tick={{ fontSize: 12, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="number"
            domain={escalaPrecio.dominio}
            ticks={escalaPrecio.ticks}
            tickFormatter={(v: number) => (Number.isInteger(v) ? v.toFixed(0) : v.toFixed(1))}
            tick={{ fontSize: 12, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
            width={anchoEjeYPrecio}
          />
          <Tooltip
            formatter={(v: number) => formatUSD2(v)}
            contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
            labelStyle={{ color: "rgb(var(--color-ink))" }}
          />
          <Line type="linear" dataKey="agrequima" name="Agrequima" stroke={COLOR_PRECIO_AGREQUIMA} strokeWidth={3} dot={{ r: 4, fill: COLOR_PRECIO_AGREQUIMA }} isAnimationActive={false} />
          <Line type="linear" dataKey="gremiagro" name="Gremiagro" stroke={COLOR_PRECIO_GREMIAGRO} strokeWidth={3} dot={{ r: 4, fill: COLOR_PRECIO_GREMIAGRO }} isAnimationActive={false} />
          <Line type="linear" dataKey="total" name="Total" stroke={COLOR_PRECIO_TOTAL} strokeWidth={3} dot={{ r: 4, fill: COLOR_PRECIO_TOTAL }} isAnimationActive={false} />
          {/* Capa de etiquetas al final -- ver el mismo comentario en
              GraficoCIFLineas: así ninguna línea dibujada después tacha
              la caja de una serie anterior. */}
          <Customized
            component={() => (
              <g>
                {datos.map((d, i) => (
                  <EtiquetaCajaPrecio key={`agre-${i}`} x={escalaX(i)} y={escalaY(d.agrequima)} value={d.agrequima} color={COLOR_PRECIO_AGREQUIMA} esClaro={esClaro} gutterIzquierdo={gutterIzquierdo} gutterDerecho={gutterDerecho} />
                ))}
                {datos.map((d, i) => (
                  <EtiquetaCajaPrecio key={`grem-${i}`} x={escalaX(i)} y={escalaY(d.gremiagro)} value={d.gremiagro} color={COLOR_PRECIO_GREMIAGRO} esClaro={esClaro} gutterIzquierdo={gutterIzquierdo} gutterDerecho={gutterDerecho} />
                ))}
                {datos.map((d, i) => (
                  <EtiquetaCajaPrecio key={`total-${i}`} x={escalaX(i)} y={escalaY(d.total)} value={d.total} color={COLOR_PRECIO_TOTAL} esClaro={esClaro} gutterIzquierdo={gutterIzquierdo} gutterDerecho={gutterDerecho} />
                ))}
              </g>
            )}
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="flex items-center justify-center gap-6 pb-2 pt-1 text-sm font-bold text-ink">
        {[
          { color: COLOR_PRECIO_AGREQUIMA, etiqueta: "Agrequima" },
          { color: COLOR_PRECIO_GREMIAGRO, etiqueta: "Gremiagro" },
          { color: COLOR_PRECIO_TOTAL, etiqueta: "Total" },
        ].map((it) => (
          <span key={it.etiqueta} className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: it.color }} />
            {it.etiqueta}
          </span>
        ))}
      </div>
    </div>
  );
}

// --- 1. Ingresos por importación ------------------------------------------

const ANCHO_GRAFICA_1 = "78.4%"; // 1300/1658
const ANCHO_TABLA_1 = "46.6%"; // 773/1658

// Separaciones verticales reales del Layout, expresadas como % del
// ancho de contenido (1658px @ canvas 1920px) -- el mismo truco de
// margin-% ya usado en Presupuestos. Título -> primer elemento usa
// ahora GAP_TITULO_PRIMER_ELEMENTO (40.2px, TablaGrupoExpandible.tsx),
// igual en las 17 vistas del Financiero -- reemplaza el "4.6% / 76px"
// que se calculaba solo para esta pantalla.
const GAP_GRAFICA1_GRAFICA2 = "1.3%"; // 21px
const GAP_GRAFICA2_TABLA = "1.6%"; // 27px

// El eje Y de la gráfica CIF de esta pantalla (Agrequima+Gremiagro) se
// calcula de los datos que muestra (antes fijo 12,000,000-34,000,000,
// que dejaba fuera cualquier valor fuera de ese rango).

function PaginaIngresosImportacion() {
  const [data, setData] = useState<IngresosImportacionResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Grupo 2 (solo Año, sincronizado con "Ingresos por importación
  // comparativo") -- ver FinancieroFilterContext.
  const { anio, setAnio } = useFinancieroFilterGrupo2();

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerIngresosImportacion(anio ? Number(anio) : undefined)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        if (!anio) setAnio(String(res.anio));
      })
      .catch((err) => {
        if (!cancelado) setError(mensajeError(err));
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anio]);

  if (error) {
    return <p className="rounded-tremor-small bg-danger-surface px-4 py-3 text-sm text-danger">{error}</p>;
  }

  const anioOpciones = data?.anios_disponibles ?? [];
  const tituloPagina = data
    ? `Comparativo CIF US$ ${data.anio_anterior} vs. ${data.anio} Agrequima-Gremiagro`
    : "Ingresos por importación";
  const tituloGrafico = "Comparativo CIF US$ Importaciones Plaguicidas (Expresado en Miles de US$)";
  const escalaCif = calcularEscalaEje((data?.grafico_cif ?? []).flatMap((d) => [d.cif_anio_anterior, d.cif_anio_actual]));
  const tituloPrecio = data
    ? `Comportamiento acumulado a ${MESES_LARGOS[data.ultimo_mes_con_datos - 1]} ${data.anio}, precio kilolitro en US$.`
    : "";

  return (
    <div>
      <div className="relative flex min-h-[40px] items-center justify-center">
        <Title className="px-4 text-center text-2xl font-bold text-ink">{tituloPagina}</Title>
        <div className="absolute right-0 top-0">
          <FilterYear label="Año" anio={anio} onChangeAnio={setAnio} aniosOpciones={anioOpciones.map(String)} theme="gris" anchoFijo />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          <div className="mx-auto" style={{ width: ANCHO_GRAFICA_1, marginTop: GAP_TITULO_PRIMER_ELEMENTO }}>
            <GraficoCIFLineas
              titulo={tituloGrafico}
              datos={data.grafico_cif}
              anioAnterior={data.anio_anterior}
              anioActual={data.anio}
              dominioY={escalaCif.dominio}
              ticksY={escalaCif.ticks}
              anioAnteriorSinDatos={data.anio_anterior_sin_datos}
              proporcionAltoAncho={PROPORCION_ALTO_ANCHO_IMPORTACION}
            />
          </div>
          <div className="mx-auto" style={{ width: ANCHO_GRAFICA_1, marginTop: GAP_GRAFICA1_GRAFICA2 }}>
            <GraficoPrecioLineas titulo={tituloPrecio} datos={data.grafico_precio} />
          </div>
          <div className="mx-auto" style={{ width: ANCHO_TABLA_1, marginTop: GAP_GRAFICA2_TABLA }}>
            <TablaCIFMes filas={data.filas} filaTotal={data.fila_total} anioAnterior={data.anio_anterior} anioActual={data.anio} />
          </div>
        </>
      )}
    </div>
  );
}

// --- 2. Ingresos por importación comparativo ------------------------------

// Sin título general de página (la página real del .pbix NO lo tiene --
// los títulos son los de cada bloque). Separaciones reales del Layout:
// Ajustado a pedido explícito del usuario (el % del Layout, ~170px en
// las capturas reales, dejaba un hueco enorme entre el título de cada
// bloque y su tabla/gráfica): 24px fijos título -> contenido, 40px fijos
// entre el final de un bloque y el título del siguiente.
const GAP_TITULO_BLOQUE = "24px";
const GAP_ENTRE_BLOQUES = "40px";

// Sin dominio fijo: el usuario decidió que estas 2 gráficas se aparten
// de Power BI (que arranca en $0) y ajusten el eje a los datos reales,
// recalculado por GraficoCIFLineas en cada render vía calcularDominioNice
// -- ver ese componente.

function BloqueComparativo({
  bloque,
  anioAnterior,
  anioActual,
  marginTop,
}: {
  bloque: BloqueComparativoInstitucion;
  anioAnterior: number;
  anioActual: number;
  marginTop?: string;
}) {
  const anchoTabla = bloque.institucion === "Gremiagro" ? "47.3%" : "47.2%";
  return (
    <div style={{ marginTop }}>
      <Title className="text-center text-3xl font-bold text-ink">{bloque.titulo}</Title>
      <div className="flex flex-wrap items-stretch justify-center gap-4" style={{ marginTop: GAP_TITULO_BLOQUE }}>
        <div style={{ width: anchoTabla, minWidth: 320 }}>
          <TablaCIFMes filas={bloque.filas} filaTotal={bloque.fila_total} anioAnterior={anioAnterior} anioActual={anioActual} alturaCompleta />
        </div>
        <div style={{ width: "49.3%", minWidth: 320 }}>
          <GraficoCIFLineas
            titulo="Comparativo CIF US$ Importaciones Plaguicidas (Expresado en Miles de US$)"
            datos={bloque.grafico}
            anioAnterior={anioAnterior}
            anioActual={anioActual}
            anioAnteriorSinDatos={bloque.anio_anterior_sin_datos}
          />
        </div>
      </div>
    </div>
  );
}

function PaginaIngresosImportacionComparativo() {
  const [data, setData] = useState<ImportacionComparativoResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { anio, setAnio } = useFinancieroFilterGrupo2();

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerIngresosImportacionComparativo(anio ? Number(anio) : undefined)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        if (!anio) setAnio(String(res.anio));
      })
      .catch((err) => {
        if (!cancelado) setError(mensajeError(err));
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anio]);

  if (error) {
    return <p className="rounded-tremor-small bg-danger-surface px-4 py-3 text-sm text-danger">{error}</p>;
  }

  const anioOpciones = data?.anios_disponibles ?? [];

  return (
    <div>
      {/* Sin <Title> de página (la real no lo tiene) -- se conserva el
          renglón de cabecera (misma altura mínima) para que el filtro
          quede en la MISMA posición/esquina que en las demás pantallas. */}
      <div className="relative flex min-h-[40px] items-center justify-center">
        <div className="absolute right-0 top-0">
          <FilterYear label="Año" anio={anio} onChangeAnio={setAnio} aniosOpciones={anioOpciones.map(String)} theme="gris" anchoFijo />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <div style={{ marginTop: GAP_TITULO_PRIMER_ELEMENTO }}>
          {/* Sin título visible en esta pantalla, pero el renglón de
              cabecera arriba (min-h-[40px]) tiene la misma altura que el
              de las demás -- se le aplica el mismo GAP_TITULO_PRIMER_ELEMENTO
              (40.2px) para que las 17 vistas queden con la misma
              separación, según lo pedido explícitamente en esta ronda. */}
          {data.bloques.map((b, i) => (
            <BloqueComparativo
              key={b.institucion}
              bloque={b}
              anioAnterior={data.anio_anterior}
              anioActual={data.anio}
              marginTop={i === 0 ? undefined : GAP_ENTRE_BLOQUES}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// --- 3. Comparación importaciones Kilolitros -------------------------------

const ANCHO_KILOLITROS = "97.7%"; // 1620/1658
// Alto de cada tarjeta de mensaje == 9% de SU PROPIO ancho (h=150/w=1620
// del Layout) -- usando aspect-ratio (no height:%, que resuelve contra el
// alto del ancestro, no su ancho) da el alto correcto a cualquier tamaño
// de pantalla sin medir nada en JS.
const ASPECTO_TARJETA_KILOLITROS = "1620 / 150";
// Ancho del cuadro de precios: 648/1658 del Layout, centrado.
const ANCHO_CUADRO_PRECIOS = "39.1%";
// Proporción de columnas DENTRO del cuadro (132 : 184 : 184 : 148 = 648).
const ANCHOS_COLUMNA_PRECIO = ["20.4%", "28.4%", "28.4%", "22.8%"];
const GRIS_OSCURO_CELDA = "#444444"; // mismo gris que FINANCIERO_SURFACE en oscuro (Power BI)
const GAP_TARJETAS_TITULO2 = "5.8%"; // 96px (3ra tarjeta y=639+150=789 -> título y=885)

function TarjetaCambio({ mensaje }: { mensaje: string }) {
  return (
    <div
      className="flex items-center justify-center rounded-tremor-default px-4 text-center text-lg font-bold text-ink ring-1 ring-line"
      style={{ backgroundColor: FINANCIERO_SURFACE, aspectRatio: ASPECTO_TARJETA_KILOLITROS }}
    >
      {mensaje}
    </div>
  );
}

function FilaTablaKilolitro({ fila }: { fila: FilaPrecioKilolitro }) {
  // Celdas SUELTAS (sin contenedor general) -- cada valor es su propia
  // caja gris oscuro redondeada, separada por el `border-spacing` de la
  // tabla (ver PaginaKilolitros). Nada de fondo/borde por fuera.
  const claseValor = "rounded-sm px-3 py-2 text-right text-sm font-bold text-white";
  return (
    <tr>
      <td className="p-0">
        <span className="block w-full rounded-sm px-2 py-1.5 text-center text-sm font-bold text-white" style={{ backgroundColor: VERDE_ENCABEZADO }}>
          {fila.etiqueta}
        </span>
      </td>
      <td className={claseValor} style={{ backgroundColor: GRIS_OSCURO_CELDA }}>
        {fila.precio_anio_anterior === null ? "—" : formatUSD2(fila.precio_anio_anterior)}
      </td>
      <td className={claseValor} style={{ backgroundColor: GRIS_OSCURO_CELDA }}>
        {fila.precio_anio_actual === null ? "—" : formatUSD2(fila.precio_anio_actual)}
      </td>
      <td className={claseValor} style={{ backgroundColor: GRIS_OSCURO_CELDA }}>
        {fila.variacion_pct === null ? "—" : formatPercentEntero(fila.variacion_pct)}
      </td>
    </tr>
  );
}

function PaginaKilolitros() {
  const [data, setData] = useState<KilolitrosResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Grupo 1 (Año+Mes sincronizado) -- ver FinancieroFilterContext.
  const { anio, mes, cambiarAnio, cambiarMes, setAnioMes } = useFinancieroFilterGrupo1(data?.periodos_disponibles ?? []);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerKilolitros(anio ? Number(anio) : undefined, mes ? Number(mes) : undefined)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        if (!anio || !mes) setAnioMes(String(res.anio), String(res.mes));
      })
      .catch((err) => {
        if (!cancelado) setError(mensajeError(err));
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anio, mes]);

  if (error) {
    return <p className="rounded-tremor-small bg-danger-surface px-4 py-3 text-sm text-danger">{error}</p>;
  }

  const periodos = data?.periodos_disponibles ?? [];
  const aniosDisponibles = Array.from(new Set(periodos.map((p) => p.anio))).sort((a, b) => a - b);
  const mesesDelAnio = periodos
    .filter((p) => String(p.anio) === anio)
    .map((p) => p.mes)
    .sort((a, b) => a - b);

  const tituloPagina = data
    ? `Comparativos Importaciones Kilolitros Acumulado al mes de ${MESES_LARGOS[data.mes - 1]} Año ${data.anio_anterior} vrs ${data.anio}`
    : "Comparación importaciones Kilolitros";
  const tituloPrecio = data
    ? `Promedio Importaciones Precio por Kilolitro en USD Acumulado al mes de ${MESES_LARGOS[data.mes - 1]} año ${data.anio_anterior} y ${data.anio}`
    : "";

  return (
    <div>
      <div className="relative flex min-h-[40px] items-center justify-center">
        {/* text-2xl (antes text-xl) -- unificado con el resto de las 14
            pantallas del módulo (ronda de estandarización). */}
        <Title className="px-4 text-center text-2xl font-bold text-ink">{tituloPagina}</Title>
        <div className="absolute right-0 top-0">
          <FilterYearMonth
            label="Año y Mes"
            anio={anio}
            mes={mes}
            onChangeAnio={cambiarAnio}
            onChangeMes={cambiarMes}
            aniosOpciones={aniosDisponibles.map(String)}
            mesesOpciones={mesesDelAnio.map((m) => ({ value: String(m), label: MESES_LARGOS[m - 1] }))}
            theme="gris"
            anchoFijo
          />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          <div className="mx-auto space-y-3" style={{ width: ANCHO_KILOLITROS, marginTop: GAP_TITULO_PRIMER_ELEMENTO }}>
            {data.tarjetas.map((t) => (
              <TarjetaCambio key={t.etiqueta} mensaje={t.mensaje} />
            ))}
          </div>

          <Title className="text-center text-xl font-bold text-ink" style={{ marginTop: GAP_TARJETAS_TITULO2 }}>
            {tituloPrecio}
          </Title>

          {/* Sin contenedor: en Power BI son celdas sueltas sobre el fondo
              de la página, no una tabla con marco. `border-spacing` (en
              vez de padding/gap) separa cada celda 3px de las demás,
              dejando la esquina superior izquierda (sobre las etiquetas)
              vacía y transparente. */}
          <div className="mx-auto" style={{ width: ANCHO_CUADRO_PRECIOS, minWidth: 340, marginTop: "1.5%" }}>
            <table className="w-full text-sm" style={{ borderCollapse: "separate", borderSpacing: 3 }}>
              <colgroup>
                {ANCHOS_COLUMNA_PRECIO.map((a, i) => (
                  <col key={i} style={{ width: a }} />
                ))}
              </colgroup>
              <thead>
                <tr>
                  <th className="px-3 py-3" />
                  {/* Alineado a la derecha (antes centrado) -- misma
                      columna que las celdas de datos (claseValor,
                      text-right en FilaTablaKilolitro), regla de
                      encabezados de esta ronda. */}
                  <th className="rounded-sm px-3 py-3 text-right text-xs font-normal leading-tight text-white" style={{ backgroundColor: VERDE_ENCABEZADO }}>
                    Año {data.anio_anterior} al mes de {MESES_LARGOS[data.mes - 1]}
                  </th>
                  <th className="rounded-sm px-3 py-3 text-right text-xs font-normal leading-tight text-white" style={{ backgroundColor: VERDE_ENCABEZADO }}>
                    Año {data.anio} al mes de {MESES_LARGOS[data.mes - 1]}
                  </th>
                  <th className="rounded-sm px-3 py-3 text-right text-xs font-normal leading-tight text-white" style={{ backgroundColor: VERDE_ENCABEZADO }}>
                    Variación porcentual
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.filas_precio.map((f) => (
                  <FilaTablaKilolitro key={f.etiqueta} fila={f} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// --- 4. Ingresos por contribución 4.5 por millar --------------------------

// Ancho EXACTO del conjunto de las 2 gráficas de barras (borde izquierdo
// de la primera a borde derecho de la segunda) -- la gráfica de líneas
// de arriba tiene que medir lo MISMO, para que ambos bordes coincidan.
// 700/1658 + 139/1658 (hueco) + 700/1658 = 1539/1658 = 92.8%.
const ANCHO_GRAFICA_4 = "92.8%";
const ANCHO_COLUMNAS_4 = "42.2%"; // 700/1658
const GAP_COLUMNAS_4 = "8.4%"; // 139/1658 -- hueco real entre las 2 barras
const GAP_LINEAS_COLUMNAS_4 = "3.5%"; // 58px/1658
const PROPORCION_ALTO_ANCHO_LINEAS_4 = 0.3;
const PROPORCION_ALTO_ANCHO_BARRAS_4 = 0.5;
const COLOR_CONTRIB_ANTERIOR = "#5B7FAE";
const COLOR_CONTRIB_ACTUAL = "#43B0A6";

function EtiquetaCajaContribucion({
  x,
  y,
  value,
  color,
  esClaro,
  gutterIzquierdo,
  gutterDerecho,
}: LabelProps & { color: string; esClaro: boolean; gutterIzquierdo?: number; gutterDerecho?: number }) {
  if (typeof x !== "number" || typeof y !== "number" || typeof value !== "number") return null;
  const texto = formatQ(value);
  const ancho = Math.max(60, texto.length * 8.5);
  const xCaja = calcularXCaja(x, ancho, gutterIzquierdo, gutterDerecho);
  return (
    <g>
      <rect
        x={xCaja}
        y={y - 30}
        width={ancho}
        height={18}
        rx={2}
        fill="white"
        stroke={esClaro ? color : "none"}
        strokeWidth={esClaro ? 1 : 0}
      />
      <text x={xCaja + ancho / 2} y={y - 17} textAnchor="middle" fontSize={11} fontWeight={700} fill={color}>
        {texto}
      </text>
    </g>
  );
}

function GraficoContribucionLineas({
  titulo,
  datos,
  anioAnterior,
  anioActual,
}: {
  titulo: string;
  datos: PuntoContribucionMes[];
  anioAnterior: number;
  anioActual: number;
}) {
  const { tema } = useTheme();
  const esClaro = tema === "Claro";
  const hayPresupuesto = datos.some((d) => d.presupuesto !== 0);
  const etiquetaPresupuesto = `Presupuesto ${anioActual}${hayPresupuesto ? "" : " (sin datos)"}`;
  const [refTarjeta, anchoTarjeta] = useAnchoElemento<HTMLDivElement>();
  const margin = { top: 30, right: 24, bottom: 22, left: 16 };
  const anchoEjeYContrib = 80;
  const gutterIzquierdo = margin.left + anchoEjeYContrib;
  const gutterDerecho = anchoTarjeta ? anchoTarjeta - margin.right : undefined;
  const aspecto = calcularAspectoSvg(anchoTarjeta, PROPORCION_ALTO_ANCHO_LINEAS_4);
  const altoSvg = anchoTarjeta ? anchoTarjeta / aspecto : 0;
  // Dominio explícito (calcularDominioNice) en vez de domain={["auto",
  // "auto"]}: la capa de etiquetas (Customized, ver GraficoCIFLineas)
  // necesita conocer el dominio EXACTO que usa el eje para calcular la
  // posición Y de cada caja -- con "auto" no hay forma de saber qué
  // dominio resolvió Recharts internamente antes de renderizar.
  const valoresDominio = datos.flatMap((d) => (hayPresupuesto ? [d.anio_anterior, d.anio_actual, d.presupuesto] : [d.anio_anterior, d.anio_actual]));
  const { dominio, ticks } = calcularDominioNice(valoresDominio);
  const { escalaX, escalaY } = crearEscalas(datos.length, dominio, anchoTarjeta, altoSvg, margin, gutterIzquierdo);
  return (
    <div ref={refTarjeta} className="overflow-hidden rounded-tremor-default pt-2 ring-1 ring-line" style={{ backgroundColor: FINANCIERO_SURFACE }}>
      <p className="text-center text-base font-bold text-ink">{titulo}</p>
      <ResponsiveContainer width="100%" aspect={aspecto}>
        <LineChart data={datos} margin={margin}>
          <XAxis
            dataKey="mes"
            tickFormatter={(v: string) => (datos.length > UMBRAL_MESES_ABREVIADOS ? abreviarMes(v) : v)}
            tick={{ fontSize: 12, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="number"
            domain={dominio}
            ticks={ticks}
            tickFormatter={(v: number) => formatQ(v)}
            tick={{ fontSize: 12, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
            width={anchoEjeYContrib}
          />
          <Tooltip
            formatter={(v: number) => formatQ(v)}
            contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }}
            labelStyle={{ color: "rgb(var(--color-ink))" }}
          />
          <Line type="linear" dataKey="anio_anterior" name={String(anioAnterior)} stroke={COLOR_CONTRIB_ANTERIOR} strokeWidth={3} dot={{ r: 4, fill: COLOR_CONTRIB_ANTERIOR }} isAnimationActive={false} />
          <Line type="linear" dataKey="anio_actual" name={String(anioActual)} stroke={COLOR_CONTRIB_ACTUAL} strokeWidth={3} dot={{ r: 4, fill: COLOR_CONTRIB_ACTUAL }} isAnimationActive={false} />
          {hayPresupuesto && (
            <Line type="linear" dataKey="presupuesto" name={etiquetaPresupuesto} stroke={COLOR_PRESUPUESTO} strokeWidth={3} dot={{ r: 4, fill: COLOR_PRESUPUESTO }} isAnimationActive={false} />
          )}
          {/* Capa de etiquetas al final -- ver el mismo comentario en
              GraficoCIFLineas. */}
          <Customized
            component={() => (
              <g>
                {datos.map((d, i) => (
                  <EtiquetaCajaContribucion key={`ant-${i}`} x={escalaX(i)} y={escalaY(d.anio_anterior)} value={d.anio_anterior} color={COLOR_CONTRIB_ANTERIOR} esClaro={esClaro} gutterIzquierdo={gutterIzquierdo} gutterDerecho={gutterDerecho} />
                ))}
                {datos.map((d, i) => (
                  <EtiquetaCajaContribucion key={`act-${i}`} x={escalaX(i)} y={escalaY(d.anio_actual)} value={d.anio_actual} color={COLOR_CONTRIB_ACTUAL} esClaro={esClaro} gutterIzquierdo={gutterIzquierdo} gutterDerecho={gutterDerecho} />
                ))}
                {hayPresupuesto &&
                  datos.map((d, i) => (
                    <EtiquetaCajaContribucion key={`pre-${i}`} x={escalaX(i)} y={escalaY(d.presupuesto)} value={d.presupuesto} color={COLOR_PRESUPUESTO} esClaro={esClaro} gutterIzquierdo={gutterIzquierdo} gutterDerecho={gutterDerecho} />
                  ))}
              </g>
            )}
          />
        </LineChart>
      </ResponsiveContainer>
      {/* Orden pedido: {Año-1}, {Año}, Presupuesto {Año} -- Presupuesto
          siempre al final, aunque no tenga datos (se muestra igual, con
          "(sin datos)"). */}
      <div className="flex items-center justify-center gap-6 pb-2 pt-1 text-sm font-bold text-ink">
        {[
          { color: COLOR_CONTRIB_ANTERIOR, etiqueta: String(anioAnterior) },
          { color: COLOR_CONTRIB_ACTUAL, etiqueta: String(anioActual) },
          { color: COLOR_PRESUPUESTO, etiqueta: etiquetaPresupuesto },
        ].map((it) => (
          <span key={it.etiqueta} className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: it.color }} />
            {it.etiqueta}
          </span>
        ))}
      </div>
    </div>
  );
}

function ChipEjecucion({ porcentaje }: { porcentaje: number | null }) {
  return (
    <span className="rounded px-2 py-0.5 text-xs font-semibold" style={{ backgroundColor: FINANCIERO_SURFACE }}>
      {porcentaje === null ? "Sin presupuesto" : `${porcentaje.toFixed(2)}%`}
    </span>
  );
}

function GraficoColumnasContribucion({
  titulo,
  presupuesto,
  realizado,
  porcentajeEjecucion,
}: {
  titulo: string;
  presupuesto: number;
  realizado: number;
  porcentajeEjecucion: number | null;
}) {
  const fila = [{ presupuesto, realizado }];
  const [refTarjeta, anchoTarjeta] = useAnchoElemento<HTMLDivElement>();
  const barSize = anchoTarjeta ? Math.round(anchoTarjeta * 0.12) : undefined;
  // Eje Y calculado de los 2 valores que muestra, con margen sobre el más
  // alto (la etiqueta de la barra más alta no debe quedar pegada contra el
  // chip de % de ejecución -- caso real: Q4,011,995 con tope Q4,200,000,
  // solo 4.5% de aire) y sin paso escrito a mano (antes saltos fijos de
  // Q200,000).
  const escala = calcularEscalaEje([presupuesto, realizado]);
  const anchoEjeY = calcularAnchoEjeY(escala.ticks.map((v) => formatQ(v)));
  const hayPresupuesto = presupuesto !== 0;
  const gutterIzquierdo = 16 + anchoEjeY;
  const gutterDerecho = 16;
  const aspecto = calcularAspectoSvg(anchoTarjeta, PROPORCION_ALTO_ANCHO_BARRAS_4);
  return (
    <div
      ref={refTarjeta}
      className="relative overflow-hidden rounded-tremor-default pt-2 ring-1 ring-line"
      style={{ backgroundColor: FINANCIERO_SURFACE }}
    >
      <p className="px-2 text-center text-base font-bold text-ink">{titulo}</p>
      {/* El chip va DEBAJO de la línea del título (no en la misma fila) --
          el título centrado ocupa casi todo el ancho de la tarjeta, así
          que un chip en la MISMA fila (arriba a la derecha) quedaba
          encima del propio texto del título (confirmado con captura
          real). */}
      <div className="absolute right-2 top-9">
        <ChipEjecucion porcentaje={porcentajeEjecucion} />
      </div>
      <ResponsiveContainer width="100%" aspect={aspecto}>
        <BarChart data={fila} margin={{ top: 44, right: gutterDerecho, bottom: 4, left: 16 }} barGap={4}>
          <XAxis dataKey={() => ""} tick={false} axisLine={false} tickLine={false} />
          <YAxis
            type="number"
            domain={escala.dominio}
            ticks={escala.ticks}
            tickFormatter={(v: number) => formatQ(v)}
            tick={{ fontSize: 12, fontWeight: 700, fill: "rgb(var(--color-ink))" }}
            axisLine={false}
            tickLine={false}
            width={anchoEjeY}
          />
          <Tooltip formatter={(v: number) => formatQ(v)} contentStyle={{ background: FINANCIERO_SURFACE, border: "1px solid rgb(var(--color-line))", borderRadius: 8 }} />
          <Bar dataKey="presupuesto" fill={hayPresupuesto ? COLOR_PRESUPUESTO : "transparent"} radius={[4, 4, 0, 0]} isAnimationActive={false} barSize={barSize}>
            {hayPresupuesto ? (
              <LabelList dataKey="presupuesto" content={(props) => <TextoValorBarra {...props} color="rgb(var(--color-ink))" />} />
            ) : (
              <LabelList dataKey="presupuesto" content={(props) => <TextoSinPresupuesto {...props} />} />
            )}
          </Bar>
          <Bar dataKey="realizado" fill={COLOR_EJECUTADO} radius={[4, 4, 0, 0]} isAnimationActive={false} barSize={barSize}>
            <LabelList dataKey="realizado" content={(props) => <TextoValorBarra {...props} color="rgb(var(--color-ink))" />} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <LeyendaCentrada
        anchoTarjeta={anchoTarjeta}
        gutterIzquierdo={gutterIzquierdo}
        gutterDerecho={gutterDerecho}
        items={[
          { etiqueta: hayPresupuesto ? "Presupuesto" : "Presupuesto (sin datos)", color: COLOR_PRESUPUESTO },
          { etiqueta: "Realizado", color: COLOR_EJECUTADO },
        ]}
      />
    </div>
  );
}

// Etiqueta de valor completo (Q535,038) encima de la barra, y "Sin
// presupuesto" en su lugar cuando esa serie no tiene datos (la barra
// queda con altura 0 pero el ESPACIO de su categoría se conserva).
function TextoValorBarra({
  x,
  width,
  y,
  value,
  color,
}: {
  x?: number | string;
  width?: number | string;
  y?: number | string;
  value?: number | string;
  color: string;
}) {
  const xNum = Number(x);
  const wNum = Number(width);
  const yNum = Number(y);
  const vNum = Number(value);
  if (!Number.isFinite(xNum) || !Number.isFinite(wNum) || !Number.isFinite(yNum) || !Number.isFinite(vNum)) return null;
  return (
    <text x={xNum + wNum / 2} y={yNum - 6} textAnchor="middle" fontSize={14} fontWeight={700} fill={color}>
      {formatQ(vNum)}
    </text>
  );
}

function TextoSinPresupuesto({ x, width }: { x?: number | string; width?: number | string }) {
  const xNum = Number(x);
  const wNum = Number(width);
  if (!Number.isFinite(xNum) || !Number.isFinite(wNum)) return null;
  return (
    <text x={xNum + wNum / 2} y={34} textAnchor="middle" fontSize={12} fontWeight={700} fill="rgb(var(--color-ink-muted))">
      Sin presupuesto
    </text>
  );
}

function PaginaContribucionMillar() {
  // Independiente, sin sincronizar -- mismo componente visual Año/Mes
  // que las demás, pero con memoria propia dentro de la sesión (ver
  // FinancieroFilterContext): antes era estado local, que se perdía al
  // navegar a otra pantalla y volver.
  const { anio, mes, setAnioMes } = useFinancieroFilterContribucion();
  const [data, setData] = useState<ContribucionMillarResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerContribucionMillar(anio ? Number(anio) : undefined, mes ? Number(mes) : undefined)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setError(null);
        if (!anio || !mes) setAnioMes(anio || String(res.anio), mes || String(res.mes));
      })
      .catch((err) => {
        if (!cancelado) setError(mensajeError(err));
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anio, mes]);

  if (error) {
    return <p className="rounded-tremor-small bg-danger-surface px-4 py-3 text-sm text-danger">{error}</p>;
  }

  const periodos = data?.periodos_disponibles ?? [];
  const aniosDisponibles = Array.from(new Set(periodos.map((p) => p.anio))).sort((a, b) => a - b);
  const mesesDelAnio = periodos
    .filter((p) => String(p.anio) === anio)
    .map((p) => p.mes)
    .sort((a, b) => a - b);

  function cambiarAnio(nuevoAnio: string) {
    const mesesDelNuevoAnio = periodos.filter((p) => String(p.anio) === nuevoAnio).map((p) => p.mes);
    const nuevoMes = mesesDelNuevoAnio.includes(Number(mes)) ? mes : String(Math.max(...mesesDelNuevoAnio));
    setAnioMes(nuevoAnio, nuevoMes);
  }

  function cambiarMes(nuevoMes: string) {
    setAnioMes(anio, nuevoMes);
  }

  const tituloPagina = data ? `Ingresos Contribución 4.5 por millar ${MESES_LARGOS[data.mes - 1]} Año ${data.anio}` : "Ingresos Contribución 4.5 por millar";

  return (
    <div>
      <div className="relative flex min-h-[40px] items-center justify-center">
        <Title className="px-4 text-center text-2xl font-bold text-ink">{tituloPagina}</Title>
        <div className="absolute right-0 top-0">
          <FilterYearMonth
            label="Año y Mes"
            anio={anio}
            mes={mes}
            onChangeAnio={cambiarAnio}
            onChangeMes={cambiarMes}
            aniosOpciones={aniosDisponibles.map(String)}
            mesesOpciones={mesesDelAnio.map((m) => ({ value: String(m), label: MESES_LARGOS[m - 1] }))}
            theme="gris"
            anchoFijo
          />
        </div>
      </div>

      {cargando && !data && <p className="text-sm text-ink-muted">Cargando…</p>}

      {data && (
        <>
          <div className="mx-auto" style={{ width: ANCHO_GRAFICA_4, marginTop: GAP_TITULO_PRIMER_ELEMENTO }}>
            <GraficoContribucionLineas
              titulo="Contribución por importaciones (4.5 por millar) (Expresado en miles de quetzales)"
              datos={data.grafico}
              anioAnterior={data.anio - 1}
              anioActual={data.anio}
            />
          </div>

          <div className="flex flex-wrap justify-center" style={{ gap: GAP_COLUMNAS_4, marginTop: GAP_LINEAS_COLUMNAS_4 }}>
            <div style={{ width: ANCHO_COLUMNAS_4, minWidth: 320 }}>
              <GraficoColumnasContribucion
                titulo={`Ingresos Contribución 4.5 por millar del mes ${MESES_LARGOS[data.mes - 1]} Año ${data.anio}`}
                presupuesto={data.tarjeta_mes.presupuesto}
                realizado={data.tarjeta_mes.realizado}
                porcentajeEjecucion={data.tarjeta_mes.porcentaje_ejecucion}
              />
            </div>
            <div style={{ width: ANCHO_COLUMNAS_4, minWidth: 320 }}>
              <GraficoColumnasContribucion
                titulo={`Ingreso Contribución 4.5 por millar acumulado al ${ultimoDiaDelMes(data.anio, data.mes)} de ${MESES_LARGOS[data.mes - 1]} de ${data.anio}`}
                presupuesto={data.tarjeta_acumulada.presupuesto}
                realizado={data.tarjeta_acumulada.realizado}
                porcentajeEjecucion={data.tarjeta_acumulada.porcentaje_ejecucion}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// --- Router de la sub-sección "Importaciones" (del Financiero) -----------

const VISTAS = ["ingresos", "comparativo", "kilolitros", "contribucion-millar"] as const;

export function DashboardImportacionesFinancieroPage() {
  const [searchParams] = useSearchParams();
  const vistaParam = searchParams.get("vista") ?? "ingresos";
  const vista = VISTAS.includes(vistaParam as (typeof VISTAS)[number]) ? (vistaParam as (typeof VISTAS)[number]) : "ingresos";

  if (vista === "comparativo") return <PaginaIngresosImportacionComparativo />;
  if (vista === "kilolitros") return <PaginaKilolitros />;
  if (vista === "contribucion-millar") return <PaginaContribucionMillar />;
  return <PaginaIngresosImportacion />;
}

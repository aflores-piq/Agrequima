import { Fragment, useState } from "react";
import { formatQ } from "../utils/format";

// Verde exacto leído pixel a pixel del header de tabla / banda de
// resumen en las capturas reales del reporte viejo (ver
// docs/legacy/Financiero_capturas/) -- rgb(76,175,80).
export const VERDE_ENCABEZADO = "#4CAF50";

// Color de las ETIQUETAS de las tarjetas KPI (Ingresos/Egresos/Activo/
// Pasivo/etc. y el título de la tarjeta comparativa de página 4) --
// blanco puro por instrucción DIRECTA del usuario, no sujeto a lo
// medido en las capturas de referencia (que muestran un azul,
// rgb(68,149,208)/#4495D0 -- ese valor se usó en una ronda anterior y
// se descartó explícitamente a favor de este). Fijo (no reactivo al
// tema), igual que VERDE_ENCABEZADO.
export const COLOR_ETIQUETA_KPI = "#FFFFFF";

// Fondo de tarjetas/tablas/gráficos de Financiero -- variable de tema
// propia (--color-financiero-surface, ver index.css), NO un hex fijo:
// en oscuro es el gris neutro #444444 medido de la captura real de
// Power BI (visiblemente más claro que el fondo general de la app,
// para que las tarjetas se distingan), en claro es blanco -- igual que
// bg-surface, para que reaccione al tema como ya lo hace Plaguicidas/
// Nutrientes (antes era un hex fijo, se quedaba oscuro en modo claro).
export const FINANCIERO_SURFACE = "rgb(var(--color-financiero-surface))";

export interface FilaCuenta {
  nombre: string;
  valores: number[];
}

export interface FilaGrupo {
  grupo: string;
  valores: number[];
  cuentas: FilaCuenta[];
}

/** Tabla de detalle con encabezado como barra verde sólida (calcada de
 * las capturas reales) y filas de Grupo expandibles/colapsables que
 * muestran las Cuentas individuales debajo -- nivel que no existía
 * antes. La fila "Total" queda fija al final, en negrita, sin color. */
export function TablaGrupoExpandible({
  titulo,
  columnas,
  filas,
  etiquetaTotal,
  totalValores,
  formatters,
  anchoEtiqueta = "300px",
  anchosDatos,
  colorFondo = FINANCIERO_SURFACE,
}: {
  titulo: string;
  columnas: string[];
  filas: FilaGrupo[];
  etiquetaTotal: string;
  totalValores: number[];
  formatters?: ((v: number) => string)[];
  /** Ancho FIJO de la primera columna (nombre de grupo/cuenta) -- debe
   * ser el MISMO valor en todas las tablas de una misma página (ver
   * DashboardFinancieroPage), para que las columnas de datos ("Mayo",
   * "Junio", etc.) queden alineadas verticalmente entre la tabla de
   * Ingresos y la de Egresos (o Activo/Pasivo/Patrimonio) -- con un
   * ancho automático por tabla, cada una lo calcula distinto según el
   * nombre más largo de SUS propias filas y quedan desalineadas. */
  anchoEtiqueta?: string;
  /** Ancho explícito por columna de datos (mismo orden que `columnas`)
   * -- por defecto las 3 se reparten el espacio restante en partes
   * iguales; usar esto solo cuando una columna necesita más lugar que
   * las demás (ej. "Acumulado Año 2026", que si no se corta en 2 líneas). */
  anchosDatos?: string[];
  /** Override puntual del fondo -- sin uso hoy (las 4 páginas comparten
   * el mismo `FINANCIERO_SURFACE`, ver DashboardFinancieroPage), se deja
   * disponible por si una página futura necesita distinguirse. Se aplica
   * IGUAL a las filas de Cuenta expandidas, que antes tenían un overlay
   * semitransparente (`bg-black/20`) encima de este color, dándoles un
   * tono distinto al expandir -- ahora es el mismo color sólido, sin
   * overlay, para que no cambie de tono. */
  colorFondo?: string;
}) {
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set());

  function alternar(grupo: string) {
    setExpandidos((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(grupo)) siguiente.delete(grupo);
      else siguiente.add(grupo);
      return siguiente;
    });
  }

  const fmt = (v: number, i: number) => (formatters?.[i] ?? formatQ)(v);

  if (filas.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-faint">Sin datos para los filtros actuales.</p>;
  }

  return (
    // Ancho 100% del contenedor que le pasa la página -- el ~56% real
    // (medido directo del Layout.json del .pbix, ver DashboardFinancieroPage)
    // se aplica UNA sola vez en un wrapper compartido con la fila de KPIs,
    // no acá por separado: dos anchos iguales pero independientes podían
    // desalinearse entre sí al cambiar el ancho de pantalla.
    <div className="overflow-hidden rounded-tremor-default ring-1 ring-line">
      <div className="overflow-x-auto">
        <table className="w-full table-fixed text-sm">
          <colgroup>
            <col style={{ width: anchoEtiqueta }} />
            {columnas.map((_, i) => (
              <col key={i} style={anchosDatos?.[i] ? { width: anchosDatos[i] } : undefined} />
            ))}
          </colgroup>
          <thead>
            <tr style={{ backgroundColor: VERDE_ENCABEZADO }}>
              <th className="break-words px-3 py-2 text-left font-semibold text-white">{titulo}</th>
              {columnas.map((c) => (
                <th key={c} className="px-3 py-2 text-right font-semibold text-white">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody style={{ backgroundColor: colorFondo }}>
            {filas.map((f) => {
              const abierto = expandidos.has(f.grupo);
              return (
                <Fragment key={f.grupo}>
                  <tr className="border-b border-line/50 hover:bg-surface-hover/60">
                    <td className="break-words px-3 py-1.5 text-ink" title={f.grupo}>
                      <button
                        type="button"
                        onClick={() => alternar(f.grupo)}
                        className="mr-1.5 inline-flex h-4 w-4 items-center justify-center text-xs text-ink-muted"
                        aria-expanded={abierto}
                        aria-label={abierto ? `Contraer ${f.grupo}` : `Expandir ${f.grupo}`}
                      >
                        {abierto ? "⊟" : "⊞"}
                      </button>
                      {f.grupo}
                    </td>
                    {f.valores.map((v, i) => (
                      <td key={i} className="px-3 py-1.5 text-right text-ink">
                        {fmt(v, i)}
                      </td>
                    ))}
                  </tr>
                  {abierto &&
                    f.cuentas.map((c) => (
                      <tr key={`${f.grupo}__${c.nombre}`} className="border-b border-line/50" style={{ backgroundColor: colorFondo }}>
                        <td className="break-words px-3 py-1 pl-10 text-ink-muted" title={c.nombre}>
                          {c.nombre}
                        </td>
                        {c.valores.map((v, i) => (
                          <td key={i} className="px-3 py-1 text-right text-ink-muted">
                            {fmt(v, i)}
                          </td>
                        ))}
                      </tr>
                    ))}
                </Fragment>
              );
            })}
            <tr className="font-semibold text-ink">
              <td className="px-3 py-2">{etiquetaTotal}</td>
              {totalValores.map((v, i) => (
                <td key={i} className="px-3 py-2 text-right">
                  {fmt(v, i)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Banda de resumen final -- misma barra verde sólida que el
 * encabezado de tabla (Resultado del ejercicio / Total pasivo y
 * patrimonio). */
export function BandaResumenVerde({
  etiqueta,
  columnas,
  valores,
  formatters,
  anchoEtiqueta = "300px",
  anchosDatos,
}: {
  etiqueta: string;
  columnas: string[];
  valores: number[];
  formatters?: ((v: number) => string)[];
  /** Mismo ancho de primera columna que las tablas de la página (ver
   * TablaGrupoExpandible) para que sus columnas de datos queden
   * alineadas verticalmente con la banda de resumen. */
  anchoEtiqueta?: string;
  /** Mismo `anchosDatos` que TablaGrupoExpandible (ver ahí) -- debe
   * coincidir para que la banda quede alineada con las tablas de arriba. */
  anchosDatos?: string[];
}) {
  const fmt = (v: number, i: number) => (formatters?.[i] ?? formatQ)(v);
  return (
    // Ancho 100% del wrapper compartido (ver comentario en TablaGrupoExpandible).
    // Una sola fila, mismo padding de celda (px-3 py-2) que el <th> del
    // encabezado verde de TablaGrupoExpandible -- para que esta banda
    // mida EXACTAMENTE lo mismo de alto que esa fila (confirmado en la
    // captura real del .pbix: ambas miden igual). Antes tenía padding
    // extra en el wrapper (py-2.5) MÁS una 2da fila con "Mayo/Junio/..."
    // repitiendo las columnas -- esa leyenda no existe en el original,
    // y sumaba alto de más.
    <div className="overflow-x-auto rounded-tremor-default text-white" style={{ backgroundColor: VERDE_ENCABEZADO }}>
      <table className="w-full table-fixed text-sm">
        <colgroup>
          <col style={{ width: anchoEtiqueta }} />
          {columnas.map((_, i) => (
            <col key={i} style={anchosDatos?.[i] ? { width: anchosDatos[i] } : undefined} />
          ))}
        </colgroup>
        <tbody>
          <tr>
            <td className="break-words px-3 py-2 font-semibold">{etiqueta}</td>
            {valores.map((v, i) => (
              <td key={i} className="px-3 py-2 text-right font-semibold">
                {fmt(v, i)}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/** Tarjeta KPI compacta con un cuadrito de color (letra adentro) --
 * calcada de las capturas reales (I/E/R, A/PA/PT). Ancho al contenido,
 * no estirada. */
export function KpiCardIcono({
  letra,
  color,
  label,
  valor,
  colorFondo = FINANCIERO_SURFACE,
}: {
  letra: string;
  color: string;
  label: string;
  valor: string;
  /** Override puntual del fondo -- ver mismo prop en TablaGrupoExpandible. */
  colorFondo?: string;
}) {
  return (
    // aspect-[4/1] = ratio alto/ancho 0.25 (medido contra la referencia real,
    // ver docs/legacy/financiero_medidas_reales.md) -- con un ancho que
    // cambia según el espacio disponible (flex-1), un alto FIJO en px no
    // mantiene la proporción; aspect-ratio sí, y las 3 páginas (misma fila
    // de 3 tarjetas flex-1 en el mismo wrapper al 56%) terminan con el
    // mismo ancho y por lo tanto el mismo alto.
    <div
      className="flex aspect-[4/1] min-w-[180px] flex-1 items-stretch overflow-hidden rounded-tremor-default ring-1 ring-line"
      style={{ backgroundColor: colorFondo }}
    >
      <div
        className="flex aspect-square h-full shrink-0 items-center justify-center text-2xl font-bold text-white"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      >
        {letra}
      </div>
      {/* flex-1 min-w-0 -- SIN esto, este div se queda del ancho de su
          propio contenido (~78px) y flota pegado al cuadrito de color,
          dejando un hueco vacío hasta el borde real de la tarjeta
          (medido: hasta 139.6px de hueco a 1794px de viewport). Con
          flex-1 el div ocupa todo el ancho restante de la tarjeta, y
          recién ahí `items-end` empuja la etiqueta y el valor contra el
          borde DERECHO real de la tarjeta (no contra un borde falso
          pegado al ícono) -- calcado de la referencia real. */}
      <div className="flex min-w-0 flex-1 flex-col items-end justify-center gap-1 px-4 py-3">
        <span className="text-xs font-semibold" style={{ color: COLOR_ETIQUETA_KPI }}>
          {label}
        </span>
        <span className="text-lg font-semibold text-ink">{valor}</span>
      </div>
    </div>
  );
}

/** Variante combinada (página 4): cuadrito + 3 "pisos" apilados --
 * título chico arriba (2 líneas FIJAS, no un texto largo que envuelve
 * distinto según el ancho -- eso hacía que la tarjeta más larga, PT,
 * recortara la 2da línea mientras A/PA sí la mostraban), porcentaje
 * grande al medio, línea divisoria y monto en Quetzales abajo. Son 2
 * valores SEPARADOS (no un texto combinado con un punto en el medio). */
export function KpiCardIconoComparativo({
  letra,
  color,
  tituloLinea1,
  tituloLinea2,
  porcentaje,
  monto,
}: {
  letra: string;
  color: string;
  tituloLinea1: string;
  tituloLinea2: string;
  porcentaje: string;
  monto: string;
}) {
  return (
    // aspect-[3.6/1] = ratio alto/ancho 0.278 -- reducido de 3.125
    // (0.32) porque la tarjeta quedaba visiblemente más alta/grande que
    // en la captura real de Power BI (aunque la PROPORCIÓN ancho de fila
    // / ancho de tabla ya coincidía con la referencia, el ancho fijo del
    // contenido de Financiero en la app -- 1658px -- es más ancho que el
    // lienzo nativo del reporte de Power BI, así que igualar el % no
    // igualaba el tamaño absoluto). Mismo mecanismo de aspect-ratio que
    // KpiCardIcono, ver comentario ahí.
    <div
      className="flex aspect-[3.6/1] min-w-[220px] flex-1 items-stretch overflow-hidden rounded-tremor-default ring-1 ring-line"
      style={{ backgroundColor: FINANCIERO_SURFACE }}
    >
      <div
        className="flex aspect-square h-full shrink-0 items-center justify-center text-[32px] font-bold text-white"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      >
        {letra}
      </div>
      {/* text-center -- calcado de la referencia real, el título, el
          porcentaje y el monto quedan centrados (no a la izquierda,
          como estaba antes). */}
      <div className="flex min-w-0 flex-1 flex-col justify-center gap-1 px-4 py-3 text-center">
        <span className="flex flex-col text-[11px] font-semibold leading-tight" style={{ color: COLOR_ETIQUETA_KPI }}>
          <span>{tituloLinea1}</span>
          <span>{tituloLinea2}</span>
        </span>
        <span className="text-lg font-normal leading-tight text-ink">{porcentaje}</span>
        <div className="border-t border-line" />
        <span className="text-lg font-bold leading-none text-ink">{monto}</span>
      </div>
    </div>
  );
}

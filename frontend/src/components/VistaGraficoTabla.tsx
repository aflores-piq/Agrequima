import { useState } from "react";
import type { ReactNode } from "react";
import { Card } from "@tremor/react";
import { FINANCIERO_SURFACE } from "./TablaGrupoExpandible";

// Tarjeta para las gráficas del Financiero que antes no tenían modo "Gráfico / Tabla"
// (Importaciones, Otros ingresos, Presupuestos, Ejecución de gastos y Flujo de caja).
// - Título: IDÉNTICO al de siempre en estas gráficas (centrado, text-base,
//   negrita, text-ink, ancho completo de la tarjeta). Va en una fila propia y NUNCA comparte renglón con el botón.
// - Botón Gráfico/Tabla: en una fila propia, pequeña, DEBAJO del título y alineada a la
//   derecha. Mismo aspecto y comportamiento que el de ChartCard (pastilla azul del
//   Financiero, "Gráfico" por defecto).
// - Fondo, borde y relleno: los mismos que ChartCard del Financiero (Estado y Balance).
// - Tabla: la MISMA tabla sencilla que ya usan Estado, Balance y Cuotas (ver más abajo).

type VistaGrafico = "grafico" | "tabla";

export function TarjetaFinanciero({
  titulo,
  chart,
  table,
  sinDatos,
}: {
  /** Título de la gráfica ("" cuando el reporte original no lleva título). */
  titulo: string;
  chart: ReactNode;
  table: ReactNode;
  /** Texto "Sin datos para ..." cuando el período elegido no tiene datos: reemplaza ejes vacíos. */
  sinDatos?: string | null;
}) {
  const [vista, setVista] = useState<VistaGrafico>("grafico");
  const vacio = sinDatos ? <MensajeSinDatos texto={sinDatos} /> : null;
  const boton = (v: VistaGrafico, texto: string) => (
    <button
      type="button"
      aria-pressed={vista === v}
      onClick={() => setVista(v)}
      className={`rounded-tremor-small px-2.5 py-1 transition-colors ${
        vista === v ? "bg-blue-600 text-white" : "text-ink-muted hover:text-ink"
      }`}
    >
      {texto}
    </button>
  );
  return (
    <Card className="flex h-full flex-col bg-surface ring-1 ring-line" style={{ backgroundColor: FINANCIERO_SURFACE }}>
      {titulo !== "" && (
        // Mismo título de siempre en estas gráficas: centrado, text-base, negrita, text-ink, con el
        // ancho completo de la tarjeta (-mx-6 anula el relleno de la tarjeta; px-2 como antes). Solo
        // se parte en 2 renglones si de verdad no cabe en el ancho de la tarjeta (igual que antes).
        <p className="-mx-6 px-2 text-center text-base font-bold text-ink">{titulo}</p>
      )}
      <div className="mt-1 flex justify-end">
        <div role="group" aria-label={`Cambiar vista de ${titulo}`} className="flex rounded-tremor-small bg-surface-hover p-0.5 text-xs">
          {boton("grafico", "Gráfico")}
          {boton("tabla", "Tabla")}
        </div>
      </div>
      <div className="mt-2 min-h-0 flex-1">{vista === "grafico" ? (vacio ?? chart) : (vacio ?? table)}</div>
    </Card>
  );
}

/** Mensaje centrado y discreto para una gráfica cuyo período elegido no tiene datos. */
export function MensajeSinDatos({ texto }: { texto: string }) {
  return (
    <div className="flex min-h-[200px] items-center justify-center" data-testid="sin-datos-grafica">
      <p className="text-center text-sm text-ink-muted">{texto}</p>
    </div>
  );
}

/** Texto "Sin datos para <período>" si todos los valores son 0/nulos; si no, null. */
export function textoSinDatos(valores: ReadonlyArray<number | null | undefined>, periodo: string): string | null {
  return valores.every((v) => !v) ? `Sin datos para ${periodo}` : null;
}

/** Tabla simple con los mismos datos que muestra la gráfica (mismo estilo que las tablas de ChartCard). */
export function TablaDatosGrafico({
  columnas,
  filas,
  alineacion,
}: {
  columnas: string[];
  filas: ReactNode[][];
  /** Alineación por columna ("left" | "right"); por defecto la primera a la izquierda y el resto a la derecha. */
  alineacion?: ("left" | "right")[];
}) {
  const alinear = (i: number) => (alineacion ? alineacion[i] : i === 0 ? "left" : "right");
  const conEncabezado = columnas.length > 2;
  return (
    <div className="overflow-x-auto" data-testid="tabla-datos-grafico">
      <table className="w-full text-sm">
        {conEncabezado && (
          <thead>
            <tr className="border-b border-line">
              {columnas.map((c, i) => (
                <th key={c + i} className={`px-2 py-1.5 font-normal text-ink-muted ${alinear(i) === "right" ? "text-right" : "text-left"}`}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {filas.map((fila, r) => (
            <tr key={r}>
              {fila.map((celda, i) => (
                <td key={i} className={`px-2 py-1.5 text-ink ${alinear(i) === "right" ? "text-right" : "text-left"}`}>
                  {celda}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

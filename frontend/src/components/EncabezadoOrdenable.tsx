import type { KeyboardEvent, ReactNode } from "react";

/** Celda de encabezado clicable para ordenar una tabla (ver
 * hooks/useTablaOrdenable.ts). La flecha va INLINE junto al texto (no en
 * un flex aparte) para heredar el text-align (izquierda/centro/derecha)
 * que ya trae `className` de cada tabla, sin tener que repetirlo acá.
 *
 * La posición de la flecha se infiere del propio `className` (si trae
 * `text-right`, columna numérica alineada a la derecha): ahí la flecha
 * va ANTES del texto, no después -- así el borde DERECHO del texto (el
 * que se mide contra las celdas de datos, también alineadas a la
 * derecha) nunca se corre al aparecer/desaparecer la flecha. En columnas
 * de texto (alineadas a la izquierda) es al revés: la flecha va
 * DESPUÉS, para no correr el borde IZQUIERDO del texto. */
export function EncabezadoOrdenable({
  children,
  className,
  flecha,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  flecha?: "▲" | "▼" | null;
  onClick: () => void;
}) {
  function alTeclado(e: KeyboardEvent<HTMLTableCellElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  }
  const alineadaDerecha = className?.includes("text-right") ?? false;
  const flechaSpan = flecha && (
    <span aria-hidden="true" className={alineadaDerecha ? "mr-1 text-[10px]" : "ml-1 text-[10px]"}>
      {flecha}
    </span>
  );
  return (
    <th
      className={`${className ?? ""} cursor-pointer select-none`}
      onClick={onClick}
      onKeyDown={alTeclado}
      role="columnheader button"
      tabIndex={0}
      aria-sort={flecha === "▲" ? "ascending" : flecha === "▼" ? "descending" : "none"}
    >
      {alineadaDerecha ? (
        <>
          {flechaSpan}
          {children}
        </>
      ) : (
        <>
          {children}
          {flechaSpan}
        </>
      )}
    </th>
  );
}

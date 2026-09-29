import type { KeyboardEvent, ReactNode } from "react";

/** Celda de encabezado clicable para ordenar una tabla (ver
 * hooks/useTablaOrdenable.ts). La flecha va INLINE junto al texto (no en
 * un flex aparte) para heredar el text-align (izquierda/centro/derecha)
 * que ya trae `className` de cada tabla, sin tener que repetirlo acá. */
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
  return (
    <th
      className={`${className ?? ""} cursor-pointer select-none`}
      onClick={onClick}
      onKeyDown={alTeclado}
      role="columnheader button"
      tabIndex={0}
      aria-sort={flecha === "▲" ? "ascending" : flecha === "▼" ? "descending" : "none"}
    >
      {children}
      {flecha && (
        <span aria-hidden="true" className="ml-1 text-[10px]">
          {flecha}
        </span>
      )}
    </th>
  );
}

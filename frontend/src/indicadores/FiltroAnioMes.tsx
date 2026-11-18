import { useEffect, useMemo, useRef, useState } from "react";
import { Icono } from "./iconos";
import type { MesDisponible, Periodo } from "./tipos";

const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

/** Filtro «Año y Mes» (pastilla «Nov. 2026» de la imagen): despliega los años y, dentro de cada uno, los meses con datos. */
export function FiltroAnioMes({
  meses,
  valor,
  onCambiar,
}: {
  meses: MesDisponible[];
  valor: Periodo | null;
  onCambiar: (p: Periodo) => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const [anioAbierto, setAnioAbierto] = useState<number | null>(null);
  const contenedor = useRef<HTMLDivElement>(null);

  const porAnio = useMemo(() => {
    const mapa = new Map<number, Set<number>>();
    for (const m of meses) {
      if (!mapa.has(m.anio)) mapa.set(m.anio, new Set());
      mapa.get(m.anio)!.add(m.mes);
    }
    return [...mapa.entries()].sort((a, b) => b[0] - a[0]);
  }, [meses]);

  useEffect(() => {
    if (!abierto) return;
    function fuera(e: MouseEvent) {
      if (contenedor.current && !contenedor.current.contains(e.target as Node)) setAbierto(false);
    }
    function tecla(e: KeyboardEvent) {
      if (e.key === "Escape") setAbierto(false);
    }
    document.addEventListener("mousedown", fuera);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", fuera);
      document.removeEventListener("keydown", tecla);
    };
  }, [abierto]);

  const etiqueta = valor ? `${MESES[valor.mes - 1]}. ${valor.anio}` : "—";

  return (
    <div className="ind-filtro" ref={contenedor}>
      <button
        type="button"
        className="ind-pill"
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-label={`Año y Mes: ${etiqueta}`}
        title="Año y Mes"
        onClick={() => {
          setAnioAbierto(valor?.anio ?? null);
          setAbierto((v) => !v);
        }}
      >
        <Icono nombre="calendario" tam={20} />
        <span>{etiqueta}</span>
        <Icono nombre="chevron" tam={16} />
      </button>
      {abierto && (
        <div className="ind-menu" role="listbox" aria-label="Año y Mes">
          <h4>Año y Mes</h4>
          {porAnio.map(([anio, conDatos]) => (
            <div key={anio}>
              <button type="button" className="anio" onClick={() => setAnioAbierto(anioAbierto === anio ? null : anio)}>
                <span aria-hidden="true">{anioAbierto === anio ? "▾" : "▸"}</span> {anio}
              </button>
              {anioAbierto === anio && (
                <div className="meses">
                  {MESES.map((nombre, i) => {
                    const mes = i + 1;
                    const seleccionado = valor?.anio === anio && valor.mes === mes;
                    return (
                      <button
                        key={mes}
                        type="button"
                        role="option"
                        aria-selected={seleccionado}
                        disabled={!conDatos.has(mes)}
                        className={`mes${seleccionado ? " sel" : ""}`}
                        onClick={() => {
                          onCambiar({ anio, mes });
                          setAbierto(false);
                        }}
                      >
                        {nombre}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

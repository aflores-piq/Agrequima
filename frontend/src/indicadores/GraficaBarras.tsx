import { COLOR_BARRA } from "./colores";
import { q0 } from "./formato";
import { Icono } from "./iconos";
import type { AgrupadoRespuesta } from "./tipos";

/** «Viáticos Totales por Colaborador»: barras horizontales (todas del color del PBIX, #00897B), de mayor a menor.
 * Con muchos colaboradores la lista se desplaza dentro de la tarjeta. */
export function GraficaBarras({ datos }: { datos: AgrupadoRespuesta | null }) {
  const lista = datos?.datos ?? [];
  const maximo = Math.max(0, ...lista.map((d) => d.total_gastos));

  return (
    <section className="ind-card ind-graf" aria-label="Viáticos Totales por Colaborador">
      <div className="ind-graf-cab">
        <div className="ind-graf-tit">
          <Icono nombre="barras" tam={22} />
          <span>Viáticos Totales por Colaborador</span>
        </div>
        <div className="ind-leyenda">
          <span>
            <i style={{ background: COLOR_BARRA }} />
            Viáticos
          </span>
        </div>
      </div>
      <div className="ind-graf-lienzo">
        {!datos ? null : lista.length === 0 ? (
          <div className="ind-vacio">Sin datos</div>
        ) : (
          <div className="ind-barras">
            {lista.map((d) => (
              <div className="ind-barra" key={d.nombre} title={`${d.nombre}: ${q0(d.total_gastos)}`}>
                <span className="n">{d.nombre}</span>
                <span className="pista">
                  <span className="b" style={{ width: `calc((100% - 70px) * ${maximo > 0 ? d.total_gastos / maximo : 0})`, background: COLOR_BARRA }} />
                  <span className="q">{q0(d.total_gastos)}</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

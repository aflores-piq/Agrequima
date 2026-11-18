import { colorGasto } from "./colores";
import { q0 } from "./formato";
import { Icono } from "./iconos";
import type { AgrupadoRespuesta } from "./tipos";
import { useMedida } from "./useMedida";

/** «Distribución de Viáticos por Tipo de Gasto»: dona con los colores de datos del PBIX; la leyenda lleva el monto
 * de cada tipo y en el centro va el total. */
export function GraficaDona({ datos }: { datos: AgrupadoRespuesta | null }) {
  const { ref, w, h } = useMedida<HTMLDivElement>();
  const lista = (datos?.datos ?? []).filter((d) => d.total_gastos > 0);
  const total = lista.reduce((s, d) => s + d.total_gastos, 0);

  const diametro = Math.max(Math.min(h - 24, Math.round(w * 0.5), 230), 80);
  const grosor = Math.round(diametro * 0.2);
  const radio = (diametro - grosor) / 2;
  const circ = 2 * Math.PI * radio;
  let acumulado = 0;

  return (
    <section className="ind-card ind-graf" aria-label="Distribución de Viáticos por Tipo de Gasto">
      <div className="ind-graf-cab">
        <div className="ind-graf-tit">
          <Icono nombre="dona" tam={22} />
          <span>Distribución de Viáticos por Tipo de Gasto</span>
        </div>
      </div>
      <div className="ind-graf-lienzo" ref={ref}>
        {!datos || w === 0 ? null : lista.length === 0 ? (
          <div className="ind-vacio">Sin datos</div>
        ) : (
          <div className="ind-dona">
            <svg className="ind-dona-svg" width={diametro} height={diametro} role="img" aria-label="Distribución por tipo de gasto">
              <g transform={`rotate(-90 ${diametro / 2} ${diametro / 2})`}>
                {lista.map((d, i) => {
                  const largo = (d.total_gastos / total) * circ;
                  const desplazamiento = -acumulado;
                  acumulado += largo;
                  return (
                    <circle
                      key={d.nombre}
                      cx={diametro / 2}
                      cy={diametro / 2}
                      r={radio}
                      fill="none"
                      stroke={colorGasto(d.nombre, i)}
                      strokeWidth={grosor}
                      strokeDasharray={`${Math.max(largo - 1.5, 0)} ${circ - Math.max(largo - 1.5, 0)}`}
                      strokeDashoffset={desplazamiento}
                    >
                      <title>{`${d.nombre}: ${q0(d.total_gastos)}`}</title>
                    </circle>
                  );
                })}
              </g>
              <text x="50%" y={diametro / 2 - 2} textAnchor="middle" fontSize="12" style={{ fill: "var(--muted)" }}>
                Total
              </text>
              <text x="50%" y={diametro / 2 + 18} textAnchor="middle" fontSize={diametro > 170 ? 20 : 16} fontWeight="700" style={{ fill: "var(--text)" }}>
                {q0(total)}
              </text>
            </svg>
            <div className="ind-dona-leyenda">
              {lista.map((d, i) => (
                <div key={d.nombre} title={`${d.nombre}: ${q0(d.total_gastos)}`}>
                  <i style={{ background: colorGasto(d.nombre, i) }} />
                  <span className="n">{d.nombre}</span>
                  <span className="q">{q0(d.total_gastos)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

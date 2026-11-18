import { useState } from "react";
import { escalaNice, q0, qCorto } from "./formato";
import { Icono } from "./iconos";
import type { AcumuladoRespuesta } from "./tipos";
import { useMedida } from "./useMedida";

const GRIS = "#9aa6c4";

/** «Viáticos acumulados»: línea del año elegido contra el anterior (medida «Gastos Acumulados Hasta Mes» del PBIX),
 * de enero hasta el mes elegido. Estilo de «Ventas acumuladas» de la imagen del nuevo diseño. */
export function GraficaAcumulada({ datos }: { datos: AcumuladoRespuesta | null }) {
  const { ref, w, h } = useMedida<HTMLDivElement>();
  const [activo, setActivo] = useState<number | null>(null);

  const actual = datos ? datos.serie_actual.slice(0, datos.mes) : [];
  const anterior = datos ? datos.serie_anterior.slice(0, datos.mes) : [];

  const mi = { izq: 54, der: 18, arr: 14, aba: 28 };
  const ancho = Math.max(w - mi.izq - mi.der, 10);
  const alto = Math.max(h - mi.arr - mi.aba, 10);
  const maximo = Math.max(0, ...actual.map((p) => p.acumulado ?? 0), ...anterior.map((p) => p.acumulado ?? 0));
  const { tope, ticks } = escalaNice(maximo, 5);
  const n = actual.length;
  const x = (i: number) => mi.izq + (n <= 1 ? ancho / 2 : (i * ancho) / (n - 1));
  const y = (v: number) => mi.arr + alto - (v / tope) * alto;

  const trazo = (serie: { acumulado: number | null }[]) =>
    serie.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.acumulado ?? 0).toFixed(1)}`).join(" ");

  function alMover(e: React.MouseEvent<SVGSVGElement>) {
    if (n === 0) return;
    const r = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - r.left;
    const i = Math.round(((px - mi.izq) / (ancho || 1)) * (n - 1));
    setActivo(Math.min(Math.max(i, 0), n - 1));
  }

  const ult = n - 1;
  const varUlt =
    datos && ult >= 0 && anterior[ult]?.acumulado
      ? (((actual[ult].acumulado ?? 0) - (anterior[ult].acumulado ?? 0)) / (anterior[ult].acumulado ?? 1)) * 100
      : null;

  return (
    <section className="ind-card ind-graf" aria-label="Viáticos acumulados">
      <div className="ind-graf-cab">
        <div className="ind-graf-tit">
          <Icono nombre="linea" tam={22} />
          <span>Viáticos acumulados</span>
        </div>
        {datos && (
          <div className="ind-leyenda">
            <span>
              <i style={{ background: "var(--brand)" }} />
              {datos.anio}
            </span>
            <span>
              <i style={{ background: GRIS }} />
              {datos.anio_anterior}
            </span>
          </div>
        )}
      </div>
      <div className="ind-graf-lienzo" ref={ref}>
        {!datos || w === 0 ? null : n === 0 || maximo === 0 ? (
          <div className="ind-vacio">Sin datos</div>
        ) : (
          <>
            <svg width={w} height={h} onMouseMove={alMover} onMouseLeave={() => setActivo(null)} role="img" aria-label="Viáticos acumulados por mes">
              <defs>
                <linearGradient id="ind-acum-area" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.22" />
                  <stop offset="100%" stopColor="var(--brand)" stopOpacity="0" />
                </linearGradient>
              </defs>
              {ticks.map((t) => (
                <g key={t}>
                  <line x1={mi.izq} x2={mi.izq + ancho} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth="1" />
                  <text x={mi.izq - 8} y={y(t) + 4} textAnchor="end" fontSize="12">
                    {qCorto(t)}
                  </text>
                </g>
              ))}
              {actual.map((p, i) => (
                <text key={p.mes} x={x(i)} y={h - 8} textAnchor="middle" fontSize="12">
                  {p.etiqueta}
                </text>
              ))}
              <path d={`${trazo(actual)} L${x(ult).toFixed(1)},${y(0)} L${x(0).toFixed(1)},${y(0)} Z`} fill="url(#ind-acum-area)" />
              <path d={trazo(anterior)} fill="none" stroke={GRIS} strokeWidth="2" strokeDasharray="5 4" strokeLinejoin="round" />
              {anterior.map((p, i) => (
                <circle key={p.mes} cx={x(i)} cy={y(p.acumulado ?? 0)} r="2.5" fill={GRIS} />
              ))}
              <path d={trazo(actual)} fill="none" stroke="var(--brand)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
              {actual.map((p, i) => (
                <circle key={p.mes} cx={x(i)} cy={y(p.acumulado ?? 0)} r={i === activo || i === ult ? 5 : 3.5} fill="var(--brand)" stroke="var(--card)" strokeWidth="1.5" />
              ))}
              {activo !== null && <line x1={x(activo)} x2={x(activo)} y1={mi.arr} y2={mi.arr + alto} stroke="var(--brand)" strokeWidth="1" strokeDasharray="3 3" />}
            </svg>
            {activo === null && (
              <div
                className="ind-tip"
                style={{ left: Math.min(Math.max(x(ult) - 70, 6), w - 120), top: Math.max(y(actual[ult].acumulado ?? 0) - 52, 2) }}
              >
                <b>{q0(actual[ult].acumulado ?? 0)}</b>
                {varUlt !== null && (
                  <div style={{ color: varUlt >= 0 ? "var(--sube)" : "var(--baja)", fontWeight: 600 }}>
                    {varUlt >= 0 ? "+" : "−"}
                    {Math.abs(varUlt).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%
                  </div>
                )}
              </div>
            )}
            {activo !== null && (
              <div className="ind-tip" style={{ left: Math.min(Math.max(x(activo) + 12, 6), w - 150), top: 8 }}>
                <b>{actual[activo].etiqueta}</b>
                <div>
                  {datos!.anio}: {q0(actual[activo].acumulado ?? 0)}
                </div>
                <div>
                  {datos!.anio_anterior}: {q0(anterior[activo]?.acumulado ?? 0)}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

import { COLOR_KPI } from "./colores";
import { entero, q0 } from "./formato";
import { Icono } from "./iconos";
import type { NombreIcono } from "./iconos";
import type { Tarjeta } from "./tipos";

const ICONO: Record<Tarjeta["clave"], NombreIcono> = {
  total_viaticos: "dinero",
  tecnicos_conductores: "tecnico",
  total_documentos: "documentos",
  total_proveedores: "proveedores",
};

/** Mini gráfica de los últimos 12 meses (línea con relleno suave y punto final), en el color de la tarjeta. */
function Mini({ valores, color, id }: { valores: number[]; color: string; id: string }) {
  const W = 72;
  const H = 36;
  const pad = 4;
  const max = Math.max(...valores, 0);
  const min = Math.min(...valores, 0);
  const rango = max - min || 1;
  const puntos = valores.map((v, i) => {
    const x = pad + (i * (W - 2 * pad)) / Math.max(valores.length - 1, 1);
    const y = H - pad - ((v - min) / rango) * (H - 2 * pad);
    return [x, y] as const;
  });
  const linea = puntos.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${pad},${H - pad} ${linea} ${W - pad},${H - pad}`;
  const [ux, uy] = puntos[puntos.length - 1];
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} width={W} height={H} aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#${id})`} />
      <polyline points={linea} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={ux} cy={uy} r="3" fill={color} />
    </svg>
  );
}

export function TarjetaKpi({ tarjeta, textoComparacion = "vs. año ant." }: { tarjeta: Tarjeta; textoComparacion?: string }) {
  const color = COLOR_KPI[tarjeta.clave];
  const valor = tarjeta.formato === "moneda" ? q0(tarjeta.valor) : entero(tarjeta.valor);
  const pct = tarjeta.variacion_pct;
  const clase = pct === null ? "nulo" : pct >= 0 ? "sube" : "baja";
  return (
    <div className="ind-card ind-kpi" data-kpi={tarjeta.clave}>
      <div className="ico" style={{ background: `${color}24`, color }}>
        <Icono nombre={ICONO[tarjeta.clave]} tam={30} grosor={1.9} />
      </div>
      <div className="txt">
        <div className="t">{tarjeta.etiqueta}</div>
        <div className="v">{valor}</div>
        <div className={`d ${clase}`}>
          {pct === null ? (
            <span>Sin datos del año ant.</span>
          ) : (
            <>
              <span aria-hidden="true">{pct >= 0 ? "▲" : "▼"}</span>
              <span>
                {pct >= 0 ? "+" : "−"}
                {Math.abs(pct).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}% {textoComparacion}
              </span>
            </>
          )}
        </div>
      </div>
      <Mini valores={tarjeta.ultimos_12_meses.map((p) => p.valor)} color={color} id={`spark-${tarjeta.clave}`} />
    </div>
  );
}

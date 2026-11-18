import { Link, NavLink } from "react-router-dom";
import agrequimaLogo from "../assets/agrequima-logo.png";
import pronostiqIcono from "../assets/pronostiq-icono.png";
import pronostiqTexto from "../assets/pronostiq-texto.png";
import { Icono } from "./iconos";
import type { NombreIcono } from "./iconos";

interface Pagina {
  titulo: string;
  icono: NombreIcono;
  /** Sin ruta = todavía no existe: se muestra, pero no navega. */
  ruta?: string;
}

// Nombres exactos de las páginas del PBIX (la 2.ª está guardada sin tilde en el PBIX).
const GRUPOS: { titulo: string; paginas: Pagina[] }[] = [
  {
    titulo: "Viáticos",
    paginas: [
      { titulo: "Resumen General", icono: "resumen", ruta: "/app/indicadores/resumen-general" },
      { titulo: "Tecnico y tipo de gasto", icono: "tecnico" },
      { titulo: "Registros Faltantes de Carga", icono: "registros" },
    ],
  },
  {
    titulo: "CuidAgro",
    paginas: [
      { titulo: "Agricultura Sostenible", icono: "agricultura" },
      { titulo: "Ecosistemas y Ambiente", icono: "ecosistemas" },
      { titulo: "Resiliencia", icono: "resiliencia" },
      { titulo: "Salud", icono: "salud" },
    ],
  },
];

/** Barra lateral azul marino del módulo Indicadores (estilo de la imagen del nuevo diseño): logo de PronostiQ, logo de
 * Agrequima, páginas agrupadas en «Viáticos» y «CuidAgro» y, solo para el Administrador, la tarjeta «Potencia tus
 * análisis con IA». Colapsable a una franja de íconos. */
export function IndicadoresSidebar({
  cerrada,
  mostrarIa,
  onVerEjemplos,
}: {
  cerrada: boolean;
  mostrarIa: boolean;
  onVerEjemplos: () => void;
}) {
  return (
    <aside className={`ind-side${cerrada ? " cerrada" : ""}`} aria-label="Páginas de Indicadores">
      <div className="ind-side-marca">
        <div className="ind-logo-pq">
          <img className="icono" src={pronostiqIcono} alt="" />
          <img className="texto" src={pronostiqTexto} alt="PronostiQ" />
        </div>
        <div className="ind-logo-ag">
          <img src={agrequimaLogo} alt="Agrequima" />
        </div>
      </div>

      <nav className="ind-nav">
        {GRUPOS.map((grupo) => (
          <div key={grupo.titulo} style={{ display: "contents" }}>
            <div className="ind-nav-grupo">{grupo.titulo}</div>
            {grupo.paginas.map((p) =>
              p.ruta ? (
                <NavLink key={p.titulo} to={p.ruta} data-n={p.titulo} className={({ isActive }) => `ind-item${isActive ? " activa" : ""}`}>
                  <Icono nombre={p.icono} />
                  <span className="etq">{p.titulo}</span>
                </NavLink>
              ) : (
                <div key={p.titulo} className="ind-item pronto" data-n={`${p.titulo} (próximamente)`} aria-disabled="true" title="Próximamente">
                  <Icono nombre={p.icono} />
                  <span className="etq">{p.titulo}</span>
                  <span className="pronto-tag">Pronto</span>
                </div>
              )
            )}
          </div>
        ))}
      </nav>

      <div className="ind-side-pie">
        {mostrarIa && (
          <div className="ind-ia">
            <Icono nombre="chispas" tam={26} />
            <div className="titulo">Potencia tus análisis con IA</div>
            <button type="button" onClick={onVerEjemplos}>
              Ver ejemplos →
            </button>
          </div>
        )}
        <Link to="/app" className="ind-item" data-n="Volver al menú general">
          <Icono nombre="atras" />
          <span className="etq">Volver al menú general</span>
        </Link>
      </div>
    </aside>
  );
}

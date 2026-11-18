import { Icono } from "./iconos";
import type { NombreIcono } from "./iconos";

type Pestana = "chat" | "sugerencias" | "analisis";

const PESTANAS: { id: Pestana; titulo: string }[] = [
  { id: "chat", titulo: "Chat" },
  { id: "sugerencias", titulo: "Sugerencias" },
  { id: "analisis", titulo: "Análisis" },
];

const SUGERENCIAS: { icono: NombreIcono; texto: string }[] = [
  { icono: "tendencia", texto: "¿Qué tipo de gasto creció más este mes?" },
  { icono: "rejilla", texto: "Muéstrame los viáticos por colaborador" },
  { icono: "calendario", texto: "Compara este mes vs. el año anterior" },
];

/** Copiloto PronostiQ (SOLO la interfaz): el cuadro y el botón están deshabilitados y no se llama a ninguna IA.
 * Solo lo monta el marco para el rol Administrador. */
export function CopilotoPanel({
  nombre,
  pestana,
  onPestana,
  onCerrar,
}: {
  nombre: string;
  pestana: Pestana;
  onPestana: (p: Pestana) => void;
  onCerrar: () => void;
}) {
  const primerNombre = nombre.trim().split(/\s+/)[0] || nombre;
  return (
    <aside className="ind-copiloto" aria-label="Copiloto PronostiQ">
      <div className="ind-cop-cab">
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          Copiloto PronostiQ <Icono nombre="chispas" tam={18} />
        </span>
        <button type="button" onClick={onCerrar} aria-label="Cerrar el Copiloto" title="Cerrar">
          <Icono nombre="minimizar" tam={18} grosor={2.2} />
        </button>
      </div>
      <div className="ind-cop-tabs" role="tablist">
        {PESTANAS.map((p) => (
          <button key={p.id} type="button" role="tab" aria-selected={pestana === p.id} className={pestana === p.id ? "activa" : ""} onClick={() => onPestana(p.id)}>
            {p.titulo}
          </button>
        ))}
      </div>
      <div className="ind-cop-cuerpo">
        <div className="ind-cop-robot">
          <Icono nombre="chispas" tam={42} grosor={1.5} />
        </div>
        <div className="ind-cop-saludo">¡Hola {primerNombre}!</div>
        <div className="ind-cop-sub">¿En qué puedo ayudarte hoy?</div>
        <div className="ind-cop-sug">
          {SUGERENCIAS.map((s) => (
            <div key={s.texto}>
              <Icono nombre={s.icono} tam={22} />
              <span>{s.texto}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="ind-cop-pie">
        <input type="text" disabled placeholder="Próximamente" aria-label="Escribe tu pregunta (Próximamente)" />
        <button type="button" disabled aria-label="Enviar (Próximamente)" title="Próximamente">
          <Icono nombre="enviar" tam={20} />
        </button>
      </div>
    </aside>
  );
}

export type { Pestana };

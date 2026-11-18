import type { ReactNode } from "react";

/** Íconos de trazo (24x24) del módulo Indicadores. Los de las páginas y tarjetas son los de la maqueta v2. */
const TRAZOS: Record<string, ReactNode> = {
  resumen: <path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />,
  tecnico: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20c.5-3.5 3.2-5.5 6.5-5.5s6 2 6.5 5.5" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M17 14c2.5 0 4.2 1.5 4.5 4" />
    </>
  ),
  registros: (
    <>
      <path d="M6 3h8l5 5v13H6z" />
      <path d="M14 3v5h5" />
      <path d="M12.5 12v4M12.5 18.5v.1" />
    </>
  ),
  agricultura: (
    <>
      <path d="M12 21v-9" />
      <path d="M12 12c0-4 3-6 7-6 0 4-3 6-7 6z" />
      <path d="M12 15c0-3-2.5-5-6-5 0 3.5 2.5 5 6 5z" />
    </>
  ),
  ecosistemas: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" />
    </>
  ),
  resiliencia: <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />,
  salud: <path d="M3 12h4l2-5 4 10 2-5h6" />,
  // tarjetas KPI
  dinero: (
    <>
      <path d="M4 7h16v11H4z" />
      <circle cx="12" cy="12.5" r="2.6" />
      <path d="M7 10v.1M17 15v.1" />
    </>
  ),
  documentos: (
    <>
      <path d="M6 3h8l5 5v13H6z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h7M9 17h7" />
    </>
  ),
  proveedores: (
    <>
      <path d="M4 10l1.5-5h13L20 10" />
      <path d="M5 10v10h14V10" />
      <path d="M4 10c0 1.7 1.3 3 3 3s3-1.3 3-3c0 1.7 1.3 3 3 3s3-1.3 3-3c0 1.7 1.3 3 3 3s3-1.3 3-3" />
    </>
  ),
  // títulos de gráficas y de la página
  barras: (
    <>
      <path d="M5 20V12M12 20V5M19 20v-9" />
    </>
  ),
  linea: (
    <>
      <path d="M3 17l5-6 4 3 8-9" />
      <path d="M15 5h5v5" />
    </>
  ),
  dona: (
    <>
      <path d="M12 3a9 9 0 1 0 9 9h-9z" />
      <path d="M15 3.5A9 9 0 0 1 20.5 9H15z" />
    </>
  ),
  tabla: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18M9 10v10" />
    </>
  ),
  // controles
  calendario: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="3" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </>
  ),
  chevron: <path d="M6 9l6 6 6-6" />,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  atras: <path d="M15 5l-7 7 7 7" />,
  menuCerrar: <path d="M11 6l-6 6 6 6M19 6l-6 6 6 6" />,
  chispas: (
    <>
      <path d="M10 3l1.6 4.4L16 9l-4.4 1.6L10 15l-1.6-4.4L4 9l4.4-1.6z" />
      <path d="M18 14l.8 2.2L21 17l-2.2.8L18 20l-.8-2.2L15 17l2.2-.8z" />
    </>
  ),
  enviar: <path d="M4 12l16-8-6 16-3-7z" />,
  minimizar: <path d="M6 12h12" />,
  tendencia: (
    <>
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M15 7h6v6" />
    </>
  ),
  rejilla: (
    <>
      <rect x="4" y="4" width="7" height="7" rx="1.5" />
      <rect x="13" y="4" width="7" height="7" rx="1.5" />
      <rect x="4" y="13" width="7" height="7" rx="1.5" />
      <rect x="13" y="13" width="7" height="7" rx="1.5" />
    </>
  ),
  inicio: <path d="M4 11l8-7 8 7M6 10v10h12V10" />,
};

export type NombreIcono = keyof typeof TRAZOS;

export function Icono({ nombre, tam = 24, grosor = 1.8, className }: { nombre: NombreIcono; tam?: number; grosor?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={tam}
      height={tam}
      fill="none"
      stroke="currentColor"
      strokeWidth={grosor}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
      style={{ flex: "none" }}
    >
      {TRAZOS[nombre]}
    </svg>
  );
}

/** Marca de barras de PronostiQ (maqueta). */
export function LogoBarras({ tam = 34 }: { tam?: number }) {
  return (
    <svg width={tam} height={tam} viewBox="0 0 34 34" aria-hidden="true">
      <rect x="3" y="18" width="7" height="13" rx="2" fill="#48ADFE" />
      <rect x="13" y="11" width="7" height="20" rx="2" fill="#48ADFE" />
      <rect x="23" y="3" width="7" height="28" rx="2" fill="#48ADFE" />
    </svg>
  );
}

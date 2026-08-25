// Paleta fija por dashboard: verde/teal para Plaguicidas, naranja para
// Nutrientes. NUNCA se reasigna dinámicamente según el filtro activo.

export type DashboardTheme = "plaguicidas" | "nutrientes";

export const dashboardAccent: Record<
  DashboardTheme,
  {
    tremor: string; // nombre de color Tremor (Card, ProgressBar, BarChart)
    text: string; // clase tailwind para texto de acento
    ring: string; // clase tailwind para bordes/focus de acento
    chip: string; // clase tailwind para chips/badges
    light: string; // hex extremo claro de la escala de intensidad
    dark: string; // hex extremo oscuro de la escala de intensidad
  }
> = {
  plaguicidas: {
    tremor: "teal",
    text: "text-teal-400",
    ring: "ring-teal-500/40",
    chip: "bg-teal-500/10 text-teal-300 ring-1 ring-teal-500/30",
    light: "#99f6e4", // teal-200
    dark: "#0f766e", // teal-700
  },
  nutrientes: {
    tremor: "orange",
    text: "text-orange-400",
    ring: "ring-orange-500/40",
    chip: "bg-orange-500/10 text-orange-300 ring-1 ring-orange-500/30",
    light: "#fed7aa", // orange-200
    dark: "#c2410c", // orange-700
  },
};

// Orden fijo de categorías de aplicación para la dona de plaguicidas —
// debe coincidir exactamente con CATEGORIAS_APLICACION_ORDEN en
// backend/app/services/clasificacion.py. El orden y el color de cada
// categoría son fijos, nunca se reasignan según qué categorías estén
// presentes en el filtro.
export const APLICACION_ORDEN = [
  "Herbicida",
  "Insecticida",
  "Fungicida",
  "Acaricida",
  "Nematicida",
  "Materia Técnica - Herbicida",
  "Materia Técnica - Fungicida",
  "Materia Técnica - Insecticida",
  "Materia Técnica - Otro",
  "Otros",
];

export const APLICACION_COLOR: Record<string, string> = {
  HERBICIDA: "emerald",
  INSECTICIDA: "amber",
  FUNGICIDA: "violet",
  ACARICIDA: "cyan",
  NEMATICIDA: "pink",
  "MATERIA TÉCNICA - HERBICIDA": "lime",
  "MATERIA TÉCNICA - FUNGICIDA": "fuchsia",
  "MATERIA TÉCNICA - INSECTICIDA": "indigo",
  "MATERIA TÉCNICA - OTRO": "stone",
  OTROS: "slate",
};

const APLICACION_COLOR_OTROS = "slate";

export function ordenarCategorias(categorias: string[]): string[] {
  const presentes = new Set(categorias);
  const fijas = APLICACION_ORDEN.filter((c) => presentes.has(c));
  const otras = categorias.filter((c) => !APLICACION_ORDEN.includes(c)).sort();
  return [...fijas, ...otras];
}

export function colorParaCategoria(categoria: string): string {
  return APLICACION_COLOR[categoria.toUpperCase()] ?? APLICACION_COLOR_OTROS;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const n = parseInt(h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbToHex(rgb: [number, number, number]): string {
  return (
    "#" +
    rgb.map((c) => Math.round(Math.min(255, Math.max(0, c))).toString(16).padStart(2, "0")).join("")
  );
}

/** Devuelve un color en la escala de intensidad de un solo hue (claro ->
 * oscuro) para rankings de magnitud (top ingredientes, importadores,
 * países): NO asigna un color distinto por barra, solo varía la
 * intensidad según qué tan grande es el valor relativo (t entre 0 y 1). */
export function colorIntensidad(theme: DashboardTheme, t: number): string {
  const clamped = Math.min(1, Math.max(0, t));
  const { light, dark } = dashboardAccent[theme];
  const [lr, lg, lb] = hexToRgb(light);
  const [dr, dg, db] = hexToRgb(dark);
  return rgbToHex([
    lr + (dr - lr) * clamped,
    lg + (dg - lg) * clamped,
    lb + (db - lb) * clamped,
  ]);
}

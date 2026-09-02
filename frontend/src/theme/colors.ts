// Paleta fija por dashboard: verde/teal para Plaguicidas, naranja para
// Nutrientes. NUNCA se reasigna dinámicamente según el filtro activo.

import type { Color } from "@tremor/react";

export type DashboardTheme = "plaguicidas" | "nutrientes";

export const dashboardAccent: Record<
  DashboardTheme,
  {
    tremor: Color; // nombre de color Tremor (Card, ProgressBar, BarChart)
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

// Clases completas y literales (no interpoladas): Tailwind genera CSS
// solo a partir de nombres de clase que aparecen tal cual en el código
// fuente — una clase armada con un string dinámico ("bg-" + color +
// "-500/10") nunca se generaría. Un color por cada valor posible de
// APLICACION_COLOR.
const BADGE_CLASE_POR_COLOR: Record<string, string> = {
  emerald: "bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/30",
  amber: "bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/30",
  violet: "bg-violet-500/10 text-violet-300 ring-1 ring-violet-500/30",
  cyan: "bg-cyan-500/10 text-cyan-300 ring-1 ring-cyan-500/30",
  pink: "bg-pink-500/10 text-pink-300 ring-1 ring-pink-500/30",
  lime: "bg-lime-500/10 text-lime-300 ring-1 ring-lime-500/30",
  fuchsia: "bg-fuchsia-500/10 text-fuchsia-300 ring-1 ring-fuchsia-500/30",
  indigo: "bg-indigo-500/10 text-indigo-300 ring-1 ring-indigo-500/30",
  stone: "bg-stone-500/10 text-stone-300 ring-1 ring-stone-500/30",
  slate: "bg-slate-500/10 text-slate-300 ring-1 ring-slate-500/30",
};

/** Clases Tailwind del badge de una categoría de aplicación (plaguicidas):
 * mismo color fijo por categoría en toda la app, ver APLICACION_COLOR. */
export function claseBadgeCategoria(categoria: string): string {
  const color = colorParaCategoria(categoria);
  return BADGE_CLASE_POR_COLOR[color] ?? BADGE_CLASE_POR_COLOR.slate;
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

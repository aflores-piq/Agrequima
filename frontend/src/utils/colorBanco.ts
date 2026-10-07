// Estilo del encabezado de cada banco en Conciliación bancaria: un degradado
// horizontal del COLOR ÚNICO del banco (el color_hex de dbo.CatalogoBancos,
// que llega en `banco.color`) -- a la izquierda el color tal cual, a la
// derecha ese mismo color mezclado 70 % color + 30 % blanco --, sin colores
// secundarios. El degradado y el borde se calculan acá; la tabla no tiene
// ninguna columna extra.

// Gris por defecto del backend (COLOR_BANCO_POR_DEFECTO) -- solo se usa si
// llegara un color con formato inválido.
const GRIS_POR_DEFECTO = "#9E9E9E";
const FORMATO_HEX = /^#[0-9a-fA-F]{6}$/;
const PROPORCION_COLOR = 0.7;

export function mezclarConBlanco(hex: string): string {
  const base = FORMATO_HEX.test(hex) ? hex : GRIS_POR_DEFECTO;
  const canal = (desde: number) => {
    const valor = parseInt(base.slice(desde, desde + 2), 16);
    const mezclado = Math.round(valor * PROPORCION_COLOR + 255 * (1 - PROPORCION_COLOR));
    return mezclado.toString(16).padStart(2, "0");
  };
  return `#${canal(1)}${canal(3)}${canal(5)}`.toUpperCase();
}

export function degradadoBanco(hex: string): string {
  const base = FORMATO_HEX.test(hex) ? hex : GRIS_POR_DEFECTO;
  return `linear-gradient(to right, ${base}, ${mezclarConBlanco(base)})`;
}

export function colorBordeBanco(hex: string): string {
  return FORMATO_HEX.test(hex) ? hex : GRIS_POR_DEFECTO;
}

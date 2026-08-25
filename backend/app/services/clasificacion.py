"""Normalización de columnas de texto crudo con muchas variantes hacia un
conjunto fijo y pequeño de categorías, usado en los dashboards donde cada
fila debe caer en exactamente una categoría (dona, gráficos con orden de
color fijo) o donde el mismo lugar aparece escrito de formas distintas."""

import unicodedata

CATEGORIAS_APLICACION_ORDEN = [
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
]


def clasificar_aplicacion(valor: str | None) -> str:
    """dbo.Importacion.aplicacion trae más de 60 variantes de texto crudo
    (combos como 'INSECTICIDA, FUNGICIDA', errores de captura como
    'HEBICIDA', mayúsculas/minúsculas mezcladas). Para la dona de
    diversificación cada transacción cae en UNA sola categoría, con esta
    prioridad: Herbicida > Insecticida > Fungicida > Acaricida >
    Nematicida > Materia Técnica > Otros."""
    if not valor:
        return "Otros"
    v = valor.upper()

    # "CNICA" en vez de "TÉCNICA" tolera el mojibake que trae la columna
    # (T�CNICA) para algunos registros.
    es_materia_tecnica = "MATERIA" in v and "CNICA" in v
    if es_materia_tecnica:
        if "HERBICID" in v or "HEBICID" in v:
            return "Materia Técnica - Herbicida"
        if "FUNGICID" in v:
            return "Materia Técnica - Fungicida"
        if "INSECTICID" in v:
            return "Materia Técnica - Insecticida"
        return "Materia Técnica - Otro"

    if "HERBICID" in v or "HEBICID" in v:
        return "Herbicida"
    if "INSECTICID" in v:
        return "Insecticida"
    if "FUNGICID" in v:
        return "Fungicida"
    if "ACARICID" in v:
        return "Acaricida"
    if "NEMATICID" in v or "NEMATIACID" in v:
        return "Nematicida"
    return "Otros"


def _clave_sin_acentos(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_acentos.strip().upper()


# Variantes reales observadas en dbo.Nutrientes.AduanadeIngreso (mayúsculas
# sueltas, con/sin acentos, con/sin el prefijo "Puerto") que en realidad
# son el mismo lugar.
_ADUANA_CANONICA = {
    "CORINTO": "Corinto",
    "EL FLORIDO": "El Florido",
    "EXPRESS AEREO": "Express Aéreo",
    "PEDRO DE ALVARADO": "Pedro de Alvarado",
    "PUERTO BARRIOS": "Puerto Barrios",
    "PUERTO QUETZAL": "Puerto Quetzal",
    "SANTO TOMAS DE CASTILLA": "Puerto Santo Tomás de Castilla",
    "PUERTO SANTO TOMAS DE CASTILLA": "Puerto Santo Tomás de Castilla",
    "SAN CRISTOBAL": "San Cristóbal",
    "TECUN UMAN": "Tecún Umán",
    "AGUA CALIENTE": "Agua Caliente",
    "VALLE NUEVO": "Valle Nuevo",
}


def normalizar_aduana(valor: str | None) -> str | None:
    if not valor:
        return valor
    return _ADUANA_CANONICA.get(_clave_sin_acentos(valor), valor.strip())

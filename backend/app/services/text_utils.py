"""Utilidades de normalización y saneo de texto compartidas por los
procesos ETL de plaguicidas y nutrientes."""

import re

import pandas as pd

_TEXTOS_VACIOS = {"nan", "none", "null", "n/a", "na", ""}


def es_vacio(valor) -> bool:
    if pd.isna(valor):
        return True
    if isinstance(valor, str) and valor.strip().lower() in _TEXTOS_VACIOS:
        return True
    return False


def normalizar(texto) -> str | None:
    """TRIM + UPPER + colapsar espacios múltiples. Clave de cruce."""
    if es_vacio(texto):
        return None
    return re.sub(r"\s+", " ", str(texto).strip().upper())


def a_texto_id(valor) -> str | None:
    """Convierte un identificador a texto de forma segura (sin decimales
    si es un entero disfrazado de float, ej. 66698.0 -> '66698')."""
    if es_vacio(valor):
        return None
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def limpiar_texto(texto) -> str | None:
    """TRIM + colapsar espacios, sin cambiar mayúsculas."""
    if es_vacio(texto):
        return None
    return re.sub(r"\s+", " ", str(texto).strip())


def truncar_columnas(df: pd.DataFrame, limites: dict) -> tuple[pd.DataFrame, list[dict]]:
    """Corta cualquier valor de texto que exceda el límite de su columna
    destino, para evitar que SQL Server rechace todo el lote con 'String
    or binary data would be truncated'. Devuelve el detalle de lo truncado."""
    advertencias: list[dict] = []
    for columna, limite in limites.items():
        if columna not in df.columns:
            continue

        def _recortar(valor, _limite=limite, _columna=columna):
            if valor is None:
                return None
            texto = str(valor)
            if len(texto) > _limite:
                advertencias.append({
                    "columna": _columna,
                    "longitud_original": len(texto),
                    "limite": _limite,
                })
                return texto[:_limite]
            return texto

        df[columna] = df[columna].apply(_recortar)
    return df, advertencias


def limpiar_moneda(valor) -> float | None:
    """Convierte columnas de moneda tipo '$2,649.75' o 'Q20,308.13' a
    float, quitando símbolo de moneda, separador de miles y espacios.
    Útil para columnas numéricas que llegan como texto (ej. desde un
    CSV), a diferencia de un Excel donde la celda ya viene tipada."""
    if es_vacio(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = re.sub(r"[^0-9.\-]", "", str(valor))
    if texto in ("", "-", "."):
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def detectar_fila_encabezado(
    df_sin_encabezado: pd.DataFrame,
    columnas_esperadas: list[str],
    min_coincidencias: int = 5,
    max_filas_a_revisar: int = 10,
) -> int:
    """Encuentra en qué fila están los encabezados reales de un archivo
    (leído con header=None), en vez de asumir que siempre es la fila 0.

    Algunos archivos traen una fila de título arriba de los encabezados
    (ej. "Consolidado Licencias de Importación 2023 al mes de
    diciembre") o filas en blanco; si se asumiera fila 0, esa fila de
    título se leería como si fueran los nombres de columna y todo el
    archivo quedaría desalineado.

    Revisa las primeras `max_filas_a_revisar` filas y devuelve el índice
    de la primera que contenga al menos `min_coincidencias` de
    `columnas_esperadas` (comparando normalizado: trim + mayúsculas, sin
    exigir coincidencia exacta de mayúsculas/minúsculas ni espacios)."""
    normalizadas_esperadas = {c.strip().upper() for c in columnas_esperadas}
    limite = min(max_filas_a_revisar, len(df_sin_encabezado))
    for i in range(limite):
        valores_fila = {
            str(v).strip().upper() for v in df_sin_encabezado.iloc[i].tolist() if not pd.isna(v)
        }
        if len(normalizadas_esperadas & valores_fila) >= min_coincidencias:
            return i
    raise ValueError(
        f"No se pudo encontrar la fila de encabezados en las primeras {limite} filas del "
        f"archivo (se esperaban al menos {min_coincidencias} de estas columnas: "
        f"{sorted(columnas_esperadas)})."
    )


def parece_error_captura(texto: str | None) -> bool:
    """Heurística simple para separar valores que en realidad son basura
    de captura (números sueltos, nombres de archivo) de valores reales
    sin agrupador todavía. No es perfecta: es solo una ayuda para
    priorizar la revisión manual en la pantalla de excepciones."""
    if not texto:
        return False
    t = texto.strip()
    if re.fullmatch(r"[\d.,]+", t):
        return True
    if re.search(r"\.(pdf|xlsx?|docx?|jpg|png)$", t, re.IGNORECASE):
        return True
    return False

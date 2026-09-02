"""Constructores de archivos sintéticos en memoria para las pruebas de
carga (evita depender de archivos reales del cliente en el repo)."""

from io import BytesIO

import pandas as pd
from sqlalchemy import text

from app.core.db import engine


def limpiar_importacion_anio(anio: int) -> None:
    """Borra cualquier fila de un año de prueba antes de cargarlo de
    nuevo. Necesario desde que usp_CargarImportacion dejó de hacer
    DELETE + INSERT por año (ver 'solo cargar el mes nuevo'): sin este
    borrido explícito, una corrida repetida de la suite encontraría el
    año ya cargado de una corrida anterior y el ETL ignoraría las filas
    por considerarlas ya guardadas, rompiendo el aislamiento del test."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dbo.Importacion WHERE anio = :anio"), {"anio": anio})


def limpiar_nutrientes_anio(anio: int) -> None:
    """Igual que limpiar_importacion_anio, para dbo.Nutrientes."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dbo.Nutrientes WHERE anio = :anio"), {"anio": anio})


COLUMNAS_IMPORTACIONES = [
    "RECIBO", "SerieSAT", "RecSAT", "APLICACIoN", "RECIBOSAT", "FECHA",
    "IMPORTADOR", "PRODUCTO", "INGREDIENTEACT", "EXPORTADOR", "ORIGEN",
    "pct", "CANTIDAD", "UNMEDIDA", "CIFusd", "CIFQ", "CAMBIO", "Empresa", "UMSP",
]


def construir_excel_importaciones(
    filas: list[dict], hoja: str = "ImpPlagTest", titulo: str | None = None
) -> bytes:
    """`titulo`: si se da, antepone una fila de título (col B) + 2 filas
    en blanco antes del encabezado real, igual que un archivo real con
    una fila tipo "Consolidado Licencias de Importación 2023..." arriba
    de los encabezados — para probar la detección de fila de encabezado."""
    df = pd.DataFrame(filas, columns=COLUMNAS_IMPORTACIONES)
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    buffer = BytesIO()
    startrow = 3 if titulo else 0
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=hoja, index=False, startrow=startrow)
        if titulo:
            writer.sheets[hoja]["B1"] = titulo
    buffer.seek(0)
    return buffer.read()


def construir_excel_nomenclatura(filas: list[dict]) -> bytes:
    """filas: [{"ingrediente": ..., "agrupador": ..., "codigo": ...}, ...]"""
    df = pd.DataFrame(
        [
            {
                "INGREDIENTE ACT.": f["ingrediente"],
                "Agrupación estandarizada_Nomenclatura": f["agrupador"],
                "Codigo": f["codigo"],
            }
            for f in filas
        ]
    )
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Nomenclatura agrupada", index=False)
    buffer.seek(0)
    return buffer.read()


def _filas_titulo_csv(titulo: str, num_columnas: int) -> str:
    fila_titulo = titulo + ";" * (num_columnas - 1)
    fila_vacia = ";" * (num_columnas - 1)
    return f"{fila_titulo}\n{fila_vacia}\n{fila_vacia}\n"


def construir_csv_importaciones(filas: list[dict], titulo: str | None = None) -> bytes:
    """filas: mismas claves que construir_excel_importaciones, pero los
    valores de FECHA/CANTIDAD/CIFusd/CIFQ/UMSP se escriben tal como
    llegarían en un CSV real (texto, con formato de moneda tipo
    '$1,234.56' y fecha 'DD/MM/YYYY'), para probar la limpieza que hace
    el servicio específicamente para archivos .csv. `titulo`: ver
    construir_excel_importaciones."""
    df = pd.DataFrame(filas, columns=COLUMNAS_IMPORTACIONES)
    texto = df.to_csv(sep=";", index=False)
    if titulo:
        texto = _filas_titulo_csv(titulo, len(COLUMNAS_IMPORTACIONES)) + texto
    return ("﻿" + texto).encode("utf-8")


def construir_excel_hoja_ambigua() -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Hoja1", index=False)
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Hoja2", index=False)
    buffer.seek(0)
    return buffer.read()


COLUMNAS_NUTRIENTES = [
    "Tipo", "No_Licencia", "No_Registro", "NombreComercial", "EmpresaImportadora",
    "FechaEmision", "UMedida", "Cantidad", "PaisProcedencia", "PaisOrigen",
    "AduanadeIngreso", " CIF_dolares ", " CIF_Q ", " TimbresQ ", "Exportador",
    "Concentraciones", "Componentes", "VENTANILLA",
]


def construir_csv_nutrientes(filas: list[dict], titulo: str | None = None) -> bytes:
    """`titulo`: ver construir_excel_importaciones — antepone una fila de
    título + 2 en blanco antes del encabezado real."""
    df = pd.DataFrame(filas, columns=COLUMNAS_NUTRIENTES)
    texto = df.to_csv(sep=";", index=False)
    if titulo:
        texto = _filas_titulo_csv(titulo, len(COLUMNAS_NUTRIENTES)) + texto
    return ("﻿" + texto).encode("utf-8")


def construir_excel_nutrientes(
    filas: list[dict], hoja: str = "Licencias", titulo: str | None = None,
    fecha_como_texto: bool = False,
) -> bytes:
    """Igual que construir_csv_nutrientes, pero como .xlsx con las celdas
    ya tipadas (fecha real, montos como número) en vez de texto crudo —
    así se prueba el mismo camino que un archivo .xlsx real, distinto del
    parseo de texto que usa el .csv (encoding, formato de fecha, símbolos
    de moneda). `titulo`: ver construir_excel_importaciones.

    `fecha_como_texto=True`: deja "FechaEmision" como texto "DD/MM/YYYY"
    en vez de convertirla a datetime nativo — reproduce el caso real
    donde la celda del .xlsx llega como texto aunque la columna se vea
    formateada como Fecha (bug confirmado en producción, carga del
    2026-08-27)."""
    df = pd.DataFrame(filas, columns=COLUMNAS_NUTRIENTES)
    if not fecha_como_texto:
        df["FechaEmision"] = pd.to_datetime(df["FechaEmision"], dayfirst=True)
    buffer = BytesIO()
    startrow = 3 if titulo else 0
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=hoja, index=False, startrow=startrow)
        if titulo:
            writer.sheets[hoja]["B1"] = titulo
    buffer.seek(0)
    return buffer.read()

"""ETL de Otros Ingresos (módulo Financiero).

Mismo patrón que etl_saldo_bancario.py: carga directa sin catálogo,
DELETE + INSERT por período (año/mes) presente en el archivo.
"""

import logging
from io import BytesIO

import pandas as pd
from sqlalchemy import text

from app.core.db import engine
from app.schemas.cargas import PeriodoCubierto, ResumenCargaFinanciero
from app.services.auditoria import registrar_auditoria
from app.services.text_utils import limpiar_texto

logger = logging.getLogger(__name__)

_MAPEO_COLUMNAS = {
    "tipo": "Tipo",
    "concepto": "Concepto",
    "año": "Anio",
    "anio": "Anio",
    "mes": "Mes",
    "valor": "Valor",
}

_COLUMNAS_REQUERIDAS = ["Tipo", "Concepto", "Anio", "Mes", "Valor"]


def _normalizar_encabezados(df: pd.DataFrame) -> pd.DataFrame:
    renombre = {}
    for columna in df.columns:
        clave = str(columna).strip().lower()
        if clave in _MAPEO_COLUMNAS:
            renombre[columna] = _MAPEO_COLUMNAS[clave]
    return df.rename(columns=renombre)


def _leer_excel(contenido: bytes) -> pd.DataFrame:
    df = pd.read_excel(BytesIO(contenido))
    df = _normalizar_encabezados(df)

    faltantes = [c for c in _COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise ValueError(
            f"El archivo de Otros Ingresos no tiene las columnas esperadas: "
            f"{faltantes}. Columnas encontradas: {list(df.columns)}."
        )

    salida = pd.DataFrame({
        "Tipo": df["Tipo"].apply(limpiar_texto),
        "Concepto": df["Concepto"].apply(limpiar_texto),
        "Anio": pd.to_numeric(df["Anio"], errors="coerce"),
        "Mes": pd.to_numeric(df["Mes"], errors="coerce"),
        "Valor": pd.to_numeric(df["Valor"], errors="coerce"),
    })

    antes = len(salida)
    salida = salida[~salida["Anio"].isna() & ~salida["Mes"].isna()].copy()
    filas_descartadas = antes - len(salida)
    if filas_descartadas:
        logger.warning(
            "Otros Ingresos: %d fila(s) descartada(s) por no tener Año/Mes.", filas_descartadas
        )

    if salida.empty:
        raise ValueError("El archivo de Otros Ingresos no tiene ninguna fila con Año y Mes válidos.")

    return salida


def procesar_carga_otro_ingreso(
    contenido: bytes, nombre_archivo: str, usuario_id: int
) -> ResumenCargaFinanciero:
    logger.info("Iniciando carga de Otros Ingresos: archivo=%s usuario_id=%s", nombre_archivo, usuario_id)
    try:
        df = _leer_excel(contenido)
        periodos = sorted({(int(a), int(m)) for a, m in zip(df["Anio"], df["Mes"])})

        df.to_sql("stg_OtroIngreso", engine, if_exists="replace", index=False)

        with engine.begin() as conn:
            for anio, mes in periodos:
                conn.execute(
                    text("DELETE FROM dbo.OtroIngreso WHERE Anio = :anio AND Mes = :mes"),
                    {"anio": anio, "mes": mes},
                )
            conn.execute(
                text(
                    """
                    INSERT INTO dbo.OtroIngreso (Tipo, Concepto, Anio, Mes, Valor, UsuarioId, FechaMod)
                    SELECT Tipo, Concepto, CAST(Anio AS INT), CAST(Mes AS INT), Valor, :usuario_id, GETDATE()
                    FROM dbo.stg_OtroIngreso
                    WHERE Tipo IS NOT NULL OR Concepto IS NOT NULL OR Valor IS NOT NULL
                    """
                ),
                {"usuario_id": usuario_id},
            )
    except Exception as exc:
        logger.exception("Falló la carga de Otros Ingresos (archivo=%s)", nombre_archivo)
        registrar_auditoria("OtrosIngresos", nombre_archivo, usuario_id, None, None, "Error", str(exc))
        raise

    resumen = ResumenCargaFinanciero(
        filas_cargadas=len(df),
        periodos=[PeriodoCubierto(anio=a, mes=m) for a, m in periodos],
        estado="OK",
    )

    registrar_auditoria(
        "OtrosIngresos", nombre_archivo, usuario_id, resumen.filas_cargadas, 0, resumen.estado, None
    )
    logger.info(
        "Carga de Otros Ingresos finalizada: archivo=%s filas=%s periodos=%s",
        nombre_archivo, resumen.filas_cargadas, periodos,
    )
    return resumen

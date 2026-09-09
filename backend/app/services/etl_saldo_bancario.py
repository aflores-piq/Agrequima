"""ETL de Saldos Bancarios (módulo Financiero).

Carga directa, sin cruce de catálogo/agrupador (a diferencia de
Plaguicidas/Nutrientes): el Excel trae Concepto/Año/Mes/Banco/Valor ya
listos para insertar tal cual. Estrategia de idempotencia distinta a la
de Plaguicidas/Nutrientes ("solo cargar el mes nuevo"): acá se hace
DELETE + INSERT de cada período (año/mes) presente en el archivo, para
que volver a subir el mismo mes (una corrección) lo reemplace en vez de
duplicarlo o de ignorarlo.
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

# Nombres de columna aceptados en el Excel -> nombre interno. Se acepta
# tanto "Año" (con tilde) como "Anio" (sin tilde, por si el archivo se
# guardó con otra codificación) para el mismo campo.
_MAPEO_COLUMNAS = {
    "concepto": "Concepto",
    "año": "Anio",
    "anio": "Anio",
    "mes": "Mes",
    "banco": "Banco",
    "valor": "Valor",
}

_COLUMNAS_REQUERIDAS = ["Concepto", "Anio", "Mes", "Banco", "Valor"]


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
            f"El archivo de Saldos Bancarios no tiene las columnas esperadas: "
            f"{faltantes}. Columnas encontradas: {list(df.columns)}."
        )

    salida = pd.DataFrame({
        "Concepto": df["Concepto"].apply(limpiar_texto),
        "Anio": pd.to_numeric(df["Anio"], errors="coerce"),
        "Mes": pd.to_numeric(df["Mes"], errors="coerce"),
        "Banco": df["Banco"].apply(limpiar_texto),
        "Valor": pd.to_numeric(df["Valor"], errors="coerce"),
    })

    antes = len(salida)
    salida = salida[~salida["Anio"].isna() & ~salida["Mes"].isna()].copy()
    filas_descartadas = antes - len(salida)
    if filas_descartadas:
        logger.warning(
            "Saldos Bancarios: %d fila(s) descartada(s) por no tener Año/Mes.", filas_descartadas
        )

    if salida.empty:
        raise ValueError("El archivo de Saldos Bancarios no tiene ninguna fila con Año y Mes válidos.")

    return salida


def procesar_carga_saldo_bancario(
    contenido: bytes, nombre_archivo: str, usuario_id: int
) -> ResumenCargaFinanciero:
    logger.info("Iniciando carga de Saldos Bancarios: archivo=%s usuario_id=%s", nombre_archivo, usuario_id)
    try:
        df = _leer_excel(contenido)
        periodos = sorted({(int(a), int(m)) for a, m in zip(df["Anio"], df["Mes"])})

        df.to_sql("stg_SaldoBancario", engine, if_exists="replace", index=False)

        with engine.begin() as conn:
            for anio, mes in periodos:
                conn.execute(
                    text("DELETE FROM dbo.SaldoBancario WHERE Anio = :anio AND Mes = :mes"),
                    {"anio": anio, "mes": mes},
                )
            conn.execute(
                text(
                    """
                    INSERT INTO dbo.SaldoBancario (Concepto, Anio, Mes, Banco, Valor, UsuarioId, FechaMod)
                    SELECT Concepto, CAST(Anio AS INT), CAST(Mes AS INT), Banco, Valor, :usuario_id, GETDATE()
                    FROM dbo.stg_SaldoBancario
                    WHERE Concepto IS NOT NULL OR Banco IS NOT NULL OR Valor IS NOT NULL
                    """
                ),
                {"usuario_id": usuario_id},
            )
    except Exception as exc:
        logger.exception("Falló la carga de Saldos Bancarios (archivo=%s)", nombre_archivo)
        registrar_auditoria("SaldosBancarios", nombre_archivo, usuario_id, None, None, "Error", str(exc))
        raise

    resumen = ResumenCargaFinanciero(
        filas_cargadas=len(df),
        periodos=[PeriodoCubierto(anio=a, mes=m) for a, m in periodos],
        estado="OK",
    )

    registrar_auditoria(
        "SaldosBancarios", nombre_archivo, usuario_id, resumen.filas_cargadas, 0, resumen.estado, None
    )
    logger.info(
        "Carga de Saldos Bancarios finalizada: archivo=%s filas=%s periodos=%s",
        nombre_archivo, resumen.filas_cargadas, periodos,
    )
    return resumen

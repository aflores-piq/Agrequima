"""Copia UNA SOLA VEZ (no es parte del sync nocturno) las piezas que le
faltan a PIQ_IA para que la pantalla de Carga funcione ahí también:

  - Los 4 stored procedures de carga/actualización de catálogo
    (se recrean con la definición EXACTA de origen, vía OBJECT_DEFINITION).
  - Las tablas de log (log_ExcepcionesAgrupador,
    log_ExcepcionesAgrupadorNutrientes): estructura + datos actuales.
  - Las tablas de staging (stg_Importacion, stg_Nutrientes,
    stg_Nomenclatura, stg_AgrupadorNutrientes): solo estructura, vacías
    — son transitorias, el propio ETL las recrea (DROP+CREATE) en cada
    carga real (ver to_sql(if_exists="replace") en etl_*.py).

Uso (manual, una sola vez):
    python -m app.scripts.copiar_objetos_carga_piq_ia
"""

import sys

from sqlalchemy import MetaData, Table, create_engine, text

from app.scripts.sync_piq_ia import _asegurar_tabla_destino, _conn_str, _copiar_tabla, _vaciar_tabla_destino, logger

PROCEDURES = [
    "usp_CargarImportacion",
    "usp_CargarNutrientes",
    "usp_ActualizarNomenclatura",
    "usp_ActualizarAgrupadorNutrientes",
]
TABLAS_LOG_CON_DATOS = ["log_ExcepcionesAgrupador", "log_ExcepcionesAgrupadorNutrientes"]
TABLAS_STAGING_VACIAS = ["stg_Importacion", "stg_Nutrientes", "stg_Nomenclatura", "stg_AgrupadorNutrientes"]


def _copiar_procedimiento(origen_engine, destino_engine, nombre: str) -> None:
    with origen_engine.connect() as conn:
        definicion = conn.execute(
            text("SELECT OBJECT_DEFINITION(OBJECT_ID(:p))"), {"p": f"dbo.{nombre}"}
        ).scalar()
    if definicion is None:
        raise RuntimeError(f"No se encontró el procedure dbo.{nombre} en el origen.")

    with destino_engine.begin() as conn:
        conn.execute(text(f"IF OBJECT_ID('dbo.{nombre}', 'P') IS NOT NULL DROP PROCEDURE dbo.{nombre}"))
        conn.execute(text(definicion))


def _crear_tabla_staging_vacia(origen_engine, destino_engine, nombre_tabla: str) -> None:
    metadata_destino = MetaData()
    _asegurar_tabla_destino(origen_engine, destino_engine, nombre_tabla, metadata_destino)
    # Si la tabla ya existía (ej. una prueba anterior la recreó vía
    # to_sql(if_exists="replace") con datos) create_all no la toca -- se
    # vacía explícito para garantizar "solo estructura, vacía".
    _vaciar_tabla_destino(destino_engine, nombre_tabla)


def main() -> int:
    origen_engine = create_engine(_conn_str("ORIGEN"))
    destino_engine = create_engine(_conn_str("DESTINO"))

    logger.info("=== Copia única de objetos de Carga hacia PIQ_IA ===")
    hubo_error = False

    for nombre in TABLAS_LOG_CON_DATOS:
        try:
            filas = _copiar_tabla(origen_engine, destino_engine, nombre)
            logger.info("OK   tabla log       %-30s %d filas", nombre, filas)
        except Exception:
            hubo_error = True
            logger.exception("ERROR al copiar tabla log %s", nombre)

    for nombre in TABLAS_STAGING_VACIAS:
        try:
            _crear_tabla_staging_vacia(origen_engine, destino_engine, nombre)
            logger.info("OK   tabla staging   %-30s (solo estructura, vacía)", nombre)
        except Exception:
            hubo_error = True
            logger.exception("ERROR al crear tabla staging %s", nombre)

    for nombre in PROCEDURES:
        try:
            _copiar_procedimiento(origen_engine, destino_engine, nombre)
            logger.info("OK   procedure       %s", nombre)
        except Exception:
            hubo_error = True
            logger.exception("ERROR al copiar procedure %s", nombre)

    logger.info("=== Copia única de objetos de Carga finalizada (%s) ===", "con errores" if hubo_error else "OK")
    return 1 if hubo_error else 0


if __name__ == "__main__":
    sys.exit(main())

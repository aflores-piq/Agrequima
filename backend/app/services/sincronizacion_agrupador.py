"""Sincroniza Grupo/CodigoAgrupador (plaguicidas) y
ProductoAgrupado/CodigoAgrupador (nutrientes) en las tablas finales
contra el catálogo actual — misma lógica reutilizada por:
  1. el backfill retroactivo de una sola vez (script), y
  2. el guardado de un Agrupador/ProductoAgrupado desde la pantalla de
     Nomenclatura (para que aplique de inmediato a todas las filas que
     comparten esa misma clave, no solo la fila que se estaba editando).

La clave de cruce se recalcula aquí mismo en vez de depender de una
columna persistida, porque dbo.Importacion / dbo.Nutrientes no guardan
la clave normalizada — solo el ETL de carga la usa como staging
temporal.

La clave del catálogo se calcula en Python con normalizar()
(text_utils.py): TRIM + UPPER + colapsar espacios internos múltiples a
uno solo. El JOIN debe calcular la MISMA clave sobre
ingrediente_act/NombreComercial — UPPER(LTRIM(RTRIM(...))) por sí solo
NO colapsa espacios internos, así que un valor con doble espacio
interno nunca hacía match contra el catálogo (la fila se quedaba con
Grupo/ProductoAgrupado NULL para siempre, aunque el catálogo ya tuviera
el agrupador correcto) — exactamente el bug de "sigue apareciendo sin
agrupador después de guardar". _normalizar_sql() replica el colapsado
de espacios encadenando REPLACE('  ', ' ') varias veces (cada pasada
reduce a la mitad el largo de una racha de espacios)."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def _normalizar_sql(columna: str) -> str:
    """Expresión SQL equivalente a normalizar() (text_utils.py): TRIM +
    UPPER + colapsar espacios internos múltiples a uno solo."""
    expr = columna
    for _ in range(5):  # colapsa rachas de hasta 2^5 = 32 espacios
        expr = f"REPLACE({expr}, '  ', ' ')"
    return f"UPPER(LTRIM(RTRIM({expr})))"


def sincronizar_agrupador_plaguicidas(db: Session) -> int:
    clave_importacion = _normalizar_sql("i.ingrediente_act")
    resultado = db.execute(text(f"""
        UPDATE i
        SET i.Grupo = c.Agrupador, i.CodigoAgrupador = c.Codigo
        FROM dbo.Importacion i
        JOIN dbo.CatalogoNomenclaturaPlaguicidas c
          ON c.IngredienteActivo_Key = {clave_importacion}
        WHERE i.ingrediente_act IS NOT NULL
          AND (
              ISNULL(i.Grupo, '') <> ISNULL(c.Agrupador, '')
           OR ISNULL(i.CodigoAgrupador, '') <> ISNULL(c.Codigo, '')
          )
    """))
    return resultado.rowcount


def sincronizar_agrupador_nutrientes(db: Session) -> int:
    clave_nutriente = _normalizar_sql("n.NombreComercial")
    resultado = db.execute(text(f"""
        UPDATE n
        SET n.ProductoAgrupado = c.ProductoAgrupado, n.CodigoAgrupador = c.Codigo
        FROM dbo.Nutrientes n
        JOIN dbo.CatalogoAgrupadorNutrientes c
          ON c.NombreComercial_Key = {clave_nutriente}
        WHERE n.NombreComercial IS NOT NULL
          AND (
              ISNULL(n.ProductoAgrupado, '') <> ISNULL(c.ProductoAgrupado, '')
           OR ISNULL(n.CodigoAgrupador, '') <> ISNULL(c.Codigo, '')
          )
    """))
    return resultado.rowcount

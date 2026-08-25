"""Sincroniza Grupo/CodigoAgrupador (plaguicidas) y
ProductoAgrupado/CodigoAgrupador (nutrientes) en las tablas finales
contra el catálogo actual — misma lógica reutilizada por:
  1. el backfill retroactivo de una sola vez (script), y
  2. el guardado de un Agrupador nuevo desde la pantalla de Excepciones
     (para que aplique de inmediato a todas las filas que comparten esa
     misma clave, no solo la fila que se estaba editando).

La clave de cruce se recalcula aquí mismo (TRIM + UPPER) en vez de
depender de una columna persistida, porque dbo.Importacion / dbo.Nutrientes
no guardan la clave normalizada — solo el ETL de carga la usa como
staging temporal."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def sincronizar_agrupador_plaguicidas(db: Session) -> int:
    resultado = db.execute(text("""
        UPDATE i
        SET i.Grupo = c.Agrupador, i.CodigoAgrupador = c.Codigo
        FROM dbo.Importacion i
        JOIN dbo.CatalogoNomenclaturaPlaguicidas c
          ON c.IngredienteActivo_Key = UPPER(LTRIM(RTRIM(i.ingrediente_act)))
        WHERE i.ingrediente_act IS NOT NULL
          AND (
              ISNULL(i.Grupo, '') <> ISNULL(c.Agrupador, '')
           OR ISNULL(i.CodigoAgrupador, '') <> ISNULL(c.Codigo, '')
          )
    """))
    return resultado.rowcount


def sincronizar_agrupador_nutrientes(db: Session) -> int:
    resultado = db.execute(text("""
        UPDATE n
        SET n.ProductoAgrupado = c.ProductoAgrupado, n.CodigoAgrupador = c.Codigo
        FROM dbo.Nutrientes n
        JOIN dbo.CatalogoAgrupadorNutrientes c
          ON c.NombreComercial_Key = UPPER(LTRIM(RTRIM(n.NombreComercial)))
        WHERE n.NombreComercial IS NOT NULL
          AND (
              ISNULL(n.ProductoAgrupado, '') <> ISNULL(c.ProductoAgrupado, '')
           OR ISNULL(n.CodigoAgrupador, '') <> ISNULL(c.Codigo, '')
          )
    """))
    return resultado.rowcount

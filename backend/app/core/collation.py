"""Collation explícita para mezclar columnas homologadas con columnas originales (UN solo lugar).

PROBLEMA QUE RESUELVE: en el servidor real las columnas originales (Importacion.importador, Importacion.producto,
Nutrientes.NombreComercial, Nutrientes.EmpresaImportadora, ...) están en Modern_Spanish_CI_AS, pero las columnas que agregaron
los scripts 26 y 27 (EmpresaHomologada, NombreComercialHomologado, ...) quedaron en la collation por defecto de la base
(SQL_Latin1_General_CP1_CI_AS). SQL Server no puede resolver COALESCE(homologada, original) entre dos collations distintas y
responde error 446/468 ("Cannot resolve collation conflict ... in CASE operator") en cuanto el dashboard hace
COUNT(DISTINCT COALESCE(...)), GROUP BY, IS NOT NULL, etc. En la base de desarrollo todas las columnas tienen la misma
collation y por eso el error no se veía.

REGLA: toda expresión que MEZCLE una columna homologada con una original (COALESCE, comparación, DISTINCT, GROUP BY,
ORDER BY, UNION, JOIN) pasa por estas funciones. La collation explícita es la de las columnas ORIGINALES
(Modern_Spanish_CI_AS) -- NO DATABASE_DEFAULT -- para que agrupar y ordenar se comporte igual que antes de la homologación.
Si las dos columnas ya tienen esa collation, el COLLATE explícito no cambia el resultado.

Las comparaciones EXACTAS entre columnas homologadas (para detectar cambios en la sincronización) usan Latin1_General_BIN2
a ambos lados, que es explícita y por eso tampoco tiene conflicto; no pasan por aquí.
"""

from sqlalchemy import func

# Collation de las columnas originales del servidor real (ver docstring). El script 29 alinea las columnas homologadas con ella.
COLLATION_ORIGINALES = "Modern_Spanish_CI_AS"


def con_collation_originales(columna):
    """`columna COLLATE Modern_Spanish_CI_AS` (expresión SQLAlchemy)."""
    return columna.collate(COLLATION_ORIGINALES)


def coalesce_homologado(homologada, original):
    """COALESCE(homologada, original) seguro sin importar la collation de cada columna: el nombre homologado y, si no hay,
    el original. Devuelve una expresión SQLAlchemy con COLLATE Modern_Spanish_CI_AS explícito en los dos lados."""
    return func.coalesce(con_collation_originales(homologada), con_collation_originales(original))


def sql_collate_originales(expresion_sql: str) -> str:
    """Igual que con_collation_originales, para SQL escrito a mano: devuelve `(<expr> COLLATE Modern_Spanish_CI_AS)`."""
    return f"({expresion_sql} COLLATE {COLLATION_ORIGINALES})"


def sql_coalesce_homologado(homologada_sql: str, original_sql: str) -> str:
    """Igual que coalesce_homologado, para SQL escrito a mano (text())."""
    return f"COALESCE({homologada_sql} COLLATE {COLLATION_ORIGINALES}, {original_sql} COLLATE {COLLATION_ORIGINALES})"

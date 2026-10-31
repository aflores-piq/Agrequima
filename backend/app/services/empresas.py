"""Homologación de empresas (Plaguicidas y Nutrientes): clave normalizada, sincronización y conteo de empresas nuevas.

La clave de una empresa la calcula UNA sola función de SQL Server, dbo.fn_ClaveEmpresa (script 26): mayúsculas, sin tildes,
sin puntos ni comas, espacios colapsados y las variantes de sociedad anónima (S.A., S. A., SA, S A, SOCIEDAD ANONIMA) unificadas
en "SA". La usan el script 26 (semilla), los procedimientos de carga (usp_CargarImportacion / usp_CargarNutrientes) y este
módulo, así que cargas, script y sincronización siempre dan la misma clave. No une errores de tipeo ni quita otras palabras.

dbo.CatalogoEmpresas (EmpresaKey -> EmpresaHomologada) es UN catálogo compartido por las dos tablas; la columna
EmpresaHomologada de dbo.Importacion y dbo.Nutrientes se sincroniza desde él (mismo patrón que Grupo / ProductoAgrupado). Los
datos originales (importador, EmpresaImportadora) NO se modifican nunca; los tableros usan COALESCE(EmpresaHomologada, original).
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session


def clave_empresa(db: Session | Connection, texto: str | None) -> str | None:
    """Clave normalizada de una empresa (la misma que usan el script 26 y las cargas); None si el texto está vacío."""
    if texto is None:
        return None
    return db.execute(text("SELECT dbo.fn_ClaveEmpresa(:t)"), {"t": texto}).scalar()


def sincronizar_empresas(db: Session) -> int:
    """Pone en EmpresaHomologada de dbo.Importacion y dbo.Nutrientes el nombre del catálogo para la clave de cada fila (y
    NULL si su clave ya no está en el catálogo). Solo toca filas cuyo valor cambia. Devuelve cuántas filas cambió; el commit
    lo hace quien llama (misma convención de sincronizacion_agrupador.py)."""
    total = 0
    for tabla, columna in (("Importacion", "importador"), ("Nutrientes", "EmpresaImportadora")):
        total += db.execute(text(f"""
            UPDATE t
            SET t.EmpresaHomologada = c.EmpresaHomologada
            FROM dbo.{tabla} t
            JOIN dbo.CatalogoEmpresas c
              ON c.EmpresaKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveEmpresa(t.{columna}) COLLATE DATABASE_DEFAULT
            WHERE ISNULL(t.EmpresaHomologada, N'') COLLATE Latin1_General_BIN2 <> c.EmpresaHomologada COLLATE Latin1_General_BIN2
        """)).rowcount
        total += db.execute(text(f"""
            UPDATE t
            SET t.EmpresaHomologada = NULL
            FROM dbo.{tabla} t
            WHERE t.EmpresaHomologada IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM dbo.CatalogoEmpresas c
                  WHERE c.EmpresaKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveEmpresa(t.{columna}) COLLATE DATABASE_DEFAULT)
        """)).rowcount
    return total


def max_log_empresas(conn: Connection) -> int:
    """Último LogId de dbo.log_ExcepcionesEmpresas antes de una carga (para contar solo las empresas que la carga agregue)."""
    return int(conn.execute(text("SELECT ISNULL(MAX(LogId), 0) FROM dbo.log_ExcepcionesEmpresas")).scalar() or 0)


def contar_empresas_sin_homologar(conn: Connection, max_id_antes: int) -> int:
    """Empresas (una fila por empresa) que la carga registró en dbo.log_ExcepcionesEmpresas: su clave no estaba en el catálogo."""
    return int(
        conn.execute(
            text("SELECT COUNT(*) FROM dbo.log_ExcepcionesEmpresas WHERE LogId > :max_id"), {"max_id": max_id_antes}
        ).scalar()
        or 0
    )

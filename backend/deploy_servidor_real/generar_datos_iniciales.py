"""Genera 03_cargar_datos_iniciales.sql (en esta misma carpeta) -- un
dump SQL autocontenido con los datos REALES actuales de las 4 tablas
de negocio de AGREQUIMA (Importacion, Nutrientes,
CatalogoNomenclaturaPlaguicidas, CatalogoAgrupadorNutrientes), para
llevar al servidor real donde no hay conexión en vivo hacia esta
laptop -- mismo patrón que 01_crear_base_piq_ia.sql y
02_seed_roles_y_admin.sql: un .sql que alguien ejecuta a mano por SSMS.

NO toca Roles/Usuarios (eso ya está bien en el servidor real, es un
problema aparte de este script).

Herramienta permanente (no un descartable de una sola vez): el día que
haga falta refrescar PIQ_IA con datos más nuevos de AGREQUIMA, alcanza
con volver a correr esto -- por eso vive junto al .sql que genera, en
vez de en una carpeta de temporales.

Uso (desde la raíz del repositorio):
    python backend/deploy_servidor_real/generar_datos_iniciales.py
"""

import datetime
import decimal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402

TABLAS = [
    "Importacion",
    "Nutrientes",
    "CatalogoNomenclaturaPlaguicidas",
    "CatalogoAgrupadorNutrientes",
]

FILAS_POR_INSERT = 1000  # tope real de SQL Server para VALUES multi-fila

SALIDA = Path(__file__).resolve().parent / "03_cargar_datos_iniciales.sql"


def _tiene_identity(db, tabla: str) -> bool:
    n = db.execute(
        text("SELECT COUNT(*) FROM sys.identity_columns WHERE object_id = OBJECT_ID('dbo.' + :t)"),
        {"t": tabla},
    ).scalar()
    return bool(n)


def _valor_sql(valor) -> str:
    """Convierte un valor Python (tal como lo devuelve pyodbc/SQLAlchemy)
    a su literal T-SQL correspondiente, con el escapado correcto."""
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, (int, float, decimal.Decimal)):
        return str(valor)
    if isinstance(valor, datetime.datetime):
        # SIN guiones a propósito: confirmado con evidencia real que
        # 'YYYY-MM-DD ...' para el tipo DATETIME (a diferencia de DATE)
        # SÍ depende del DATEFORMAT de la sesión -- este servidor tiene
        # el login con idioma "Español" (DATEFORMAT=dmy por default), y
        # bajo esa sesión SQL Server intenta leer "2026" como el DÍA,
        # lo cual está fuera de rango y hace fallar TODA la carga. El
        # formato "YYYYMMDD HH:MM:SS.fff" (sin separadores en la fecha)
        # es el único 100% seguro para DATETIME sin importar el idioma
        # de la sesión que ejecute este script.
        return "'" + valor.strftime("%Y%m%d %H:%M:%S.%f")[:-3] + "'"
    if isinstance(valor, datetime.date):
        # DATE (a diferencia de DATETIME) SÍ es seguro con guiones bajo
        # cualquier DATEFORMAT -- confirmado también contra este mismo
        # servidor en sesión con idioma Español.
        return "'" + valor.strftime("%Y-%m-%d") + "'"
    # Texto: escapar comillas simples duplicándolas (regla estándar T-SQL).
    texto = str(valor).replace("'", "''")
    return "'" + texto + "'"


def _generar_tabla(db, tabla: str) -> tuple[str, int]:
    resultado = db.execute(text(f"SELECT * FROM dbo.{tabla}"))
    columnas = list(resultado.keys())
    filas = resultado.fetchall()
    con_identity = _tiene_identity(db, tabla)

    columnas_sql = ", ".join(f"[{c}]" for c in columnas)

    partes = []
    partes.append(f"PRINT 'Cargando {tabla}...';")
    partes.append("BEGIN TRY")
    partes.append("    BEGIN TRANSACTION;")
    partes.append(f"    TRUNCATE TABLE dbo.{tabla};")
    if con_identity:
        partes.append(f"    SET IDENTITY_INSERT dbo.{tabla} ON;")

    if not filas:
        partes.append("    -- (tabla sin filas en el origen -- queda vacía)")
    else:
        for inicio in range(0, len(filas), FILAS_POR_INSERT):
            bloque = filas[inicio : inicio + FILAS_POR_INSERT]
            valores = ",\n        ".join(
                "(" + ", ".join(_valor_sql(v) for v in fila) + ")" for fila in bloque
            )
            partes.append(f"    INSERT INTO dbo.{tabla} ({columnas_sql}) VALUES")
            partes.append(f"        {valores};")

    if con_identity:
        partes.append(f"    SET IDENTITY_INSERT dbo.{tabla} OFF;")
    partes.append("    COMMIT TRANSACTION;")
    partes.append(f"    PRINT 'OK: {tabla} cargada ({len(filas)} filas)';")
    partes.append("END TRY")
    partes.append("BEGIN CATCH")
    if con_identity:
        # SET IDENTITY_INSERT es de sesión, no transaccional -- el ROLLBACK
        # de abajo no lo revierte. Si el error ocurrió después de haberlo
        # prendido, hay que apagarlo a mano o la sesión queda "trabada"
        # (no deja prender IDENTITY_INSERT en ninguna otra tabla después).
        partes.append(f"    SET IDENTITY_INSERT dbo.{tabla} OFF;")
    partes.append("    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;")
    partes.append(
        f"    PRINT 'ERROR al cargar {tabla}: ' + ERROR_MESSAGE() "
        f"+ ' (línea ' + CAST(ERROR_LINE() AS VARCHAR(20)) + ')';"
    )
    partes.append("END CATCH")
    partes.append("GO")
    partes.append("")

    return "\n".join(partes), len(filas)


def main() -> None:
    db = SessionLocal()
    encabezado = f"""/* =====================================================================
   PIQ_IA -- Carga de datos iniciales (Importacion, Nutrientes,
   CatalogoNomenclaturaPlaguicidas, CatalogoAgrupadorNutrientes)
   =====================================================================
   Generado automáticamente desde AGREQUIMA (Desarrollo-2) el
   {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")} -- NO editar a mano.

   Correr esto DESPUÉS de 01_crear_base_piq_ia.sql y
   02_seed_roles_y_admin.sql, conectado con SSMS a la base PIQ_IA del
   servidor real.

   Qué hace, por cada una de las 4 tablas: TRUNCATE + INSERT de todas
   las filas reales (en bloques de hasta {FILAS_POR_INSERT}, el máximo
   que permite SQL Server por sentencia VALUES), preservando los IDs
   IDENTITY exactos donde corresponde. Envuelto en TRY/CATCH con su
   propia transacción por tabla: si una tabla falla, las demás no se
   ven afectadas, y el motivo exacto queda impreso en el panel de
   Mensajes de SSMS.

   Es seguro volver a correrlo las veces que haga falta -- siempre
   trunca antes de insertar, nunca duplica.

   NO toca Roles ni Usuarios -- eso se maneja aparte
   (02_seed_roles_y_admin.sql) y no se pisa acá.
   ===================================================================== */

USE PIQ_IA;
GO

"""

    bloques = []
    resumen = []
    for tabla in TABLAS:
        sql_tabla, n = _generar_tabla(db, tabla)
        bloques.append(sql_tabla)
        resumen.append((tabla, n))

    pie = """
SELECT
    'Importacion' AS tabla, COUNT(*) AS filas FROM dbo.Importacion
UNION ALL
SELECT 'Nutrientes', COUNT(*) FROM dbo.Nutrientes
UNION ALL
SELECT 'CatalogoNomenclaturaPlaguicidas', COUNT(*) FROM dbo.CatalogoNomenclaturaPlaguicidas
UNION ALL
SELECT 'CatalogoAgrupadorNutrientes', COUNT(*) FROM dbo.CatalogoAgrupadorNutrientes;
GO
"""

    contenido = encabezado + "\n".join(bloques) + pie
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig (con BOM), no utf-8 a secas: confirmado con evidencia real
    # que sqlcmd, sin un BOM que le indique que el archivo es UTF-8, lo lee
    # con la codepage ANSI local y corrompe cualquier tilde/ñ (a diferencia
    # de SSMS, que si detecta UTF-8 sin BOM correctamente -- pero como este
    # script también se valida por sqlcmd, hay que escribirlo con BOM para
    # que ambos lo lean igual de bien).
    SALIDA.write_text(contenido, encoding="utf-8-sig")

    db.close()

    print(f"Archivo generado: {SALIDA}")
    print(f"Tamaño: {SALIDA.stat().st_size / (1024 * 1024):.2f} MB")
    print("Filas por tabla incluidas en el .sql:")
    for tabla, n in resumen:
        print(f"  {tabla}: {n}")


if __name__ == "__main__":
    main()

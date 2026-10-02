"""Genera 16_datos_financiero.sql (en esta misma carpeta, o
16a/16b/... si el resultado es demasiado grande para SSMS) -- un dump
SQL autocontenido con los datos REALES actuales de las 10 tablas del
módulo Financiero, para llevar al servidor real donde no hay conexión
en vivo hacia esta laptop. Mismo patrón exacto que
generar_datos_iniciales.py (03_cargar_datos_iniciales.sql) -- ver ese
archivo para el detalle de cada decisión (formato de fecha sin
guiones para DATETIME, BOM utf-8-sig, IDENTITY_INSERT, TRY/CATCH con
transacción propia por tabla).

Herramienta permanente: el día que haga falta refrescar PIQ_IA con
datos más nuevos de Financiero, alcanza con volver a correr esto.

Uso (desde la raíz del repositorio):
    python backend/deploy_servidor_real/generar_datos_financiero.py
"""

import datetime
import decimal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402

TABLAS = [
    "BalanceSaldos",
    "BalanceGeneral",
    "CatalogoCuentas",
    "CentrosDeCosto",
    "Presupuestos",
    "AsociadosCuota",
    "ChequesCirculacion",
    "SaldosBancos",
    "SaldoBancario",
    "OtroIngreso",
]

FILAS_POR_INSERT = 1000  # tope real de SQL Server para VALUES multi-fila

# Tope de tamaño por archivo antes de partir en 16a/16b/... -- SSMS
# puede abrir archivos más grandes, pero se vuelve lento/pesado de
# revisar a mano; 15MB es un margen cómodo (igual criterio que
# "03_cargar_datos_iniciales.sql", que ya pesa ~10MB con 4 tablas).
LIMITE_MB_POR_ARCHIVO = 15

CARPETA = Path(__file__).resolve().parent


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
        # Sin guiones a propósito -- ver generar_datos_iniciales.py para
        # el porqué (DATEFORMAT de sesión en español puede leer mal
        # "YYYY-MM-DD" en una columna DATETIME).
        return "'" + valor.strftime("%Y%m%d %H:%M:%S.%f")[:-3] + "'"
    if isinstance(valor, datetime.date):
        return "'" + valor.strftime("%Y-%m-%d") + "'"
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


def _encabezado(sufijo: str, tablas_de_este_archivo: list[str]) -> str:
    return f"""/* =====================================================================
   PIQ_IA -- Carga de datos del módulo Financiero{sufijo}
   =====================================================================
   Generado automáticamente desde la base de desarrollo el
   {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")} -- NO editar a mano
   (volver a correr generar_datos_financiero.py si hace falta refrescar).

   Correr esto DESPUÉS de 01_crear_base_piq_ia.sql, 02_seed_roles_y_admin.sql
   y 15_tablas_financiero.sql + 13_saldos_bancos_financiero.sql +
   14_otro_ingreso_financiero.sql (las 10 tablas deben existir antes),
   conectado con SSMS a la base PIQ_IA del servidor real.

   Tablas en este archivo: {", ".join(tablas_de_este_archivo)}.

   TRUNCATE + INSERT por tabla (bloques de hasta {FILAS_POR_INSERT} filas),
   envuelto en TRY/CATCH con su propia transacción: si una tabla falla,
   las demás no se ven afectadas. Es seguro volver a correrlo las veces
   que haga falta -- siempre trunca antes de insertar, nunca duplica.
   ===================================================================== */

USE PIQ_IA;
GO

"""


def main() -> None:
    db = SessionLocal()

    bloques_por_tabla: list[tuple[str, str, int]] = []
    for tabla in TABLAS:
        sql_tabla, n = _generar_tabla(db, tabla)
        bloques_por_tabla.append((tabla, sql_tabla, n))
    db.close()

    # Partir en archivos de hasta LIMITE_MB_POR_ARCHIVO, SIN cortar una
    # tabla a la mitad entre 2 archivos (cada tabla es atómica dentro de
    # su propio archivo).
    archivos: list[list[tuple[str, str, int]]] = []
    actual: list[tuple[str, str, int]] = []
    tamano_actual = 0
    limite_bytes = LIMITE_MB_POR_ARCHIVO * 1024 * 1024
    for tabla, sql_tabla, n in bloques_por_tabla:
        tamano_bloque = len(sql_tabla.encode("utf-8"))
        if actual and tamano_actual + tamano_bloque > limite_bytes:
            archivos.append(actual)
            actual = []
            tamano_actual = 0
        actual.append((tabla, sql_tabla, n))
        tamano_actual += tamano_bloque
    if actual:
        archivos.append(actual)

    resumen = []
    if len(archivos) == 1:
        nombres = ["16_datos_financiero.sql"]
    else:
        letras = "abcdefghijklmnopqrstuvwxyz"
        nombres = [f"16{letras[i]}_datos_financiero.sql" for i in range(len(archivos))]

    for idx, (nombre, bloques) in enumerate(zip(nombres, archivos)):
        tablas_de_este = [t for t, _, _ in bloques]
        sufijo = "" if len(archivos) == 1 else f" ({idx + 1}/{len(archivos)})"
        encabezado = _encabezado(sufijo, tablas_de_este)
        pie = ""
        if idx == len(archivos) - 1:
            # SELECT final de verificación SOLO en el último archivo (ya
            # corrieron todos los TRUNCATE+INSERT de las 10 tablas).
            selects = "\nUNION ALL\n".join(f"SELECT '{t}', COUNT(*) FROM dbo.{t}" for t in TABLAS[1:])
            pie = f"""
SELECT '{TABLAS[0]}' AS tabla, COUNT(*) AS filas FROM dbo.{TABLAS[0]}
UNION ALL
{selects};
GO
"""
        contenido = encabezado + "\n".join(b for _, b, _ in bloques) + pie
        ruta = CARPETA / nombre
        ruta.write_text(contenido, encoding="utf-8-sig")
        resumen.append((nombre, ruta.stat().st_size / (1024 * 1024), [(t, n) for t, _, n in bloques]))

    print(f"Archivos generados: {len(archivos)}")
    for nombre, mb, tablas_n in resumen:
        print(f"  {nombre} -- {mb:.2f} MB")
        for t, n in tablas_n:
            print(f"      {t}: {n} filas")


if __name__ == "__main__":
    main()

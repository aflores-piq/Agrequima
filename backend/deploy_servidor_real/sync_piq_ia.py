"""Sincronizacion nocturna de PIQ_IA: espeja tablas de solo lectura desde
la base origen (la base real del cliente, o -- mientras se prueba -- la
base de Desarrollo-2) hacia la base PIQ_IA de este servidor.

Version AUTONOMA para este servidor: no depende del backend de la app
(no hace falta copiar el resto del repositorio, ni tener FastAPI
instalado) -- solo este archivo + un ".env" en la misma carpeta + las
librerias listadas en requirements.txt. Ver LEEME.txt para la
instalacion paso a paso.

Genérico a propósito: la lista de tablas a espejar se lee de la
variable de entorno SYNC_TABLAS (separadas por coma) -- para agregar
tablas de otros proyectos (Financiero, Indicadores) en el futuro,
alcanza con ampliar esa variable en el .env, sin tocar este código.

Para cada tabla: refleja el esquema real desde el origen, crea la misma
tabla en destino si no existe, y hace un refresh completo (vacía +
inserta todas las filas actuales) -- así el espejo queda idéntico a la
fuente en cada corrida.

Uso:
    python sync_piq_ia.py
"""

import logging
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, text

CARPETA_SCRIPT = Path(__file__).resolve().parent
load_dotenv(CARPETA_SCRIPT / ".env")

ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

TABLAS_A_ESPEJAR = [t.strip() for t in os.getenv("SYNC_TABLAS", "").split(",") if t.strip()]

LOG_DIR = CARPETA_SCRIPT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "sync_piq_ia.log"

logger = logging.getLogger("sync_piq_ia")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler_archivo = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _handler_archivo.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_handler_archivo)
    logger.addHandler(logging.StreamHandler(sys.stdout))


def _conn_str(prefijo: str) -> str:
    """Arma la cadena de conexión leyendo SYNC_{prefijo}_DB_* del .env."""
    server = os.getenv(f"SYNC_{prefijo}_DB_SERVER")
    nombre = os.getenv(f"SYNC_{prefijo}_DB_NAME")
    usuario = os.getenv(f"SYNC_{prefijo}_DB_USER")
    password = os.getenv(f"SYNC_{prefijo}_DB_PASSWORD")
    faltantes = [
        var for var, val in (("SERVER", server), ("NAME", nombre), ("USER", usuario), ("PASSWORD", password))
        if not val
    ]
    if faltantes:
        raise RuntimeError(
            f"Faltan variables de entorno SYNC_{prefijo}_DB_{{{','.join(faltantes)}}} en el .env "
            f"(¿copiaste .env.ejemplo a .env y lo completaste?)"
        )
    return (
        f"mssql+pyodbc://{usuario}:{quote_plus(password)}@{server}/{nombre}"
        f"?driver={ODBC_DRIVER.replace(' ', '+')}"
    )


def _tiene_columna_identity(engine, tabla: str) -> bool:
    with engine.connect() as conn:
        n = conn.execute(
            text(
                "SELECT COUNT(*) FROM sys.identity_columns "
                "WHERE object_id = OBJECT_ID('dbo.' + :t)"
            ),
            {"t": tabla},
        ).scalar()
    return bool(n)


def _crear_tabla_log_si_no_existe(destino_engine) -> None:
    with destino_engine.begin() as conn:
        conn.execute(
            text(
                """
                IF OBJECT_ID('dbo.SyncLog') IS NULL
                CREATE TABLE dbo.SyncLog (
                    LogId         INT IDENTITY(1,1) PRIMARY KEY,
                    FechaCorrida  DATETIME NOT NULL DEFAULT GETDATE(),
                    Tabla         VARCHAR(200) NOT NULL,
                    FilasCopiadas INT NULL,
                    Estado        VARCHAR(20) NOT NULL,
                    MensajeError  NVARCHAR(MAX) NULL
                )
                """
            )
        )


def _registrar_log(destino_engine, tabla: str, filas, estado: str, mensaje_error=None) -> None:
    with destino_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dbo.SyncLog (Tabla, FilasCopiadas, Estado, MensajeError) "
                "VALUES (:t, :f, :e, :m)"
            ),
            {"t": tabla, "f": filas, "e": estado, "m": mensaje_error},
        )


def _copiar_tabla(origen_engine, destino_engine, nombre_tabla: str) -> int:
    """Refleja el esquema real de `nombre_tabla` desde el origen (mismos
    tipos/largos/PK que la fuente, no un esquema adivinado), lo crea en
    destino si no existe, y reemplaza todo su contenido por el actual
    del origen. Pensado para tablas SIN relaciones FK entre sí (que es
    el caso de las 4 tablas de datos que trae este mecanismo)."""
    metadata_origen = MetaData()
    tabla_origen = Table(nombre_tabla, metadata_origen, schema="dbo", autoload_with=origen_engine)

    metadata_destino = MetaData()
    tabla_destino = tabla_origen.to_metadata(metadata_destino)
    metadata_destino.create_all(destino_engine, tables=[tabla_destino])

    df = pd.read_sql(f"SELECT * FROM dbo.{nombre_tabla}", origen_engine)
    con_identity = _tiene_columna_identity(origen_engine, nombre_tabla)

    with destino_engine.begin() as conn:
        conn.execute(text(f"DELETE FROM dbo.{nombre_tabla}"))
        if con_identity:
            conn.execute(text(f"SET IDENTITY_INSERT dbo.{nombre_tabla} ON"))
        if not df.empty:
            df.to_sql(nombre_tabla, conn, schema="dbo", if_exists="append", index=False)
        if con_identity:
            conn.execute(text(f"SET IDENTITY_INSERT dbo.{nombre_tabla} OFF"))

    return len(df)


def main() -> int:
    if not TABLAS_A_ESPEJAR:
        logger.error("SYNC_TABLAS está vacío en .env — no hay nada que espejar.")
        return 1

    origen_engine = create_engine(_conn_str("ORIGEN"))
    destino_engine = create_engine(_conn_str("DESTINO"))

    _crear_tabla_log_si_no_existe(destino_engine)

    logger.info("=== Iniciando sincronización PIQ_IA (%d tablas configuradas) ===", len(TABLAS_A_ESPEJAR))
    hubo_error = False
    for tabla in TABLAS_A_ESPEJAR:
        try:
            filas = _copiar_tabla(origen_engine, destino_engine, tabla)
            logger.info("OK   %-40s %d filas", tabla, filas)
            _registrar_log(destino_engine, tabla, filas, "OK")
        except Exception as exc:
            hubo_error = True
            logger.exception("ERROR al copiar %s", tabla)
            _registrar_log(destino_engine, tabla, None, "Error", str(exc))

    logger.info("=== Sincronización PIQ_IA finalizada (%s) ===", "con errores" if hubo_error else "OK")
    return 1 if hubo_error else 0


if __name__ == "__main__":
    sys.exit(main())

"""Sincronización nocturna de PIQ_IA: espeja tablas de solo lectura desde
la base origen (fase de prueba: AGREQUIMA en esta misma instancia; a
futuro, la base real del cliente vía VPN) hacia la base PIQ_IA.

Genérico a propósito: la lista de tablas a espejar se lee de la variable
de entorno SYNC_TABLAS (separadas por coma), no está escrita a mano en
este archivo — así, cuando se agreguen las tablas de los proyectos
Financiero e Indicadores, alcanza con ampliar esa variable, sin tocar
este código. Para cada tabla: refleja el esquema real desde el origen,
crea la misma tabla en destino si no existe, y hace un refresh completo
(TRUNCATE + INSERT de todas las filas actuales) — así el espejo queda
idéntico a la fuente en cada corrida, sin arrastrar filas que ya se
borraron del lado origen.

Mismo estilo de conexión que el resto del backend (SQLAlchemy + pyodbc,
config por variables de entorno vía .env en la raíz del repo, sin nada
hardcodeado) — ver app/core/db.py / app/core/config.py, del cual esto es
independiente a propósito: origen y destino son conexiones separadas de
la que usa la app en producción, y ese engine no se toca ni se importa
acá.

Uso:
    python -m app.scripts.sync_piq_ia
"""

import logging
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, text

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")

ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

TABLAS_A_ESPEJAR = [t.strip() for t in os.getenv("SYNC_TABLAS", "").split(",") if t.strip()]

LOG_DIR = ROOT_DIR / "logs"
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
    """Arma la cadena de conexión leyendo SYNC_{prefijo}_DB_* del .env —
    mismo formato mssql+pyodbc que app/core/db.py."""
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
            f"Faltan variables de entorno SYNC_{prefijo}_DB_{{{','.join(faltantes)}}} en .env"
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


def _registrar_log(destino_engine, tabla: str, filas: int | None, estado: str, mensaje_error: str | None = None) -> None:
    with destino_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dbo.SyncLog (Tabla, FilasCopiadas, Estado, MensajeError) "
                "VALUES (:t, :f, :e, :m)"
            ),
            {"t": tabla, "f": filas, "e": estado, "m": mensaje_error},
        )


def _asegurar_tabla_destino(origen_engine, destino_engine, nombre_tabla: str, metadata_destino: MetaData) -> None:
    """Refleja el esquema real de `nombre_tabla` desde el origen (mismos
    tipos/largos/PK que la fuente, no un esquema adivinado) y lo crea en
    destino si no existe. `metadata_destino` debe ser el MISMO objeto
    entre varias tablas de un mismo grupo cuando hay FK entre ellas (ej.
    Usuarios -> Roles) — si no, cada tabla arranca de un MetaData nuevo
    (uso normal para tablas sin relación, como las del sync nocturno)."""
    metadata_origen = MetaData()
    tabla_origen = Table(nombre_tabla, metadata_origen, schema="dbo", autoload_with=origen_engine)
    tabla_destino = tabla_origen.to_metadata(metadata_destino)
    metadata_destino.create_all(destino_engine, tables=[tabla_destino])


def _vaciar_tabla_destino(destino_engine, nombre_tabla: str) -> None:
    """DELETE, no TRUNCATE: TRUNCATE falla en SQL Server si CUALQUIER
    otra tabla tiene una FK apuntando a esta, aunque esa tabla esté
    vacía — que es exactamente el caso de Roles/Usuarios una vez que
    Usuarios/AuditoriaCargas ya existen. Para grupos con FK entre sí,
    hay que vaciar en orden inverso (hijo antes que padre) — ver
    `_copiar_grupo_tablas`."""
    with destino_engine.begin() as conn:
        conn.execute(text(f"DELETE FROM dbo.{nombre_tabla}"))


def _insertar_filas_en_destino(origen_engine, destino_engine, nombre_tabla: str) -> int:
    df = pd.read_sql(f"SELECT * FROM dbo.{nombre_tabla}", origen_engine)
    con_identity = _tiene_columna_identity(origen_engine, nombre_tabla)

    with destino_engine.begin() as conn:
        if con_identity:
            conn.execute(text(f"SET IDENTITY_INSERT dbo.{nombre_tabla} ON"))
        if not df.empty:
            df.to_sql(nombre_tabla, conn, schema="dbo", if_exists="append", index=False)
        if con_identity:
            conn.execute(text(f"SET IDENTITY_INSERT dbo.{nombre_tabla} OFF"))

    return len(df)


def _copiar_tabla(origen_engine, destino_engine, nombre_tabla: str, metadata_destino: MetaData | None = None) -> int:
    """Refresh completo de una tabla SIN relaciones FK con otras del
    mismo grupo (caso del sync nocturno: Importacion/Nutrientes/
    Catalogo* no tienen FK entre sí) — crea si falta, vacía, reinserta.
    Para tablas CON FK entre sí (Roles/Usuarios/AuditoriaCargas), usar
    `_copiar_grupo_tablas` en su lugar."""
    if metadata_destino is None:
        metadata_destino = MetaData()
    _asegurar_tabla_destino(origen_engine, destino_engine, nombre_tabla, metadata_destino)
    _vaciar_tabla_destino(destino_engine, nombre_tabla)
    return _insertar_filas_en_destino(origen_engine, destino_engine, nombre_tabla)


def _copiar_grupo_tablas(origen_engine, destino_engine, tablas_en_orden_de_fk: list[str]) -> dict[str, int]:
    """Como _copiar_tabla, pero para un grupo de tablas con FK entre sí.
    `tablas_en_orden_de_fk`: la tabla referenciada va primero (ej.
    ["Roles", "Usuarios", "AuditoriaCargas"]). Internamente: crea todas
    en ese orden (mismo MetaData compartido, así las FK resuelven),
    vacía todas en orden INVERSO (hijo antes que padre, si no DELETE
    viola la FK), e inserta todas de nuevo en el orden original."""
    metadata_destino = MetaData()
    for tabla in tablas_en_orden_de_fk:
        _asegurar_tabla_destino(origen_engine, destino_engine, tabla, metadata_destino)

    for tabla in reversed(tablas_en_orden_de_fk):
        _vaciar_tabla_destino(destino_engine, tabla)

    filas_por_tabla = {}
    for tabla in tablas_en_orden_de_fk:
        filas_por_tabla[tabla] = _insertar_filas_en_destino(origen_engine, destino_engine, tabla)
    return filas_por_tabla


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

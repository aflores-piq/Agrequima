"""Copia UNA SOLA VEZ (a diferencia de sync_piq_ia.py, esto NO corre cada
noche ni está en la tarea programada) las tablas propias de la
aplicación hacia PIQ_IA: Roles, Usuarios, AuditoriaCargas.

A diferencia de Importacion/Nutrientes/Catalogo* (datos del cliente,
espejados cada noche desde el origen), estas tablas las administra
directamente la app misma (login, alta de usuarios, historial de
cargas) — sincronizarlas cada noche pisaría cualquier cambio hecho
directo contra PIQ_IA mientras se la usa/prueba. Se copian una vez para
dejar PIQ_IA funcional de punta a punta, y listo.

Reutiliza el mismo mecanismo genérico de reflejo de esquema + refresh
completo que sync_piq_ia.py (mismas conexiones SYNC_ORIGEN_DB_*/
SYNC_DESTINO_DB_* del .env) — el orden de la lista importa: Roles antes
que Usuarios (FK Usuarios.RolId -> Roles.RolId), Usuarios antes que
AuditoriaCargas (FK AuditoriaCargas.UsuarioId -> Usuarios.UsuarioId).

Uso (manual, se corre una sola vez):
    python -m app.scripts.copiar_tablas_app_piq_ia
"""

import sys

from sqlalchemy import create_engine

from app.scripts.sync_piq_ia import _conn_str, _copiar_grupo_tablas, logger

# Orden importa: la tabla referenciada por FK va primero (Roles antes
# que Usuarios, Usuarios antes que AuditoriaCargas) — _copiar_grupo_tablas
# crea/vacía/reinserta respetando esta dependencia en ambos sentidos.
TABLAS_APP = ["Roles", "Usuarios", "AuditoriaCargas"]


def main() -> int:
    origen_engine = create_engine(_conn_str("ORIGEN"))
    destino_engine = create_engine(_conn_str("DESTINO"))

    logger.info("=== Copia única de tablas propias de la app hacia PIQ_IA ===")
    try:
        filas_por_tabla = _copiar_grupo_tablas(origen_engine, destino_engine, TABLAS_APP)
        for tabla, filas in filas_por_tabla.items():
            logger.info("OK   %-25s %d filas", tabla, filas)
        hubo_error = False
    except Exception:
        hubo_error = True
        logger.exception("ERROR al copiar el grupo de tablas de la app")

    logger.info("=== Copia única finalizada (%s) ===", "con errores" if hubo_error else "OK")
    return 1 if hubo_error else 0


if __name__ == "__main__":
    sys.exit(main())

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.config import CORS_ORIGINS, FRONTEND_DIST_PATH
from app.routers import (
    admin_cargas,
    admin_nomenclatura,
    admin_usuarios,
    auth,
    dashboard,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Agrequima API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Todas las rutas de la API van bajo /api -- así ninguna puede volver a
# chocar con una ruta de React Router del lado del frontend (antes,
# GET /admin/usuarios y GET /admin/nomenclatura/{plaguicidas,nutrientes}
# coincidían EXACTO con las páginas de esos mismos nombres en el SPA, y
# la API ganaba siempre al recargar la página -- ver el catch-all más
# abajo). /health queda afuera a propósito: es un endpoint de
# infraestructura (monitoreo/balanceador), no de la API de negocio, y
# no choca con ninguna ruta del frontend.
app.include_router(auth.router, prefix="/api")
app.include_router(admin_cargas.router, prefix="/api")
app.include_router(admin_nomenclatura.router, prefix="/api")
app.include_router(admin_usuarios.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# --- Frontend compilado (SPA) -----------------------------------------
# Se registra DESPUÉS de todas las rutas de la API a propósito:
# Starlette hace match de rutas en el orden en que se registraron, no
# por especificidad -- así, cualquier ruta real de la API (todas bajo
# /api/..., más /health) se resuelve primero, y esto solo entra para
# lo que no matcheó ninguna ruta de arriba -- ya no puede haber choque
# con una ruta del SPA (ver comentario en los include_router de arriba).
_frontend_dir = Path(FRONTEND_DIST_PATH)

if _frontend_dir.is_dir():

    @app.get("/{ruta_spa:path}", include_in_schema=False)
    def servir_frontend(ruta_spa: str) -> FileResponse:
        """Sirve el frontend compilado: un archivo estático real si la
        ruta pedida existe tal cual (JS/CSS de assets/, favicon, etc.),
        o si no, index.html -- así React Router puede resolver rutas del
        lado del cliente (ej. /admin/usuarios) también al recargar la
        página, no solo navegando desde adentro de la app."""
        candidato = (_frontend_dir / ruta_spa).resolve()
        try:
            candidato.relative_to(_frontend_dir.resolve())
        except ValueError:
            candidato = None  # intento de salirse de la carpeta del frontend

        if ruta_spa and candidato is not None and candidato.is_file():
            return FileResponse(candidato)
        return FileResponse(_frontend_dir / "index.html")

else:
    logging.getLogger(__name__).warning(
        "FRONTEND_DIST_PATH (%s) no existe -- no se está sirviendo ningún "
        "frontend compilado (normal en desarrollo local).",
        FRONTEND_DIST_PATH,
    )

"""Mantenimiento de la homologación de nombres comerciales (Plaguicidas y Nutrientes).

Misma mecánica que la homologación de empresas (routers/admin_empresas.py): cada operación que escribe guarda UsuarioMod/FechaMod en
el catálogo y sincroniza las filas ya cargadas en la MISMA transacción. Plaguicidas usa dbo.CatalogoNombresComerciales; Nutrientes
reutiliza dbo.CatalogoAgrupadorNutrientes. Los datos originales no se modifican nunca. Ver services/homologacion_catalogo.py."""

from collections.abc import Callable

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import UsuarioToken, get_current_user, require_acceso_importaciones, require_role
from app.schemas.nombres_comerciales import (
    AsignarNombresPayload,
    ConfirmarNombresPayload,
    ConfirmarPendientesNombresPayload,
    NuevosSinHomologarNombres,
    PaginaGruposNombres,
    RenombrarNombrePayload,
    ResultadoExcelNombres,
    ResultadoNombres,
    SepararNombrePayload,
    UnirNombresPayload,
)
from app.services import homologacion_catalogo as svc
from app.services.homologacion_empresas import ErrorHomologacion

router = APIRouter(
    prefix="/admin/nombres-comerciales/{tipo}",
    tags=["admin-nombres-comerciales"],
    dependencies=[Depends(require_role("Administrador")), Depends(require_acceso_importaciones)],
)

TAMANO_MAX_EXCEL = 10 * 1024 * 1024


def _cfg(tipo: str) -> svc.Config:
    try:
        return svc.obtener_config(tipo)
    except ErrorHomologacion as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.mensaje)


def _ejecutar(db: Session, operacion: Callable[[], dict]) -> dict:
    """Corre una operación de escritura en una transacción: commit si sale bien, rollback si no."""
    try:
        resultado = operacion()
        db.commit()
        return resultado
    except ErrorHomologacion as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.mensaje)
    except Exception:
        db.rollback()
        raise


@router.get("/grupos", response_model=PaginaGruposNombres)
def listar_grupos(
    tipo: str,
    busqueda: str | None = None,
    estado: str = Query("todas", description="todas | pendientes | confirmadas"),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    """Grupos de nombres comerciales (por nombre estándar), por CIF USD descendente, con sus variantes."""
    try:
        return svc.listar_grupos(db, _cfg(tipo), busqueda, estado, pagina, tamano_pagina)
    except ErrorHomologacion as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.mensaje)


@router.get("/nuevos-sin-homologar", response_model=NuevosSinHomologarNombres)
def nuevos_sin_homologar(
    tipo: str,
    busqueda: str | None = None,
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    """Nombres que están en los datos y todavía no tienen entrada en el catálogo."""
    return svc.nuevas_sin_homologar(db, _cfg(tipo), busqueda, pagina, tamano_pagina)


@router.post("/unir", response_model=ResultadoNombres)
def unir(tipo: str, payload: UnirNombresPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)) -> dict:
    """Une 2 o más grupos (por sus claves) bajo un nombre estándar; quedan confirmados."""
    cfg = _cfg(tipo)
    return _ejecutar(db, lambda: svc.unir(db, cfg, payload.claves, payload.nombre_oficial, usuario.usuario_id))


@router.put("/renombrar", response_model=ResultadoNombres)
def renombrar(tipo: str, payload: RenombrarNombrePayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)) -> dict:
    """Cambia el nombre estándar de un grupo; queda confirmado."""
    cfg = _cfg(tipo)
    return _ejecutar(db, lambda: svc.renombrar(db, cfg, payload.nombre_actual, payload.nombre_nuevo, usuario.usuario_id))


@router.post("/separar", response_model=ResultadoNombres)
def separar(tipo: str, payload: SepararNombrePayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)) -> dict:
    """Saca una variante (clave) de su grupo: queda sola, con su nombre original como estándar, confirmada."""
    cfg = _cfg(tipo)
    return _ejecutar(db, lambda: svc.separar(db, cfg, payload.clave, usuario.usuario_id))


@router.post("/confirmar", response_model=ResultadoNombres)
def confirmar(tipo: str, payload: ConfirmarNombresPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)) -> dict:
    """Confirma uno o varios grupos (por nombre estándar)."""
    cfg = _cfg(tipo)
    return _ejecutar(db, lambda: svc.confirmar(db, cfg, payload.nombres, usuario.usuario_id))


@router.post("/confirmar-pendientes", response_model=ResultadoNombres)
def confirmar_pendientes(
    tipo: str, payload: ConfirmarPendientesNombresPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)
) -> dict:
    """Confirma todos los grupos pendientes que cumplen la búsqueda actual."""
    cfg = _cfg(tipo)
    return _ejecutar(db, lambda: svc.confirmar_pendientes(db, cfg, payload.busqueda, usuario.usuario_id))


@router.post("/nuevos-sin-homologar/asignar", response_model=ResultadoNombres)
def asignar_nuevos(tipo: str, payload: AsignarNombresPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)) -> dict:
    """Asigna nombres nuevos a un grupo existente o crea un grupo nuevo con ellos; quedan confirmados."""
    cfg = _cfg(tipo)
    return _ejecutar(
        db, lambda: svc.asignar_nuevas(db, cfg, payload.claves, payload.nombre_grupo, payload.grupo_nuevo, usuario.usuario_id)
    )


@router.post("/excel", response_model=ResultadoExcelNombres)
async def cargar_excel(
    tipo: str,
    archivo: UploadFile = File(..., description="Excel con dos columnas: nombre comercial y nombre estándar"),
    aplicar: bool = Query(False, description="False = solo vista previa; True = aplica en una transacción"),
    db: Session = Depends(get_db),
    usuario: UsuarioToken = Depends(get_current_user),
) -> dict:
    """Excel estándar (nombre comercial / nombre estándar): con aplicar=false devuelve la vista previa (cuántos se unirán, cuántos
    son nuevos, cuántos tienen conflicto) sin cambiar nada; con aplicar=true los aplica en una transacción."""
    cfg = _cfg(tipo)
    nombre = (archivo.filename or "").lower()
    if not nombre.endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx).")
    contenido = await archivo.read()
    if len(contenido) > TAMANO_MAX_EXCEL:
        raise HTTPException(status_code=400, detail="El archivo es demasiado grande (máximo 10 MB).")
    return _ejecutar(db, lambda: svc.procesar_excel(db, cfg, contenido, aplicar, usuario.usuario_id))

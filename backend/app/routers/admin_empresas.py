"""Mantenimiento de la homologación de empresas (Plaguicidas y Nutrientes).

Cada operación que escribe guarda UsuarioMod/FechaMod en dbo.CatalogoEmpresas y sincroniza EmpresaHomologada en las filas ya
cargadas de dbo.Importacion y dbo.Nutrientes dentro de la MISMA transacción (si algo falla se deshace todo). Los datos
originales (importador, EmpresaImportadora) no se modifican nunca. Ver services/homologacion_empresas.py."""

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import UsuarioToken, get_current_user, require_acceso_importaciones, require_role
from app.schemas.empresas import (
    AsignarNuevasPayload,
    ConfirmarPayload,
    ConfirmarPendientesPayload,
    NuevasSinHomologarResponse,
    PaginaGruposEmpresas,
    RenombrarPayload,
    ResultadoHomologacion,
    SepararPayload,
    UnirPayload,
)
from app.services import homologacion_empresas as svc

router = APIRouter(
    prefix="/admin/empresas",
    tags=["admin-empresas"],
    dependencies=[Depends(require_role("Administrador")), Depends(require_acceso_importaciones)],
)


def _ejecutar(db: Session, operacion: Callable[[], dict]) -> dict:
    """Corre una operación de escritura en una transacción: commit si sale bien, rollback si no."""
    try:
        resultado = operacion()
        db.commit()
        return resultado
    except svc.ErrorHomologacion as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.mensaje)
    except Exception:
        db.rollback()
        raise


@router.get("/grupos", response_model=PaginaGruposEmpresas)
def listar_grupos(
    busqueda: str | None = None,
    estado: str = Query("todas", description="todas | pendientes | confirmadas"),
    origen: str = Query("todas", description="todas | P | N | ambas"),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    """Grupos de empresas (por nombre homologado), ordenados por CIF USD total descendente, con sus variantes."""
    try:
        return svc.listar_grupos(db, busqueda, estado, origen, pagina, tamano_pagina)
    except svc.ErrorHomologacion as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.mensaje)


@router.get("/nuevas-sin-homologar", response_model=NuevasSinHomologarResponse)
def nuevas_sin_homologar(db: Session = Depends(get_db)) -> dict:
    """Empresas que llegaron en cargas y todavía no están en el catálogo (dbo.log_ExcepcionesEmpresas)."""
    return svc.nuevas_sin_homologar(db)


@router.post("/unir", response_model=ResultadoHomologacion)
def unir(payload: UnirPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)) -> dict:
    """Une 2 o más grupos (por sus claves) bajo un nombre oficial; quedan confirmados."""
    return _ejecutar(db, lambda: svc.unir(db, payload.claves, payload.nombre_oficial, usuario.usuario_id))


@router.put("/renombrar", response_model=ResultadoHomologacion)
def renombrar(
    payload: RenombrarPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)
) -> dict:
    """Cambia el nombre oficial de un grupo; queda confirmado."""
    return _ejecutar(db, lambda: svc.renombrar(db, payload.nombre_actual, payload.nombre_nuevo, usuario.usuario_id))


@router.post("/separar", response_model=ResultadoHomologacion)
def separar(
    payload: SepararPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)
) -> dict:
    """Saca una variante (clave) de su grupo: queda sola, con su nombre original como homologado, confirmada."""
    return _ejecutar(db, lambda: svc.separar(db, payload.clave, usuario.usuario_id))


@router.post("/confirmar", response_model=ResultadoHomologacion)
def confirmar(
    payload: ConfirmarPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)
) -> dict:
    """Confirma uno o varios grupos (por nombre homologado)."""
    return _ejecutar(db, lambda: svc.confirmar(db, payload.nombres, usuario.usuario_id))


@router.post("/confirmar-pendientes", response_model=ResultadoHomologacion)
def confirmar_pendientes(
    payload: ConfirmarPendientesPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)
) -> dict:
    """Confirma todos los grupos pendientes que cumplen el filtro actual (búsqueda + origen)."""
    return _ejecutar(db, lambda: svc.confirmar_pendientes(db, payload.busqueda, payload.origen, usuario.usuario_id))


@router.post("/nuevas-sin-homologar/asignar", response_model=ResultadoHomologacion)
def asignar_nuevas(
    payload: AsignarNuevasPayload, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)
) -> dict:
    """Asigna empresas nuevas a un grupo existente o crea un grupo nuevo con ellas; quedan confirmadas."""
    return _ejecutar(
        db, lambda: svc.asignar_nuevas(db, payload.claves, payload.nombre_grupo, payload.grupo_nuevo, usuario.usuario_id)
    )

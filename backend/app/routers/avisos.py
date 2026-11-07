"""Avisos (campanita): lista de avisos del usuario y marcado de LEÍDO por usuario.

Solo exige sesión: cada usuario ve los avisos que le corresponden por su rol ('Todos' para todos; 'Administrador' solo para el rol
Administrador) y marca LEÍDO por su cuenta (dbo.AvisosLeidos); marcar uno no lo marca para los demás. Ver services/avisos.py."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import UsuarioToken, get_current_user
from app.services import avisos as svc

router = APIRouter(prefix="/avisos", tags=["avisos"])


class AvisoOut(BaseModel):
    aviso_id: int
    tipo: str
    mensaje: str
    referencia: str | None = None
    fecha_creacion: datetime
    destino: str
    leido: bool


class ListaAvisos(BaseModel):
    no_leidos: int
    avisos: list[AvisoOut]


class ResultadoLeer(BaseModel):
    marcados: int
    no_leidos: int


@router.get("", response_model=ListaAvisos)
def listar(
    incluir_leidos: bool = Query(False, description="True = incluye también los ya leídos por este usuario"),
    db: Session = Depends(get_db),
    usuario: UsuarioToken = Depends(get_current_user),
) -> dict:
    """Avisos que le corresponden al usuario según su rol, los más recientes primero, con el conteo de no leídos."""
    return svc.listar_avisos(db, usuario.usuario_id, usuario.rol, incluir_leidos)


@router.post("/leer-todos", response_model=ResultadoLeer)
def leer_todos(db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)) -> dict:
    """Marca como leídos (solo para este usuario) todos sus avisos pendientes."""
    marcados = svc.marcar_todos_leidos(db, usuario.usuario_id, usuario.rol)
    db.commit()
    return {"marcados": marcados, "no_leidos": svc.listar_avisos(db, usuario.usuario_id, usuario.rol, limite=1)["no_leidos"]}


@router.post("/{aviso_id}/leido", response_model=ResultadoLeer)
def leido(aviso_id: int, db: Session = Depends(get_db), usuario: UsuarioToken = Depends(get_current_user)) -> dict:
    """Marca un aviso como leído por este usuario. 404 si no existe o no le corresponde."""
    if not svc.marcar_leido(db, usuario.usuario_id, usuario.rol, aviso_id):
        db.rollback()
        raise HTTPException(status_code=404, detail="El aviso no existe.")
    db.commit()
    return {"marcados": 1, "no_leidos": svc.listar_avisos(db, usuario.usuario_id, usuario.rol, limite=1)["no_leidos"]}

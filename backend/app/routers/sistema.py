from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import UsuarioToken, get_current_user
from app.models.sync import SyncEstado

router = APIRouter(prefix="/sistema", tags=["sistema"])


class UltimaActualizacionResponse(BaseModel):
    # Hora de Guatemala (sin zona). None = todavía no hay ninguna sincronización registrada.
    ultima_actualizacion: datetime | None


@router.get("/ultima-actualizacion", response_model=UltimaActualizacionResponse)
def ultima_actualizacion(
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(get_current_user),
) -> UltimaActualizacionResponse:
    """Fecha y hora de la última sincronización EXITOSA de Financiero (dbo.SyncEstado). Si la tabla
    está vacía (o todavía no existe) devuelve None: la portada simplemente no muestra el recuadro."""
    try:
        fecha = db.query(SyncEstado.UltimaEjecucionOk).filter(SyncEstado.Proceso == "Financiero").scalar()
    except SQLAlchemyError:
        db.rollback()
        fecha = None
    return UltimaActualizacionResponse(ultima_actualizacion=fecha)

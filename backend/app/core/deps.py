from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.usuario import Usuario

bearer_scheme = HTTPBearer()


@dataclass
class UsuarioToken:
    usuario_id: int
    nombre_usuario: str
    rol: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UsuarioToken:
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    return UsuarioToken(
        usuario_id=int(payload["sub"]),
        nombre_usuario=payload["username"],
        rol=payload["rol"],
    )


def require_role(*roles_permitidos: str):
    def dependency(
        usuario: UsuarioToken = Depends(get_current_user),
    ) -> UsuarioToken:
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta acción",
            )
        return usuario

    return dependency


def require_export_permission(
    usuario: UsuarioToken = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsuarioToken:
    """A diferencia de require_role (que solo mira el rol embebido en el
    JWT), esto consulta dbo.Usuarios.PuedeExportar en cada request: es un
    permiso individual por usuario (no por rol), así que si un
    administrador se lo quita/da a alguien puntualmente, aplica de
    inmediato sin esperar a que el usuario vuelva a loguearse."""
    puede_exportar = (
        db.query(Usuario.PuedeExportar).filter(Usuario.UsuarioId == usuario.usuario_id).scalar()
    )
    if not puede_exportar:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para exportar.",
        )
    return usuario


def _verificar_acceso_modulo(db: Session, usuario: UsuarioToken, columna, nombre_modulo: str) -> None:
    """Compartido por require_acceso_importaciones/financiero/indicadores
    -- mismo criterio que require_export_permission: permiso individual
    por usuario, consultado fresco en cada request (no embebido de forma
    estática), así que un cambio de acceso aplica de inmediato sin
    esperar a que el usuario vuelva a loguearse."""
    tiene_acceso = db.query(columna).filter(Usuario.UsuarioId == usuario.usuario_id).scalar()
    if not tiene_acceso:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tiene acceso al módulo {nombre_modulo}.",
        )


def require_acceso_importaciones(
    usuario: UsuarioToken = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsuarioToken:
    _verificar_acceso_modulo(db, usuario, Usuario.AccesoImportaciones, "Importaciones")
    return usuario


def require_acceso_financiero(
    usuario: UsuarioToken = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsuarioToken:
    _verificar_acceso_modulo(db, usuario, Usuario.AccesoFinanciero, "Financiero")
    return usuario


def require_acceso_indicadores(
    usuario: UsuarioToken = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsuarioToken:
    """Todavía sin endpoints propios (Indicadores no tiene pantallas) --
    lista para usarse en cuanto ese proyecto arranque."""
    _verificar_acceso_modulo(db, usuario, Usuario.AccesoIndicadores, "Indicadores")
    return usuario

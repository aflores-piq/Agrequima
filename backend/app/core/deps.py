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

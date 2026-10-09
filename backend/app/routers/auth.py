from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.db import get_db
from app.core.deps import UsuarioToken, get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.usuario import AvisoLegalAceptacion, Rol, Usuario
from app.schemas.auth import (
    ActualizarPreferenciasRequest,
    AvisoLegalResponse,
    CambiarMiPasswordRequest,
    LoginRequest,
    PreferenciasResponse,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Guatemala está en UTC-6 todo el año (no usa horario de verano).
ZONA_GUATEMALA = timezone(timedelta(hours=-6))


def ahora_guatemala() -> datetime:
    """Fecha y hora actual de Guatemala (sin zona, para guardar como DATETIME2), tomada del
    reloj del servidor en UTC: no depende de la zona horaria del equipo ni del navegador."""
    return datetime.now(timezone.utc).astimezone(ZONA_GUATEMALA).replace(tzinfo=None, microsecond=0)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    usuario = (
        db.query(Usuario)
        .filter(Usuario.NombreUsuario == payload.nombre_usuario)
        .first()
    )
    if (
        usuario is None
        or not usuario.Activo
        or not verify_password(payload.password, usuario.PasswordHash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    rol = db.query(Rol).filter(Rol.RolId == usuario.RolId).first()

    usuario.UltimoLogin = func.getdate()
    db.commit()

    token = create_access_token(
        sub=str(usuario.UsuarioId),
        username=usuario.NombreUsuario,
        rol=rol.NombreRol,
        puede_exportar=usuario.PuedeExportar,
        nombre_completo=usuario.NombreCompleto,
        email=usuario.Email,
        acceso_importaciones=usuario.AccesoImportaciones,
        acceso_financiero=usuario.AccesoFinanciero,
        acceso_indicadores=usuario.AccesoIndicadores,
    )
    return TokenResponse(
        access_token=token,
        rol=rol.NombreRol,
        puede_exportar=usuario.PuedeExportar,
        tema=usuario.Tema,
        acceso_importaciones=usuario.AccesoImportaciones,
        acceso_financiero=usuario.AccesoFinanciero,
        acceso_indicadores=usuario.AccesoIndicadores,
        # El aviso legal se pide en CADA inicio de sesión: siempre False acá (el frontend lo muestra
        # y, al aceptar, POST /auth/aviso-legal deja un registro nuevo). La primera aceptación sigue
        # en dbo.Usuarios; el historial completo está en dbo.AvisoLegalAceptaciones.
        aviso_legal_aceptado=False,
    )


@router.patch("/preferencias", response_model=PreferenciasResponse)
def actualizar_preferencias(
    payload: ActualizarPreferenciasRequest,
    db: Session = Depends(get_db),
    usuario_token: UsuarioToken = Depends(get_current_user),
) -> PreferenciasResponse:
    """Tema se guarda por usuario (no solo en el navegador) para que se
    aplique de inmediato al iniciar sesión desde cualquier equipo — ver
    menú de cuenta del encabezado."""
    usuario = db.query(Usuario).filter(Usuario.UsuarioId == usuario_token.usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    usuario.Tema = payload.tema
    db.commit()
    return PreferenciasResponse(tema=usuario.Tema)


@router.patch("/password", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_mi_password(
    payload: CambiarMiPasswordRequest,
    db: Session = Depends(get_db),
    usuario_token: UsuarioToken = Depends(get_current_user),
) -> None:
    """Autoservicio: cualquier usuario logueado cambia SU PROPIA
    contraseña (a diferencia de PATCH /admin/usuarios/{id}/password, que
    es para que un Administrador/Administrador de Usuarios se la cambie
    a otra cuenta) — por eso acá se exige la contraseña actual como
    confirmación, en vez de depender solo del rol."""
    usuario = db.query(Usuario).filter(Usuario.UsuarioId == usuario_token.usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if not verify_password(payload.password_actual, usuario.PasswordHash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta.",
        )
    if len(payload.password_nueva) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña nueva debe tener al menos 8 caracteres.",
        )
    usuario.PasswordHash = hash_password(payload.password_nueva)
    db.commit()


@router.post("/aviso-legal", response_model=AvisoLegalResponse)
def aceptar_aviso_legal(
    db: Session = Depends(get_db),
    usuario_token: UsuarioToken = Depends(get_current_user),
) -> AvisoLegalResponse:
    """Registra una aceptación del aviso legal del usuario autenticado. Se llama en CADA inicio
    de sesión: cada llamada agrega una fila a dbo.AvisoLegalAceptaciones con el usuario y la
    fecha/hora de Guatemala (la calcula el servidor, nunca el navegador, para que sirva de
    respaldo confiable ante un reclamo). La primera aceptación además queda en
    dbo.Usuarios (AvisoLegalAceptado / AvisoLegalFechaAceptacion), sin pisar esa fecha."""
    usuario = db.query(Usuario).filter(Usuario.UsuarioId == usuario_token.usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    ahora = ahora_guatemala()
    db.add(
        AvisoLegalAceptacion(
            UsuarioId=usuario.UsuarioId,
            NombreUsuario=usuario.NombreUsuario,
            FechaHoraGuatemala=ahora,
        )
    )
    if not usuario.AvisoLegalAceptado:
        usuario.AvisoLegalAceptado = True
        usuario.AvisoLegalFechaAceptacion = func.getdate()
    db.commit()
    return AvisoLegalResponse(aceptado=True, fecha_aceptacion=ahora)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import UsuarioToken, require_role
from app.core.security import hash_password
from app.models.usuario import Rol, Usuario
from app.schemas.usuarios import UsuarioCreate, UsuarioOut, UsuarioUpdate

router = APIRouter(
    prefix="/admin/usuarios",
    tags=["admin-usuarios"],
    dependencies=[Depends(require_role("Administrador"))],
)


def _a_usuario_out(usuario: Usuario, rol_nombre: str) -> UsuarioOut:
    return UsuarioOut(
        usuario_id=usuario.UsuarioId,
        nombre_usuario=usuario.NombreUsuario,
        nombre_completo=usuario.NombreCompleto,
        email=usuario.Email,
        rol=rol_nombre,
        activo=usuario.Activo,
        puede_exportar=usuario.PuedeExportar,
        fecha_creacion=usuario.FechaCreacion,
        ultimo_login=usuario.UltimoLogin,
    )


def _buscar_rol(db: Session, nombre_rol: str) -> Rol:
    rol = db.query(Rol).filter(Rol.NombreRol == nombre_rol).first()
    if rol is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rol '{nombre_rol}' no existe.",
        )
    return rol


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)) -> list[UsuarioOut]:
    filas = db.query(Usuario, Rol.NombreRol).join(Rol, Usuario.RolId == Rol.RolId).order_by(Usuario.NombreUsuario).all()
    return [_a_usuario_out(usuario, rol_nombre) for usuario, rol_nombre in filas]


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(payload: UsuarioCreate, db: Session = Depends(get_db)) -> UsuarioOut:
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres.",
        )
    if db.query(Usuario).filter(Usuario.NombreUsuario == payload.nombre_usuario).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un usuario '{payload.nombre_usuario}'.",
        )

    rol = _buscar_rol(db, payload.rol)

    usuario = Usuario(
        NombreUsuario=payload.nombre_usuario,
        NombreCompleto=payload.nombre_completo,
        Email=payload.email,
        PasswordHash=hash_password(payload.password),
        RolId=rol.RolId,
        Activo=True,
        PuedeExportar=payload.puede_exportar,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return _a_usuario_out(usuario, rol.NombreRol)


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario_actual: UsuarioToken = Depends(require_role("Administrador")),
) -> UsuarioOut:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    if usuario_id == usuario_actual.usuario_id and payload.activo is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta.",
        )

    if payload.rol is not None:
        rol = _buscar_rol(db, payload.rol)
        usuario.RolId = rol.RolId
    if payload.activo is not None:
        usuario.Activo = payload.activo
    if payload.puede_exportar is not None:
        usuario.PuedeExportar = payload.puede_exportar

    db.commit()
    db.refresh(usuario)

    rol_nombre = db.query(Rol.NombreRol).filter(Rol.RolId == usuario.RolId).scalar()
    return _a_usuario_out(usuario, rol_nombre)

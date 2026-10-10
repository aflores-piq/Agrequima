from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import UsuarioToken, require_role
from app.models.usuario import AvisoLegalAceptacion, Rol, Usuario
from app.schemas.bitacora import BitacoraIngresosResponse, FilaBitacoraIngreso

# Roles que ven la bitácora: los mismos que ven "Administrador de usuarios" (más el administrador general).
# El "Administrador de Usuarios" ve los ingresos de todos MENOS los de cuentas con rol Administrador
# (sí los de otros Administradores de Usuarios y los suyos). Es una regla propia de la bitácora: la
# lista de Usuarios sigue con la suya.
ROLES_OCULTOS_PARA_ADMIN_USUARIOS = {"Administrador"}

router = APIRouter(
    prefix="/admin/bitacora-ingresos",
    tags=["admin-bitacora"],
    dependencies=[Depends(require_role("Administrador", "Administrador de Usuarios"))],
)


@router.get("", response_model=BitacoraIngresosResponse)
def bitacora_ingresos(
    usuario_actual: UsuarioToken = Depends(require_role("Administrador", "Administrador de Usuarios")),
    empresa: str | None = Query(None),
    usuario: str | None = Query(None),
    db: Session = Depends(get_db),
) -> BitacoraIngresosResponse:
    """Cada inicio de sesión (cada aceptación del aviso legal, dbo.AvisoLegalAceptaciones), el más
    reciente primero, con el nombre y la empresa que el usuario tiene hoy en dbo.Usuarios."""
    base = db.query(AvisoLegalAceptacion).join(Usuario, Usuario.UsuarioId == AvisoLegalAceptacion.UsuarioId)
    # El Administrador ve todo. El "Administrador de Usuarios" no ve las cuentas con rol Administrador.
    # Aplica a la tabla, al conteo y a las opciones de los filtros (todos salen de esta consulta base).
    if usuario_actual.rol == "Administrador de Usuarios":
        base = base.join(Rol, Rol.RolId == Usuario.RolId).filter(
            Rol.NombreRol.notin_(ROLES_OCULTOS_PARA_ADMIN_USUARIOS)
        )

    filtrada = base
    if empresa:
        filtrada = filtrada.filter(Usuario.Empresa == empresa)
    if usuario:
        filtrada = filtrada.filter(Usuario.NombreUsuario == usuario)

    filas = (
        filtrada.with_entities(
            Usuario.NombreUsuario,
            Usuario.NombreCompleto,
            Usuario.Empresa,
            AvisoLegalAceptacion.FechaHoraGuatemala,
        )
        .order_by(AvisoLegalAceptacion.FechaHoraGuatemala.desc(), AvisoLegalAceptacion.AceptacionId.desc())
        .all()
    )

    # Opciones de los filtros: todo lo que aparece en la bitácora (no cambian al filtrar).
    empresas = [
        e
        for (e,) in base.with_entities(Usuario.Empresa).filter(Usuario.Empresa.isnot(None)).distinct().order_by(Usuario.Empresa)
        if e
    ]
    usuarios = [u for (u,) in base.with_entities(Usuario.NombreUsuario).distinct().order_by(Usuario.NombreUsuario)]

    return BitacoraIngresosResponse(
        total=len(filas),
        filas=[
            FilaBitacoraIngreso(usuario=u, nombre=n, empresa=e, fecha_hora=f) for u, n, e, f in filas
        ],
        empresas=empresas,
        usuarios=usuarios,
    )

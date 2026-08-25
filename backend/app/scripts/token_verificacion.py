"""Genera un JWT de administrador válido para pruebas automatizadas
(Playwright) que necesitan una sesión ya autenticada sin pasar por la
pantalla de login.

Uso: python -m app.scripts.token_verificacion
"""

from app.core.db import SessionLocal
from app.core.security import create_access_token
from app.models.usuario import Rol, Usuario


def main() -> None:
    db = SessionLocal()
    try:
        fila = (
            db.query(Usuario, Rol)
            .join(Rol, Usuario.RolId == Rol.RolId)
            .filter(Rol.NombreRol == "Administrador", Usuario.Activo == True)  # noqa: E712
            .first()
        )
        if fila is None:
            raise SystemExit("No hay ningún usuario Administrador activo en la base de datos.")
        usuario, rol = fila
        print(create_access_token(
            sub=str(usuario.UsuarioId),
            username=usuario.NombreUsuario,
            rol=rol.NombreRol,
            puede_exportar=usuario.PuedeExportar,
        ))
    finally:
        db.close()


if __name__ == "__main__":
    main()

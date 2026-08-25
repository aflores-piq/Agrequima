"""Crea el primer usuario administrador en dbo.Usuarios.

Pide usuario y contraseña por consola y guarda la contraseña ya hasheada
con bcrypt (nunca en texto plano). Ejecutar una sola vez, al preparar un
ambiente nuevo, después de aplicar db/agrequima_schema_sql_server.sql.

Uso:
    python -m app.scripts.seed_admin
"""

import getpass
import sys

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.usuario import Rol, Usuario


def _leer_contrasena(prompt: str) -> str:
    try:
        return getpass.getpass(prompt)
    except Exception:
        # getpass puede fallar si no hay una consola real disponible
        # (por ejemplo, al ejecutar el script con stdin redirigido).
        return input(prompt)


def main() -> None:
    db = SessionLocal()
    try:
        rol_admin = db.query(Rol).filter(Rol.NombreRol == "Administrador").first()
        if rol_admin is None:
            print("ERROR: no existe el rol 'Administrador' en dbo.Roles. "
                  "Ejecuta primero db/agrequima_schema_sql_server.sql.")
            sys.exit(1)

        print("=== Crear usuario administrador inicial ===")
        nombre_usuario = input("Nombre de usuario: ").strip()
        if not nombre_usuario:
            print("ERROR: el nombre de usuario no puede estar vacío.")
            sys.exit(1)

        existente = db.query(Usuario).filter(Usuario.NombreUsuario == nombre_usuario).first()
        if existente:
            print(f"ERROR: ya existe un usuario '{nombre_usuario}'.")
            sys.exit(1)

        nombre_completo = input("Nombre completo (opcional): ").strip() or None
        email = input("Email (opcional): ").strip() or None

        password = _leer_contrasena("Contraseña: ")
        password_confirm = _leer_contrasena("Confirmar contraseña: ")
        if password != password_confirm:
            print("ERROR: las contraseñas no coinciden.")
            sys.exit(1)
        if len(password) < 8:
            print("ERROR: la contraseña debe tener al menos 8 caracteres.")
            sys.exit(1)

        usuario = Usuario(
            NombreUsuario=nombre_usuario,
            NombreCompleto=nombre_completo,
            Email=email,
            PasswordHash=hash_password(password),
            RolId=rol_admin.RolId,
            Activo=True,
        )
        db.add(usuario)
        db.commit()
        print(f"Usuario administrador '{nombre_usuario}' creado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

"""Genera el hash de contraseña EXACTO que usa el backend real -- mismo
bcrypt, mismos parámetros que app/core/security.py:hash_password() (ver
ese archivo: bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())).

Esto existe para que la contraseña real de producción nunca se escriba
en texto plano en ningún archivo (ni en el .sql, ni acá) -- se escribe
UNA VEZ en esta consola local (no se muestra en pantalla mientras se
tipea) y lo único que sale de acá es el hash, que es lo que va pegado
en 02_seed_roles_y_admin.sql.

Uso:
    python generar_hash_password.py
"""

import getpass

import bcrypt


def _leer_contrasena(prompt: str) -> str:
    try:
        return getpass.getpass(prompt)
    except Exception:
        # getpass puede fallar si no hay una consola real disponible.
        return input(prompt)


def main() -> None:
    print("=== Generar hash de contraseña para dbo.Usuarios.PasswordHash ===")
    password = _leer_contrasena("Contraseña (no se muestra en pantalla): ")
    confirmacion = _leer_contrasena("Repetila para confirmar: ")

    if password != confirmacion:
        print("\nERROR: las contraseñas no coinciden. No se generó ningún hash.")
        return
    if len(password) < 8:
        print("\nERROR: la contraseña debe tener al menos 8 caracteres.")
        return

    hash_resultado = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    print("\nListo. Copiá esta línea completa (con las comillas) y pegala en")
    print("02_seed_roles_y_admin.sql, reemplazando el valor de @PasswordHash:\n")
    print(f"'{hash_resultado}'")


if __name__ == "__main__":
    main()

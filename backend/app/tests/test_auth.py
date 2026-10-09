from sqlalchemy import text

from app.core.db import engine
from app.tests.conftest import CONTRASENA_PRUEBA


def test_login_exitoso(client):
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_admin", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rol"] == "Administrador"
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["tema"] in ("Claro", "Oscuro")
    assert body["aviso_legal_aceptado"] in (True, False)


def test_preferencias_se_guardan_y_persisten_al_volver_a_iniciar_sesion(client, usuario_headers):
    """Tema se guarda por usuario (dbo.Usuarios), no solo en el
    navegador: cambiarlo y volver a hacer login (nuevo login = "otra
    sesión/equipo") debe devolver lo último guardado."""
    r = client.patch(
        "/api/auth/preferencias",
        headers=usuario_headers,
        json={"tema": "Oscuro"},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"tema": "Oscuro"}

    r_login = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_usuario", "password": CONTRASENA_PRUEBA}
    )
    assert r_login.status_code == 200, r_login.text
    assert r_login.json()["tema"] == "Oscuro"

    # Deja al usuario de prueba en su estado por defecto para no afectar
    # otros tests que reutilicen este mismo fixture (usuario_headers es
    # de session scope).
    r_reset = client.patch(
        "/api/auth/preferencias",
        headers=usuario_headers,
        json={"tema": "Claro"},
    )
    assert r_reset.status_code == 200, r_reset.text


def test_preferencias_rechaza_valores_invalidos(client, usuario_headers):
    r = client.patch(
        "/api/auth/preferencias",
        headers=usuario_headers,
        json={"tema": "Azul"},
    )
    assert r.status_code == 422


def test_preferencias_requiere_autenticacion(client):
    r = client.patch("/api/auth/preferencias", json={"tema": "Oscuro"})
    assert r.status_code == 401 or r.status_code == 403


def test_login_password_incorrecta(client):
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_admin", "password": "incorrecta"}
    )
    assert r.status_code == 401


def test_login_usuario_inexistente(client):
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "no_existe", "password": "loquesea"}
    )
    assert r.status_code == 401


def test_login_usuario_inactivo(client):
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_inactivo", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 401


def test_endpoint_protegido_sin_token(client):
    r = client.get("/api/dashboard/plaguicidas")
    assert r.status_code == 401


def test_cambiar_mi_password_exitoso(client, usuario_headers):
    """Autoservicio disponible para cualquier rol (acá probado con
    'Usuario' a propósito, no un rol de administración) — pide la
    contraseña actual como confirmación."""
    r = client.patch(
        "/api/auth/password",
        headers=usuario_headers,
        json={"password_actual": CONTRASENA_PRUEBA, "password_nueva": "NuevaPassword456"},
    )
    assert r.status_code == 204, r.text

    # La contraseña vieja ya no sirve, la nueva sí.
    r_login_vieja = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_usuario", "password": CONTRASENA_PRUEBA}
    )
    assert r_login_vieja.status_code == 401

    r_login_nueva = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_usuario", "password": "NuevaPassword456"}
    )
    assert r_login_nueva.status_code == 200, r_login_nueva.text

    # Se deja la contraseña como estaba, para no afectar otros tests que
    # reutilizan usuario_headers (fixture de session scope, logueado una
    # sola vez con CONTRASENA_PRUEBA).
    r_reset = client.patch(
        "/api/auth/password",
        headers=usuario_headers,
        json={"password_actual": "NuevaPassword456", "password_nueva": CONTRASENA_PRUEBA},
    )
    assert r_reset.status_code == 204, r_reset.text


def test_cambiar_mi_password_actual_incorrecta(client, usuario_headers):
    r = client.patch(
        "/api/auth/password",
        headers=usuario_headers,
        json={"password_actual": "esta_no_es", "password_nueva": "NuevaPassword456"},
    )
    assert r.status_code == 400


def test_cambiar_mi_password_nueva_muy_corta(client, usuario_headers):
    r = client.patch(
        "/api/auth/password",
        headers=usuario_headers,
        json={"password_actual": CONTRASENA_PRUEBA, "password_nueva": "corta"},
    )
    assert r.status_code == 400


def test_cambiar_mi_password_requiere_autenticacion(client):
    r = client.patch(
        "/api/auth/password",
        json={"password_actual": "x", "password_nueva": "NuevaPassword456"},
    )
    assert r.status_code == 401


def test_aviso_legal_se_pide_en_cada_login_y_cada_aceptacion_queda_registrada(client, usuario_headers):
    """El aviso legal se pide en CADA inicio de sesión: login siempre reporta
    aviso_legal_aceptado=False, aunque el usuario ya lo haya aceptado antes. Cada llamada a
    POST /auth/aviso-legal deja una fila en dbo.AvisoLegalAceptaciones (usuario y hora de
    Guatemala, calculada por el servidor); dbo.Usuarios conserva solo la PRIMERA fecha."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE dbo.Usuarios SET AvisoLegalAceptado = 0, AvisoLegalFechaAceptacion = NULL "
                "WHERE NombreUsuario = 'test_usuario'"
            )
        )
        antes = conn.execute(
            text("SELECT COUNT(*) FROM dbo.AvisoLegalAceptaciones WHERE NombreUsuario = 'test_usuario'")
        ).scalar()

    r_login = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_usuario", "password": CONTRASENA_PRUEBA}
    )
    assert r_login.status_code == 200, r_login.text
    assert r_login.json()["aviso_legal_aceptado"] is False

    r_aceptar = client.post("/api/auth/aviso-legal", headers=usuario_headers)
    assert r_aceptar.status_code == 200, r_aceptar.text
    body = r_aceptar.json()
    assert body["aceptado"] is True
    assert body["fecha_aceptacion"] is not None

    # Un segundo login, aunque ya aceptó, vuelve a pedir el aviso...
    r_login_2 = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_usuario", "password": CONTRASENA_PRUEBA}
    )
    assert r_login_2.status_code == 200, r_login_2.text
    assert r_login_2.json()["aviso_legal_aceptado"] is False

    # ...y su aceptación deja una SEGUNDA fila en el registro.
    r_aceptar_2 = client.post("/api/auth/aviso-legal", headers=usuario_headers)
    assert r_aceptar_2.status_code == 200, r_aceptar_2.text

    with engine.begin() as conn:
        filas = conn.execute(
            text(
                "SELECT NombreUsuario, FechaHoraGuatemala, FechaHoraUtc FROM dbo.AvisoLegalAceptaciones "
                "WHERE NombreUsuario = 'test_usuario' ORDER BY AceptacionId"
            )
        ).all()
        primera_fecha = conn.execute(
            text("SELECT AvisoLegalFechaAceptacion FROM dbo.Usuarios WHERE NombreUsuario = 'test_usuario'")
        ).scalar()
    assert len(filas) == antes + 2
    # Hora de Guatemala = UTC - 6 horas (con margen de unos segundos).
    ultima = filas[-1]
    diferencia = (ultima.FechaHoraUtc - ultima.FechaHoraGuatemala).total_seconds()
    assert 6 * 3600 - 5 <= diferencia <= 6 * 3600 + 5
    assert primera_fecha is not None

    # Deja al usuario de prueba en su estado por defecto para no afectar
    # otros tests que reutilicen este mismo fixture.
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE dbo.Usuarios SET AvisoLegalAceptado = 0, AvisoLegalFechaAceptacion = NULL "
                "WHERE NombreUsuario = 'test_usuario'"
            )
        )


def test_aviso_legal_requiere_autenticacion(client):
    r = client.post("/api/auth/aviso-legal")
    assert r.status_code == 401

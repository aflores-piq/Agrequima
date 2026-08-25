from app.tests.conftest import CONTRASENA_PRUEBA


def test_login_exitoso(client):
    r = client.post(
        "/auth/login", json={"nombre_usuario": "test_admin", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rol"] == "Administrador"
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["tema"] in ("Claro", "Oscuro")


def test_preferencias_se_guardan_y_persisten_al_volver_a_iniciar_sesion(client, usuario_headers):
    """Tema se guarda por usuario (dbo.Usuarios), no solo en el
    navegador: cambiarlo y volver a hacer login (nuevo login = "otra
    sesión/equipo") debe devolver lo último guardado."""
    r = client.patch(
        "/auth/preferencias",
        headers=usuario_headers,
        json={"tema": "Oscuro"},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"tema": "Oscuro"}

    r_login = client.post(
        "/auth/login", json={"nombre_usuario": "test_usuario", "password": CONTRASENA_PRUEBA}
    )
    assert r_login.status_code == 200, r_login.text
    assert r_login.json()["tema"] == "Oscuro"

    # Deja al usuario de prueba en su estado por defecto para no afectar
    # otros tests que reutilicen este mismo fixture (usuario_headers es
    # de session scope).
    r_reset = client.patch(
        "/auth/preferencias",
        headers=usuario_headers,
        json={"tema": "Claro"},
    )
    assert r_reset.status_code == 200, r_reset.text


def test_preferencias_rechaza_valores_invalidos(client, usuario_headers):
    r = client.patch(
        "/auth/preferencias",
        headers=usuario_headers,
        json={"tema": "Azul"},
    )
    assert r.status_code == 422


def test_preferencias_requiere_autenticacion(client):
    r = client.patch("/auth/preferencias", json={"tema": "Oscuro"})
    assert r.status_code == 401 or r.status_code == 403


def test_login_password_incorrecta(client):
    r = client.post(
        "/auth/login", json={"nombre_usuario": "test_admin", "password": "incorrecta"}
    )
    assert r.status_code == 401


def test_login_usuario_inexistente(client):
    r = client.post(
        "/auth/login", json={"nombre_usuario": "no_existe", "password": "loquesea"}
    )
    assert r.status_code == 401


def test_login_usuario_inactivo(client):
    r = client.post(
        "/auth/login", json={"nombre_usuario": "test_inactivo", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 401


def test_endpoint_protegido_sin_token(client):
    r = client.get("/dashboard/plaguicidas")
    assert r.status_code == 401

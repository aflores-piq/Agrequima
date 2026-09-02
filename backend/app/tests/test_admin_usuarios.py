import uuid


def _nombre_unico(prefijo: str) -> str:
    return f"{prefijo}_{uuid.uuid4().hex[:8]}"


def test_crear_usuario_con_puede_exportar(client, admin_headers):
    nombre = _nombre_unico("test_crear_exporta")
    r = client.post(
        "/api/admin/usuarios",
        headers=admin_headers,
        json={
            "nombre_usuario": nombre,
            "password": "PasswordPrueba123",
            "rol": "Usuario",
            "puede_exportar": True,
        },
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["puede_exportar"] is True
    assert cuerpo["rol"] == "Usuario"


def test_crear_usuario_sin_puede_exportar_default_false(client, admin_headers):
    nombre = _nombre_unico("test_crear_sin_exportar")
    r = client.post(
        "/api/admin/usuarios",
        headers=admin_headers,
        json={"nombre_usuario": nombre, "password": "PasswordPrueba123", "rol": "Administrador"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["puede_exportar"] is False


def test_actualizar_puede_exportar(client, admin_headers):
    nombre = _nombre_unico("test_actualizar_exporta")
    r = client.post(
        "/api/admin/usuarios",
        headers=admin_headers,
        json={"nombre_usuario": nombre, "password": "PasswordPrueba123", "rol": "Usuario"},
    )
    assert r.status_code == 201, r.text
    usuario_id = r.json()["usuario_id"]
    assert r.json()["puede_exportar"] is False

    r_patch = client.patch(
        f"/api/admin/usuarios/{usuario_id}",
        headers=admin_headers,
        json={"puede_exportar": True},
    )
    assert r_patch.status_code == 200, r_patch.text
    assert r_patch.json()["puede_exportar"] is True
    # El rol no debería haber cambiado por actualizar solo puede_exportar.
    assert r_patch.json()["rol"] == "Usuario"

    r_login = client.post(
        "/api/auth/login", json={"nombre_usuario": nombre, "password": "PasswordPrueba123"}
    )
    assert r_login.status_code == 200, r_login.text
    assert r_login.json()["puede_exportar"] is True


def test_usuario_recien_habilitado_puede_exportar_sin_relogin_previo(client, admin_headers):
    """El endpoint de exportación consulta la base en cada request: si se
    habilita el permiso después de emitido un token, ya se refleja con
    ese mismo token (no depende de volver a loguearse)."""
    nombre = _nombre_unico("test_export_en_vivo")
    r = client.post(
        "/api/admin/usuarios",
        headers=admin_headers,
        json={"nombre_usuario": nombre, "password": "PasswordPrueba123", "rol": "Usuario"},
    )
    assert r.status_code == 201, r.text
    usuario_id = r.json()["usuario_id"]

    r_login = client.post(
        "/api/auth/login", json={"nombre_usuario": nombre, "password": "PasswordPrueba123"}
    )
    assert r_login.status_code == 200, r_login.text
    headers = {"Authorization": f"Bearer {r_login.json()['access_token']}"}

    r_export_antes = client.get("/api/dashboard/plaguicidas/export/top-paises", headers=headers)
    assert r_export_antes.status_code == 403

    r_patch = client.patch(
        f"/api/admin/usuarios/{usuario_id}", headers=admin_headers, json={"puede_exportar": True}
    )
    assert r_patch.status_code == 200, r_patch.text

    r_export_despues = client.get("/api/dashboard/plaguicidas/export/top-paises", headers=headers)
    assert r_export_despues.status_code == 200

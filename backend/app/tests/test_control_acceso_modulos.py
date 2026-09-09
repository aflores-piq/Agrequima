"""Control de acceso por módulo (AccesoImportaciones/AccesoFinanciero/
AccesoIndicadores en dbo.Usuarios) -- permiso individual por usuario,
mismo criterio que PuedeExportar (ver deps.py)."""

import uuid

from app.tests.helpers import construir_excel_otro_ingreso, construir_excel_saldo_bancario


def _nombre_unico(prefijo: str) -> str:
    return f"{prefijo}_{uuid.uuid4().hex[:8]}"


def test_login_incluye_los_tres_campos_de_acceso(client):
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_admin", "password": "PasswordPrueba123"}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["acceso_importaciones"] is True
    assert data["acceso_financiero"] is True
    assert data["acceso_indicadores"] is False


def test_saldos_bancarios_requiere_acceso_financiero(client, admin_sin_financiero_headers):
    contenido = construir_excel_saldo_bancario([
        {"Concepto": "Saldo inicial", "Año": 2092, "Mes": 1, "Banco": "BI", "Valor": 1.0},
    ])
    r = client.post(
        "/api/admin/cargas/saldos-bancarios",
        headers=admin_sin_financiero_headers,
        files={"archivo": ("test.xlsx", contenido)},
    )
    assert r.status_code == 403


def test_otros_ingresos_requiere_acceso_financiero(client, admin_sin_financiero_headers):
    contenido = construir_excel_otro_ingreso([
        {"Tipo": "Presupuesto", "Concepto": "X", "Anio": 2092, "Mes": 1, "Valor": 1.0},
    ])
    r = client.post(
        "/api/admin/cargas/otros-ingresos",
        headers=admin_sin_financiero_headers,
        files={"archivo": ("test.xlsx", contenido)},
    )
    assert r.status_code == 403


def test_dashboard_plaguicidas_requiere_acceso_importaciones(client, usuario_sin_importaciones_headers):
    r = client.get("/api/dashboard/plaguicidas", headers=usuario_sin_importaciones_headers)
    assert r.status_code == 403


def test_dashboard_nutrientes_requiere_acceso_importaciones(client, usuario_sin_importaciones_headers):
    r = client.get("/api/dashboard/nutrientes", headers=usuario_sin_importaciones_headers)
    assert r.status_code == 403


def test_nomenclatura_plaguicidas_requiere_acceso_importaciones(client, admin_headers):
    # test_admin sí tiene AccesoImportaciones=1 -- confirma que NO se
    # rompió el acceso normal al agregar el segundo dependency check.
    r = client.get("/api/admin/nomenclatura/plaguicidas", headers=admin_headers)
    assert r.status_code == 200, r.text


def test_crear_usuario_con_acceso_financiero(client, admin_headers):
    r = client.post(
        "/api/admin/usuarios",
        headers=admin_headers,
        json={
            "nombre_usuario": _nombre_unico("test_nuevo_con_financiero"),
            "password": "PasswordPrueba123",
            "rol": "Usuario",
            "acceso_financiero": True,
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["acceso_importaciones"] is True  # default
    assert data["acceso_financiero"] is True
    assert data["acceso_indicadores"] is False  # default


def test_actualizar_usuario_acceso_financiero(client, admin_headers):
    r_crear = client.post(
        "/api/admin/usuarios",
        headers=admin_headers,
        json={
            "nombre_usuario": _nombre_unico("test_toggle_financiero"),
            "password": "PasswordPrueba123",
            "rol": "Usuario",
        },
    )
    assert r_crear.status_code == 201, r_crear.text
    usuario_id = r_crear.json()["usuario_id"]
    assert r_crear.json()["acceso_financiero"] is False

    r_update = client.patch(
        f"/api/admin/usuarios/{usuario_id}",
        headers=admin_headers,
        json={"acceso_financiero": True},
    )
    assert r_update.status_code == 200, r_update.text
    assert r_update.json()["acceso_financiero"] is True

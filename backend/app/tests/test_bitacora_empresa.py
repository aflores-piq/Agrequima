"""Campo Empresa en usuarios (script 23) y bitácora de ingresos
(GET /admin/bitacora-ingresos, lee dbo.AvisoLegalAceptaciones)."""

import uuid

from app.tests.conftest import CONTRASENA_PRUEBA


def _nombre_unico(prefijo: str) -> str:
    return f"{prefijo}_{uuid.uuid4().hex[:8]}"


def _crear(client, headers, nombre, empresa=None):
    cuerpo = {"nombre_usuario": nombre, "password": CONTRASENA_PRUEBA, "rol": "Usuario", "nombre_completo": "Persona " + nombre}
    if empresa is not None:
        cuerpo["empresa"] = empresa
    r = client.post("/api/admin/usuarios", headers=headers, json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _ingresar(client, nombre):
    """Inicia sesión y acepta el aviso legal (así queda un registro en la bitácora)."""
    r = client.post("/api/auth/login", json={"nombre_usuario": nombre, "password": CONTRASENA_PRUEBA})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.post("/api/auth/aviso-legal", headers=h).status_code == 200


def test_empresa_se_guarda_al_crear_y_al_editar(client, admin_headers):
    nombre = _nombre_unico("test_empresa")
    creado = _crear(client, admin_headers, nombre, empresa="  Empresa Uno  ")
    assert creado["empresa"] == "Empresa Uno"  # sin espacios sobrantes

    r = client.patch(f"/api/admin/usuarios/{creado['usuario_id']}", headers=admin_headers, json={"empresa": "Empresa Dos"})
    assert r.status_code == 200, r.text
    assert r.json()["empresa"] == "Empresa Dos"

    # Editar otra cosa no toca la empresa; vacío la deja sin valor.
    r = client.patch(f"/api/admin/usuarios/{creado['usuario_id']}", headers=admin_headers, json={"puede_exportar": True})
    assert r.json()["empresa"] == "Empresa Dos"
    r = client.patch(f"/api/admin/usuarios/{creado['usuario_id']}", headers=admin_headers, json={"empresa": "   "})
    assert r.json()["empresa"] is None

    lista = client.get("/api/admin/usuarios", headers=admin_headers).json()
    assert next(u for u in lista if u["nombre_usuario"] == nombre)["empresa"] is None


def test_usuario_sin_empresa_por_defecto(client, admin_headers):
    assert _crear(client, admin_headers, _nombre_unico("test_sin_empresa"))["empresa"] is None


def test_bitacora_lista_ingresos_con_empresa_y_filtros(client, admin_headers):
    empresa = _nombre_unico("Empresa Bitacora")
    a = _nombre_unico("test_bit_a")
    b = _nombre_unico("test_bit_b")
    _crear(client, admin_headers, a, empresa=empresa)
    _crear(client, admin_headers, b, empresa=empresa)
    _ingresar(client, a)
    _ingresar(client, a)
    _ingresar(client, b)

    r = client.get("/api/admin/bitacora-ingresos", headers=admin_headers, params={"empresa": empresa})
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["total"] == 3 and len(datos["filas"]) == 3
    assert {f["usuario"] for f in datos["filas"]} == {a, b}
    assert all(f["empresa"] == empresa and f["nombre"] == "Persona " + f["usuario"] for f in datos["filas"])
    # Más reciente primero: el último ingreso fue el de b.
    assert datos["filas"][0]["usuario"] == b
    fechas = [f["fecha_hora"] for f in datos["filas"]]
    assert fechas == sorted(fechas, reverse=True)
    # Las opciones de los filtros salen de la bitácora completa.
    assert empresa in datos["empresas"] and a in datos["usuarios"] and b in datos["usuarios"]

    solo_a = client.get("/api/admin/bitacora-ingresos", headers=admin_headers, params={"empresa": empresa, "usuario": a}).json()
    assert solo_a["total"] == 2 and {f["usuario"] for f in solo_a["filas"]} == {a}

    # Sin ningún filtro hay al menos esos ingresos.
    assert client.get("/api/admin/bitacora-ingresos", headers=admin_headers).json()["total"] >= 3


def test_bitacora_solo_para_administradores(client, admin_usuarios_headers, usuario_headers):
    assert client.get("/api/admin/bitacora-ingresos", headers=admin_usuarios_headers).status_code == 200
    assert client.get("/api/admin/bitacora-ingresos", headers=usuario_headers).status_code == 403
    assert client.get("/api/admin/bitacora-ingresos").status_code in (401, 403)


def test_bitacora_admin_de_usuarios_ve_todo_menos_ingresos_de_administradores(client, admin_headers, admin_usuarios_headers):
    # test_admin (rol Administrador) ingresa: lo ve el Administrador, NO el Administrador de Usuarios.
    _ingresar(client, "test_admin")
    # test_admin_usuarios (rol Administrador de Usuarios) ingresa: se ve a sí mismo.
    _ingresar(client, "test_admin_usuarios")
    como_admin = client.get("/api/admin/bitacora-ingresos", headers=admin_headers).json()
    assert "test_admin" in como_admin["usuarios"] and "test_admin_usuarios" in como_admin["usuarios"]

    como_admin_usuarios = client.get("/api/admin/bitacora-ingresos", headers=admin_usuarios_headers).json()
    assert "test_admin" not in como_admin_usuarios["usuarios"]
    assert "test_admin" not in {f["usuario"] for f in como_admin_usuarios["filas"]}
    assert "test_admin_usuarios" in como_admin_usuarios["usuarios"]  # sus propios ingresos
    assert como_admin_usuarios["total"] == len(como_admin_usuarios["filas"]) < como_admin["total"]
    # Filtrar por la cuenta Administrador tampoco la deja ver; filtrar por la suya sí.
    oculto = client.get("/api/admin/bitacora-ingresos", headers=admin_usuarios_headers, params={"usuario": "test_admin"}).json()
    assert oculto["total"] == 0
    propio = client.get("/api/admin/bitacora-ingresos", headers=admin_usuarios_headers, params={"usuario": "test_admin_usuarios"}).json()
    assert propio["total"] >= 1

    # Ve a los usuarios con rol Usuario y sus empresas.
    nombre = _nombre_unico("test_bit_visible")
    _crear(client, admin_usuarios_headers, nombre, empresa="Empresa Visible")
    _ingresar(client, nombre)
    visibles = client.get("/api/admin/bitacora-ingresos", headers=admin_usuarios_headers, params={"empresa": "Empresa Visible"}).json()
    assert nombre in visibles["usuarios"] and visibles["total"] >= 1 and "Empresa Visible" in visibles["empresas"]

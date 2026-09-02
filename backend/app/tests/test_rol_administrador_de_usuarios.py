"""Rol 'Administrador de Usuarios' (personal de Agrequima): entra al panel
de administración, pero dentro de ahí SOLO puede usar /admin/usuarios —
Carga, Nomenclatura y Excepciones deben rechazarlo con 403, igual que a
un usuario con rol 'Usuario'. A diferencia de la versión anterior de
este rol, SÍ debe poder ver los dashboards de Plaguicidas y Nutrientes
(igual que cualquier usuario autenticado — esos endpoints no exigen un
rol puntual, solo sesión válida)."""

from sqlalchemy import text

from app.core.db import engine
from app.tests.helpers import construir_excel_importaciones, construir_excel_nutrientes


def test_admin_usuarios_puede_listar_usuarios(client, admin_usuarios_headers):
    r = client.get("/api/admin/usuarios", headers=admin_usuarios_headers)
    assert r.status_code == 200, r.text


def test_admin_usuarios_puede_crear_usuario(client, admin_usuarios_headers):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM dbo.Usuarios WHERE NombreUsuario = 'creado_por_admin_usuarios'")
        )
    r = client.post(
        "/api/admin/usuarios",
        headers=admin_usuarios_headers,
        json={
            "nombre_usuario": "creado_por_admin_usuarios",
            "password": "PasswordPrueba123",
            "rol": "Usuario",
        },
    )
    assert r.status_code == 201, r.text
    usuario_id = r.json()["usuario_id"]

    # También puede editar rol/estado de lo que acaba de crear.
    r2 = client.patch(
        f"/api/admin/usuarios/{usuario_id}", headers=admin_usuarios_headers, json={"activo": False}
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["activo"] is False

    # Y cambiarle la contraseña (punto 5 del pedido: debe existir esta opción).
    r3 = client.patch(
        f"/api/admin/usuarios/{usuario_id}/password",
        headers=admin_usuarios_headers,
        json={"password": "OtraPasswordNueva123"},
    )
    assert r3.status_code == 204, r3.text


def test_cambiar_password_muy_corta_falla(client, admin_headers):
    with engine.begin() as conn:
        existente = conn.execute(
            text("SELECT UsuarioId FROM dbo.Usuarios WHERE NombreUsuario = 'test_usuario'")
        ).scalar()
    r = client.patch(
        f"/api/admin/usuarios/{existente}/password", headers=admin_headers, json={"password": "corta"}
    )
    assert r.status_code == 400


def test_admin_usuarios_rechazado_en_carga_plaguicidas(client, admin_usuarios_headers):
    contenido = construir_excel_importaciones(
        [
            {
                "RECIBO": 1, "SerieSAT": "S", "RecSAT": None, "APLICACIoN": "HERBICIDA",
                "RECIBOSAT": None, "FECHA": "2091-01-01", "IMPORTADOR": "X", "PRODUCTO": "X",
                "INGREDIENTEACT": "X", "EXPORTADOR": "X", "ORIGEN": "X", "pct": "10%",
                "CANTIDAD": 1.0, "UNMEDIDA": "KG", "CIFusd": 1.0, "CIFQ": 1.0, "CAMBIO": 7.7,
                "Empresa": "X", "UMSP": 1.0,
            }
        ]
    )
    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_usuarios_headers,
        files={"archivo_importaciones": ("test.xlsx", contenido)},
    )
    assert r.status_code == 403


def test_admin_usuarios_rechazado_en_carga_nutrientes(client, admin_usuarios_headers):
    contenido = construir_excel_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "1-91", "No_Registro": "REG-1",
                "NombreComercial": "X", "EmpresaImportadora": "X",
                "FechaEmision": "15/01/2091", "UMedida": "Kilogramos", "Cantidad": 100,
                "PaisProcedencia": "X", "PaisOrigen": "X",
                "AduanadeIngreso": "X", " CIF_dolares ": 1.0,
                " CIF_Q ": 1.0, " TimbresQ ": 1.0, "Exportador": "X",
                "Concentraciones": "X", "Componentes": "X", "VENTANILLA": "MAGA",
            }
        ]
    )
    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_usuarios_headers,
        files={"archivo_nutrientes": ("test.xlsx", contenido)},
    )
    assert r.status_code == 403


def test_admin_usuarios_puede_ver_dashboards(client, admin_usuarios_headers):
    """Corrección de diseño: este rol SÍ debe ver los dashboards, igual
    que un Usuario — solo Carga/Nomenclatura/Excepciones le quedan
    vedadas."""
    r1 = client.get("/api/dashboard/plaguicidas", headers=admin_usuarios_headers)
    assert r1.status_code == 200, r1.text
    r2 = client.get("/api/dashboard/nutrientes", headers=admin_usuarios_headers)
    assert r2.status_code == 200, r2.text


def test_admin_usuarios_rechazado_en_historial_cargas(client, admin_usuarios_headers):
    r = client.get("/api/admin/cargas/historial", headers=admin_usuarios_headers)
    assert r.status_code == 403


def test_admin_usuarios_rechazado_en_nomenclatura_y_excepciones(client, admin_usuarios_headers):
    for ruta in (
        "/api/admin/nomenclatura/plaguicidas",
        "/api/admin/nomenclatura/nutrientes",
    ):
        r = client.get(ruta, headers=admin_usuarios_headers)
        assert r.status_code == 403, f"{ruta}: {r.text}"


def test_admin_usuarios_no_ve_cuentas_de_administracion_en_listado(client, admin_usuarios_headers):
    """Corrección de seguridad: un 'Administrador de Usuarios' no debe ni
    enterarse de que existen cuentas 'Administrador' o 'Administrador de
    Usuarios' -- ni siquiera verlas listadas, para que no pueda intentar
    tocarlas por otra vía (ej. adivinando el usuario_id)."""
    r = client.get("/api/admin/usuarios", headers=admin_usuarios_headers)
    assert r.status_code == 200, r.text
    roles_listados = {u["rol"] for u in r.json()}
    assert "Administrador" not in roles_listados
    assert "Administrador de Usuarios" not in roles_listados


def _id_de(client, admin_headers, nombre_usuario):
    r = client.get("/api/admin/usuarios", headers=admin_headers)
    assert r.status_code == 200, r.text
    for u in r.json():
        if u["nombre_usuario"] == nombre_usuario:
            return u["usuario_id"]
    raise AssertionError(f"No se encontró el usuario de prueba '{nombre_usuario}'")


def test_admin_usuarios_rechazado_al_cambiar_password_de_administrador(
    client, admin_headers, admin_usuarios_headers
):
    """Hueco de seguridad corregido: antes, un 'Administrador de Usuarios'
    podía resetear la contraseña de una cuenta 'Administrador' real y
    entrar con ella a Carga/Nomenclatura."""
    id_admin_real = _id_de(client, admin_headers, "test_admin_sin_exportar")
    r = client.patch(
        f"/api/admin/usuarios/{id_admin_real}/password",
        headers=admin_usuarios_headers,
        json={"password": "PasswordRobada123"},
    )
    assert r.status_code == 403, r.text


def test_admin_usuarios_rechazado_al_desactivar_administrador(client, admin_headers, admin_usuarios_headers):
    id_admin_real = _id_de(client, admin_headers, "test_admin_sin_exportar")
    r = client.patch(
        f"/api/admin/usuarios/{id_admin_real}",
        headers=admin_usuarios_headers,
        json={"activo": False},
    )
    assert r.status_code == 403, r.text


def test_admin_usuarios_rechazado_al_cambiar_rol_de_administrador(client, admin_headers, admin_usuarios_headers):
    """Incluso si el cambio pedido es 'degradarlo' a Usuario, sigue
    prohibido: no puede tocar la cuenta en absoluto, solo por tener hoy
    un rol fuera de su alcance."""
    id_admin_real = _id_de(client, admin_headers, "test_admin_sin_exportar")
    r = client.patch(
        f"/api/admin/usuarios/{id_admin_real}",
        headers=admin_usuarios_headers,
        json={"rol": "Usuario"},
    )
    assert r.status_code == 403, r.text


def test_admin_usuarios_rechazado_al_crear_cuenta_con_rol_de_administracion(client, admin_usuarios_headers):
    for rol_pedido in ("Administrador", "Administrador de Usuarios"):
        r = client.post(
            "/api/admin/usuarios",
            headers=admin_usuarios_headers,
            json={
                "nombre_usuario": f"intento_escalar_{rol_pedido.replace(' ', '_')}",
                "password": "PasswordPrueba123",
                "rol": rol_pedido,
            },
        )
        assert r.status_code == 403, f"{rol_pedido}: {r.text}"


def test_admin_usuarios_rechazado_al_promover_usuario_a_rol_de_administracion(client, admin_usuarios_headers):
    id_usuario_normal = _id_de(client, admin_usuarios_headers, "test_usuario")
    r = client.patch(
        f"/api/admin/usuarios/{id_usuario_normal}",
        headers=admin_usuarios_headers,
        json={"rol": "Administrador"},
    )
    assert r.status_code == 403, r.text


def test_administrador_sigue_con_acceso_total(client, admin_headers):
    """El rol Administrador no se toca: sigue entrando a todo."""
    for ruta in (
        "/api/admin/usuarios",
        "/api/admin/cargas/historial",
        "/api/admin/nomenclatura/plaguicidas",
        "/api/admin/nomenclatura/nutrientes",
    ):
        r = client.get(ruta, headers=admin_headers)
        assert r.status_code == 200, f"{ruta}: {r.text}"

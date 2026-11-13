"""Roles de las pantallas de homologación: el administrador del cliente ("Administrador de Usuarios") puede usar SOLO las dos pantallas de
homologación (empresas y nombres comerciales), sin abrir el resto de la administración."""

import pytest

HOMOLOGACION = [
    "/api/admin/empresas/grupos",
    "/api/admin/empresas/nuevas-sin-homologar",
    "/api/admin/nombres-comerciales/plaguicidas/grupos",
    "/api/admin/nombres-comerciales/nutrientes/grupos",
    "/api/admin/nombres-comerciales/plaguicidas/nuevos-sin-homologar",
]

# Pantallas de administración que NO se abren al Administrador de Usuarios (siguen solo para el Administrador)
NO_CORRESPONDEN = [
    ("get", "/api/admin/nomenclatura/plaguicidas"),
    ("get", "/api/admin/nomenclatura/nutrientes"),
    ("get", "/api/admin/nomenclatura/plaguicidas/sin-agrupador"),
    ("get", "/api/admin/nomenclatura/nutrientes/sin-agrupador"),
    ("put", "/api/admin/nomenclatura/plaguicidas/X"),
    ("get", "/api/admin/cargas/historial"),
]


@pytest.mark.parametrize("ruta", HOMOLOGACION)
def test_las_pantallas_de_homologacion_aceptan_a_los_dos_roles_de_administracion(client, admin_headers, admin_usuarios_headers, usuario_headers, ruta):
    assert client.get(ruta, headers=admin_headers).status_code == 200
    assert client.get(ruta, headers=admin_usuarios_headers).status_code == 200
    assert client.get(ruta, headers=usuario_headers).status_code == 403
    assert client.get(ruta).status_code == 401


def test_administrador_de_usuarios_sin_acceso_a_importaciones_sigue_con_403(client, usuario_sin_importaciones_headers):
    """Mantiene el requisito de acceso a Importaciones (require_acceso_importaciones)."""
    for ruta in HOMOLOGACION:
        assert client.get(ruta, headers=usuario_sin_importaciones_headers).status_code == 403


@pytest.mark.parametrize("metodo,ruta", NO_CORRESPONDEN)
def test_administrador_de_usuarios_no_abre_pantallas_que_no_le_corresponden(client, admin_usuarios_headers, metodo, ruta):
    llamar = getattr(client, metodo)
    kw = {"json": {"agrupador": "X", "codigo": None}} if metodo == "put" else {}
    assert llamar(ruta, headers=admin_usuarios_headers, **kw).status_code == 403


def test_administrador_de_usuarios_no_puede_cargar_archivos_de_datos(client, admin_usuarios_headers):
    assert client.post("/api/admin/cargas/plaguicidas", headers=admin_usuarios_headers,
                       files={"archivo_importaciones": ("x.xlsx", b"x", "application/octet-stream")}).status_code == 403
    assert client.post("/api/admin/cargas/nutrientes", headers=admin_usuarios_headers,
                       files={"archivo_nutrientes": ("x.csv", b"x", "text/csv")}).status_code == 403

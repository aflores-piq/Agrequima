"""Fixtures compartidas de pruebas de integración.

IMPORTANTE: las pruebas corren contra Agrequima_Test (una base de datos
separada, con el mismo esquema que Agrequima), nunca contra la base de
datos real. El override de DB_NAME debe pasar ANTES de importar cualquier
módulo de app.*, porque app.core.db arma el engine de SQLAlchemy al
importarse.
"""

import os

os.environ["DB_NAME"] = "Agrequima_Test"

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import engine
from app.main import app

CONTRASENA_PRUEBA = "PasswordPrueba123"


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def seed_usuarios_prueba():
    with engine.begin() as conn:
        rol_admin_id = conn.execute(
            text("SELECT RolId FROM dbo.Roles WHERE NombreRol = 'Administrador'")
        ).scalar()
        rol_usuario_id = conn.execute(
            text("SELECT RolId FROM dbo.Roles WHERE NombreRol = 'Usuario'")
        ).scalar()
        rol_admin_usuarios_id = conn.execute(
            text("SELECT RolId FROM dbo.Roles WHERE NombreRol = 'Administrador de Usuarios'")
        ).scalar()

        # Upsert idempotente (no DELETE): en corridas repetidas, filas de
        # AuditoriaCargas de corridas anteriores ya referencian a estos
        # usuarios por FK, así que no se pueden borrar sin arrastrar
        # también su historial de cargas de prueba.
        # PuedeExportar es un permiso individual por usuario (no por rol,
        # ver dbo.Usuarios.PuedeExportar): se incluyen a propósito una
        # combinación "cruzada" (Usuario que sí exporta, Administrador
        # que no) para que los tests de exportación no puedan colarse
        # asumiendo que el permiso viene del rol. Mismo criterio para
        # AccesoImportaciones/AccesoFinanciero (ver
        # require_acceso_importaciones/require_acceso_financiero en
        # deps.py): test_admin necesita AccesoFinanciero=1 para poder
        # probar las cargas/dashboard de Financiero; test_admin_sin_
        # financiero y test_usuario_sin_importaciones existen
        # específicamente para probar el 403 de cada uno.
        password_hash = bcrypt.hashpw(CONTRASENA_PRUEBA.encode(), bcrypt.gensalt()).decode()
        for nombre, rol_id, activo, puede_exportar, acceso_importaciones, acceso_financiero in (
            ("test_admin", rol_admin_id, 1, 1, 1, 1),
            ("test_usuario", rol_usuario_id, 1, 0, 1, 0),
            ("test_inactivo", rol_usuario_id, 0, 0, 1, 0),
            ("test_usuario_exportador", rol_usuario_id, 1, 1, 1, 0),
            ("test_admin_sin_exportar", rol_admin_id, 1, 0, 1, 0),
            ("test_admin_usuarios", rol_admin_usuarios_id, 1, 0, 1, 0),
            ("test_admin_sin_financiero", rol_admin_id, 1, 0, 1, 0),
            ("test_usuario_sin_importaciones", rol_usuario_id, 1, 0, 0, 0),
        ):
            existente = conn.execute(
                text("SELECT UsuarioId FROM dbo.Usuarios WHERE NombreUsuario = :u"), {"u": nombre}
            ).scalar()
            if existente is None:
                conn.execute(
                    text(
                        "INSERT INTO dbo.Usuarios "
                        "(NombreUsuario, PasswordHash, RolId, Activo, PuedeExportar, AccesoImportaciones, AccesoFinanciero) "
                        "VALUES (:u, :p, :r, :a, :e, :ai, :af)"
                    ),
                    {
                        "u": nombre, "p": password_hash, "r": rol_id, "a": activo, "e": puede_exportar,
                        "ai": acceso_importaciones, "af": acceso_financiero,
                    },
                )
            else:
                conn.execute(
                    text(
                        "UPDATE dbo.Usuarios SET PasswordHash = :p, RolId = :r, Activo = :a, PuedeExportar = :e, "
                        "AccesoImportaciones = :ai, AccesoFinanciero = :af "
                        "WHERE UsuarioId = :id"
                    ),
                    {
                        "p": password_hash, "r": rol_id, "a": activo, "e": puede_exportar,
                        "ai": acceso_importaciones, "af": acceso_financiero, "id": existente,
                    },
                )
    yield


@pytest.fixture(scope="session")
def admin_headers(client):
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_admin", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def usuario_headers(client):
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_usuario", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def usuario_exportador_headers(client):
    """Rol Usuario, pero con PuedeExportar=1: prueba que el permiso es
    individual por usuario, no heredado del rol."""
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_usuario_exportador", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_sin_exportar_headers(client):
    """Rol Administrador, pero con PuedeExportar=0: confirma que el rol
    por sí solo ya no otorga el permiso de exportar."""
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_admin_sin_exportar", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_usuarios_headers(client):
    """Rol 'Administrador de Usuarios' (personal de Agrequima): solo debe
    poder usar /admin/usuarios, nada de Carga/Nomenclatura."""
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_admin_usuarios", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_sin_financiero_headers(client):
    """Rol Administrador, pero con AccesoFinanciero=0: confirma que el rol
    por sí solo no basta para usar los endpoints de Financiero."""
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_admin_sin_financiero", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def usuario_sin_importaciones_headers(client):
    """Rol Usuario, pero con AccesoImportaciones=0: confirma que sin ese
    acceso no puede ver los dashboards de Plaguicidas/Nutrientes."""
    r = client.post(
        "/api/auth/login", json={"nombre_usuario": "test_usuario_sin_importaciones", "password": CONTRASENA_PRUEBA}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

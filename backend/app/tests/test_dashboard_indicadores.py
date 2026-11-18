"""Indicadores > Viáticos > «Resumen General» (/api/dashboard/indicadores/resumen-general/*).

Usa filas sintéticas en dbo.vw_piq_viaticos con años lejanos (2090 y 2091) y el proveedor marcado «TEST_IND_», que se borran
al terminar; si la tabla no existe en la base de pruebas (la crea el script 30_copias_fieles_indicadores.sql), se crea solo
para esta prueba y se elimina después."""

import bcrypt
import pytest
from sqlalchemy import text

from app.core.db import engine
from app.tests.conftest import CONTRASENA_PRUEBA

MARCA = "TEST_IND_"

# (fecha_documento, tecnico, tipo_gasto, documento, proveedor, monto)
FILAS = [
    ("2090-03-10", "Ana", "Hospedaje", 1, MARCA + "P1", 100),  # marzo 2090 completo = 140; del 1 al 6 = 40
    ("2090-03-04", "Ana", "Hospedaje", 2, MARCA + "P1", 40),
    ("2090-04-15", "Beto", "Combustible", 32, MARCA + "P2", 10),  # abril 2090 (mes comparado con abril 2091, completo)
    ("2090-05-20", "Ana", "Hospedaje", 33, MARCA + "P1", 50),  # mayo 2090: nada del día 1 al 2
    ("2091-01-15", "Ana", "Hospedaje", 11, MARCA + "P1", 10),
    ("2091-02-15", "Ana", "Combustible", 12, MARCA + "P1", 20),
    ("2091-03-05", "Ana", "Hospedaje", 21, MARCA + "P1", 100),
    ("2091-03-06", "Beto", "Combustible", 22, MARCA + "P2", 50),
    ("2091-04-30", "Ana", "Hospedaje", 31, MARCA + "P1", 30),  # abril 2091 completo (último día = 30)
    ("2091-05-02", "Ana", "Hospedaje", 34, MARCA + "P1", 5),  # mayo 2091 incompleto (último día con datos = 2)
    (None, "Ana", "Hospedaje", 99, MARCA + "P1", 7),  # sin fecha_documento: no entra en ningún mes
]


@pytest.fixture(scope="module")
def datos_viaticos():
    with engine.begin() as conn:
        existe = conn.execute(text("SELECT OBJECT_ID('dbo.vw_piq_viaticos')")).scalar()
        es_vista = bool(existe) and conn.execute(text("SELECT OBJECTPROPERTY(OBJECT_ID('dbo.vw_piq_viaticos'), 'IsView')")).scalar()
        if es_vista:
            pytest.skip("dbo.vw_piq_viaticos es una vista en esta base: la prueba no inserta filas")
        creada = not existe
        if creada:
            conn.execute(
                text(
                    """CREATE TABLE dbo.vw_piq_viaticos (
                        Tipo_gasto varchar(500) NULL, proveedor varchar(200) NULL, motivo varchar(500) NULL,
                        documento bigint NULL, monto decimal(18,2) NULL, fecha_documento date NULL,
                        nombre_completo varchar(150) NULL, fechainicial date NULL, fechafinal date NULL)"""
                )
            )
        for fecha, tecnico, tipo, documento, proveedor, monto in FILAS:
            conn.execute(
                text(
                    "INSERT INTO dbo.vw_piq_viaticos (fecha_documento, nombre_completo, Tipo_gasto, documento, proveedor, monto) "
                    "VALUES (:f, :t, :g, :d, :p, :m)"
                ),
                {"f": fecha, "t": tecnico, "g": tipo, "d": documento, "p": proveedor, "m": monto},
            )
    yield
    with engine.begin() as conn:
        if creada:
            conn.execute(text("DROP TABLE dbo.vw_piq_viaticos"))
        else:
            conn.execute(text("DELETE FROM dbo.vw_piq_viaticos WHERE proveedor LIKE :m"), {"m": MARCA + "%"})


def _usuario_con_acceso(nombre: str, rol: str, acceso_indicadores: int) -> None:
    password_hash = bcrypt.hashpw(CONTRASENA_PRUEBA.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        rol_id = conn.execute(text("SELECT RolId FROM dbo.Roles WHERE NombreRol = :r"), {"r": rol}).scalar()
        existente = conn.execute(text("SELECT UsuarioId FROM dbo.Usuarios WHERE NombreUsuario = :u"), {"u": nombre}).scalar()
        if existente is None:
            conn.execute(
                text(
                    "INSERT INTO dbo.Usuarios (NombreUsuario, PasswordHash, RolId, Activo, PuedeExportar, AccesoImportaciones, "
                    "AccesoFinanciero, AccesoIndicadores) VALUES (:u, :p, :r, 1, 0, 1, 0, :i)"
                ),
                {"u": nombre, "p": password_hash, "r": rol_id, "i": acceso_indicadores},
            )
        else:
            conn.execute(
                text("UPDATE dbo.Usuarios SET PasswordHash = :p, RolId = :r, Activo = 1, AccesoIndicadores = :i WHERE UsuarioId = :id"),
                {"p": password_hash, "r": rol_id, "i": acceso_indicadores, "id": existente},
            )


def _headers(client, nombre: str) -> dict:
    r = client.post("/api/auth/login", json={"nombre_usuario": nombre, "password": CONTRASENA_PRUEBA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def con_acceso(client):
    _usuario_con_acceso("test_ind_usuario", "Usuario", 1)
    return _headers(client, "test_ind_usuario")


@pytest.fixture(scope="module")
def sin_acceso(client):
    _usuario_con_acceso("test_ind_sin_acceso", "Usuario", 0)
    return _headers(client, "test_ind_sin_acceso")


BASE = "/api/dashboard/indicadores/resumen-general"
MARZO_2091 = {"anio": 2091, "mes": 3}
RUTAS = ["meses", "tarjetas", "acumulado", "tipos-gasto", "colaboradores", "detalle"]


@pytest.mark.parametrize("ruta", RUTAS)
def test_sin_sesion_no_entra(client, ruta):
    r = client.get(f"{BASE}/{ruta}", params=MARZO_2091)
    assert r.status_code in (401, 403)


@pytest.mark.parametrize("ruta", RUTAS)
def test_sin_acceso_a_indicadores_da_403_sin_nombrar_el_modulo(client, sin_acceso, ruta):
    r = client.get(f"{BASE}/{ruta}", params=MARZO_2091, headers=sin_acceso)
    assert r.status_code == 403
    assert "indicador" not in r.json()["detail"].lower()


def test_acceso_de_importaciones_no_da_acceso_a_indicadores(client, usuario_headers):
    r = client.get(f"{BASE}/meses", headers=usuario_headers)
    assert r.status_code == 403


def test_periodo_invalido(client, con_acceso, datos_viaticos):
    assert client.get(f"{BASE}/tarjetas", params={"anio": 2091, "mes": 13}, headers=con_acceso).status_code == 422
    assert client.get(f"{BASE}/tarjetas", headers=con_acceso).status_code == 422


def test_meses_disponibles_y_por_defecto(client, con_acceso, datos_viaticos):
    r = client.get(f"{BASE}/meses", headers=con_acceso)
    assert r.status_code == 200, r.text
    datos = r.json()
    claves = [(m["anio"], m["mes"]) for m in datos["meses"]]
    assert (2091, 3) in claves and (2090, 3) in claves
    assert claves == sorted(claves, reverse=True)
    assert datos["por_defecto"] == {"anio": claves[0][0], "mes": claves[0][1]}
    marzo = next(m for m in datos["meses"] if (m["anio"], m["mes"]) == (2091, 3))
    assert marzo["etiqueta"] == "Mar. 2091"


def test_tarjetas_valores_titulo_y_variacion(client, con_acceso, datos_viaticos):
    r = client.get(f"{BASE}/tarjetas", params=MARZO_2091, headers=con_acceso)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["titulo"] == "Resumen General de Viáticos del 01 al 31 de Marzo de 2091"
    por = {t["clave"]: t for t in datos["tarjetas"]}
    assert list(por) == ["total_viaticos", "tecnicos_conductores", "total_documentos", "total_proveedores"]
    assert [t["etiqueta"] for t in datos["tarjetas"]] == ["Total Viáticos", "Técnicos/Conductores", "Total Documentos", "Total Proveedores"]
    assert por["total_viaticos"]["valor"] == 150
    assert por["tecnicos_conductores"]["valor"] == 2
    assert por["total_documentos"]["valor"] == 2
    assert por["total_proveedores"]["valor"] == 2
    # marzo 2091 está incompleto (último día con datos = 6): se compara contra marzo 2090 del 1 al 6 (40), no
    # contra el mes completo (140)
    assert datos["periodo_parcial"] is True and datos["dia_corte"] == 6
    assert datos["texto_comparacion"] == "vs. mismo período año ant."
    assert por["total_viaticos"]["valor_anio_anterior"] == 40
    assert por["total_viaticos"]["variacion_pct"] == 275.0  # 40 -> 150
    assert por["tecnicos_conductores"]["variacion_pct"] == 100.0  # 1 -> 2
    assert por["total_documentos"]["valor_anio_anterior"] == 1 and por["total_documentos"]["variacion_pct"] == 100.0
    # 12 meses terminando en el mes elegido (abril 2090 .. marzo 2091)
    serie = por["total_viaticos"]["ultimos_12_meses"]
    assert [(p["anio"], p["mes"]) for p in serie][0] == (2090, 4) and [(p["anio"], p["mes"]) for p in serie][-1] == (2091, 3)
    assert [p["valor"] for p in serie][-3:] == [10, 20, 150]


def test_mes_completo_se_compara_contra_el_mes_completo(client, con_acceso, datos_viaticos):
    r = client.get(f"{BASE}/tarjetas", params={"anio": 2091, "mes": 4}, headers=con_acceso)
    datos = r.json()
    assert datos["periodo_parcial"] is False and datos["dia_corte"] is None
    assert datos["texto_comparacion"] == "vs. año ant."
    por = {t["clave"]: t for t in datos["tarjetas"]}
    assert por["total_viaticos"]["valor"] == 30
    assert por["total_viaticos"]["valor_anio_anterior"] == 10
    assert por["total_viaticos"]["variacion_pct"] == 200.0


def test_mes_incompleto_sin_datos_en_el_mismo_periodo_del_anio_anterior(client, con_acceso, datos_viaticos):
    # mayo 2091 llega hasta el día 2; mayo 2090 solo tiene datos el día 20: no hay con qué comparar
    r = client.get(f"{BASE}/tarjetas", params={"anio": 2091, "mes": 5}, headers=con_acceso)
    datos = r.json()
    assert datos["periodo_parcial"] is True and datos["dia_corte"] == 2
    por = {t["clave"]: t for t in datos["tarjetas"]}
    assert por["total_viaticos"]["valor"] == 5
    assert por["total_viaticos"]["valor_anio_anterior"] is None
    assert por["total_viaticos"]["variacion_pct"] is None


def test_variacion_es_nula_si_el_mes_del_anio_anterior_no_tiene_datos(client, con_acceso, datos_viaticos):
    r = client.get(f"{BASE}/tarjetas", params={"anio": 2091, "mes": 1}, headers=con_acceso)
    por = {t["clave"]: t for t in r.json()["tarjetas"]}
    assert por["total_viaticos"]["valor"] == 10
    assert por["total_viaticos"]["valor_anio_anterior"] is None
    assert por["total_viaticos"]["variacion_pct"] is None


def test_mes_sin_datos_da_ceros(client, con_acceso, datos_viaticos):
    r = client.get(f"{BASE}/tarjetas", params={"anio": 2091, "mes": 7}, headers=con_acceso)
    assert r.status_code == 200
    assert [t["valor"] for t in r.json()["tarjetas"]] == [0, 0, 0, 0]


def test_acumulado_hasta_el_mes_elegido(client, con_acceso, datos_viaticos):
    r = client.get(f"{BASE}/acumulado", params=MARZO_2091, headers=con_acceso)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert (datos["anio"], datos["anio_anterior"]) == (2091, 2090)
    actual = [p["acumulado"] for p in datos["serie_actual"]]
    assert actual[:3] == [10, 30, 180]
    assert all(v is None for v in actual[3:])  # el año elegido solo llega hasta el mes elegido
    anterior = [p["acumulado"] for p in datos["serie_anterior"]]
    assert anterior[:2] == [0, 0] and anterior[2] == 140 and anterior[3] == 150 and anterior[4:] == [200] * 8
    assert [p["etiqueta"] for p in datos["serie_actual"]][:3] == ["Ene", "Feb", "Mar"]


def test_tipos_gasto_y_colaboradores_ordenados_de_mayor_a_menor(client, con_acceso, datos_viaticos):
    r = client.get(f"{BASE}/tipos-gasto", params=MARZO_2091, headers=con_acceso)
    assert r.json()["datos"] == [{"nombre": "Hospedaje", "total_gastos": 100}, {"nombre": "Combustible", "total_gastos": 50}]
    assert r.json()["total"] == 150
    r = client.get(f"{BASE}/colaboradores", params=MARZO_2091, headers=con_acceso)
    assert r.json()["datos"] == [{"nombre": "Ana", "total_gastos": 100}, {"nombre": "Beto", "total_gastos": 50}]


def test_detalle_con_total(client, con_acceso, datos_viaticos):
    r = client.get(f"{BASE}/detalle", params=MARZO_2091, headers=con_acceso)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["total_factura"] == 150
    assert len(datos["filas"]) == 2
    primera = datos["filas"][0]
    assert primera["fecha_documento"] == "2091-03-05"
    assert (primera["tecnico"], primera["tipo_gasto"], primera["proveedor"], primera["total_factura"]) == ("Ana", "Hospedaje", MARCA + "P1", 100)
    assert set(primera) == {
        "fecha_documento", "fecha_inicial", "fecha_final", "tecnico", "tipo_gasto", "motivo", "total_factura", "proveedor",
    }

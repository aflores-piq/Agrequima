"""Avisos (campanita): permisos por rol, leído por usuario independiente, sin duplicados y generación al terminar una carga."""

import pytest
from sqlalchemy import text

from app.core.db import engine
from app.services import etl_plaguicidas
from app.services.avisos import crear_aviso
from app.tests.helpers import limpiar_importacion_anio, limpiar_nutrientes_anio
from app.tests.test_homologacion_empresas import (
    _cargar_nutrientes,
    _cargar_plaguicidas,
    _fila_nutrientes,
    _fila_plaguicidas,
)

TIPO = "TestAviso"


def _borrar_avisos(tipo_o_referencia: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dbo.Avisos WHERE Tipo = :x OR Referencia LIKE :r"), {"x": tipo_o_referencia, "r": tipo_o_referencia + "%"})


def _crear(destino: str, mensaje: str, referencia: str) -> bool:
    with engine.begin() as conn:
        return crear_aviso(conn, TIPO, mensaje, destino, referencia)


def _lista(client, headers, **params) -> dict:
    r = client.get("/api/avisos", headers=headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _mios(lista: dict, referencia: str | None = None) -> list[dict]:
    return [a for a in lista["avisos"] if a["tipo"] == TIPO and (referencia is None or a["referencia"] == referencia)]


@pytest.fixture()
def limpio():
    _borrar_avisos(TIPO)
    yield
    _borrar_avisos(TIPO)


# ---------------------------------------------------------------------------------------------

def test_solo_usuarios_autenticados(client):
    assert client.get("/api/avisos").status_code == 401
    assert client.post("/api/avisos/leer-todos").status_code == 401
    assert client.post("/api/avisos/1/leido").status_code == 401


def test_visibilidad_por_rol(client, limpio, admin_headers, usuario_headers, admin_usuarios_headers, usuario_sin_importaciones_headers):
    assert _crear("Todos", "Para todos", "t1") and _crear("Administrador", "Solo administrador", "a1")
    admin = _lista(client, admin_headers)
    assert {a["referencia"] for a in _mios(admin)} == {"t1", "a1"}
    for headers in (usuario_headers, admin_usuarios_headers):               # Usuario y Administrador de Usuarios: solo 'Todos'
        assert {a["referencia"] for a in _mios(_lista(client, headers))} == {"t1"}
    assert {a["referencia"] for a in _mios(_lista(client, usuario_sin_importaciones_headers))} == {"t1"}
    # El conteo de no leídos coincide con la lista
    for headers in (admin_headers, usuario_headers):
        d = _lista(client, headers)
        assert d["no_leidos"] == len(d["avisos"]) or d["no_leidos"] > len(d["avisos"])      # la lista tiene tope de 100


def test_avisos_de_importaciones_no_los_ve_quien_no_tiene_acceso(client, limpio, usuario_headers, usuario_sin_importaciones_headers):
    with engine.begin() as conn:
        crear_aviso(conn, "Importaciones.TestAviso", "Elemento nuevo de importaciones", "Todos", "TestAviso:imp")
    try:
        assert any(a["referencia"] == "TestAviso:imp" for a in _lista(client, usuario_headers)["avisos"])
        assert not any(a["referencia"] == "TestAviso:imp" for a in _lista(client, usuario_sin_importaciones_headers)["avisos"])
        # ni siquiera puede marcarlo (no debe deducir que existe)
        with engine.connect() as conn:
            aid = conn.execute(text("SELECT AvisoId FROM dbo.Avisos WHERE Referencia = 'TestAviso:imp'")).scalar()
        assert client.post(f"/api/avisos/{aid}/leido", headers=usuario_sin_importaciones_headers).status_code == 404
    finally:
        _borrar_avisos("Importaciones.TestAviso")
        _borrar_avisos("TestAviso:imp")


def test_leido_es_independiente_por_usuario(client, limpio, admin_headers, usuario_headers):
    _crear("Todos", "Aviso común", "c1")
    aid = _mios(_lista(client, usuario_headers), "c1")[0]["aviso_id"]
    antes_admin = _lista(client, admin_headers)["no_leidos"]
    antes_usuario = _lista(client, usuario_headers)["no_leidos"]

    r = client.post(f"/api/avisos/{aid}/leido", headers=usuario_headers)
    assert r.status_code == 200 and r.json()["no_leidos"] == antes_usuario - 1
    # Para el usuario desaparece de pendientes (pero está con incluir_leidos); para el administrador sigue sin leer
    assert not _mios(_lista(client, usuario_headers), "c1")
    leido = _mios(_lista(client, usuario_headers, incluir_leidos=True), "c1")
    assert len(leido) == 1 and leido[0]["leido"] is True
    assert _lista(client, admin_headers)["no_leidos"] == antes_admin
    assert _mios(_lista(client, admin_headers), "c1")[0]["leido"] is False
    # Marcarlo otra vez no falla ni cuenta doble
    assert client.post(f"/api/avisos/{aid}/leido", headers=usuario_headers).status_code == 200
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM dbo.AvisosLeidos WHERE AvisoId = :a"), {"a": aid}).scalar() == 1


def test_usuario_no_puede_marcar_aviso_del_administrador_ni_inexistente(client, limpio, admin_headers, usuario_headers):
    _crear("Administrador", "Solo admin", "a2")
    aid = _mios(_lista(client, admin_headers), "a2")[0]["aviso_id"]
    assert client.post(f"/api/avisos/{aid}/leido", headers=usuario_headers).status_code == 404
    assert client.post("/api/avisos/999999999/leido", headers=usuario_headers).status_code == 404
    assert client.post(f"/api/avisos/{aid}/leido", headers=admin_headers).status_code == 200


def test_leer_todos_solo_afecta_a_ese_usuario(client, limpio, admin_headers, usuario_headers):
    _crear("Todos", "Uno", "x1")
    _crear("Todos", "Dos", "x2")
    _crear("Administrador", "Tres", "x3")
    r = client.post("/api/avisos/leer-todos", headers=usuario_headers)
    assert r.status_code == 200 and r.json()["marcados"] >= 2 and r.json()["no_leidos"] == 0
    assert _lista(client, usuario_headers)["avisos"] == []
    admin = _lista(client, admin_headers)                                  # el administrador sigue con los suyos sin leer
    assert {a["referencia"] for a in _mios(admin)} == {"x1", "x2", "x3"}
    assert client.post("/api/avisos/leer-todos", headers=admin_headers).json()["no_leidos"] == 0
    assert _lista(client, admin_headers)["avisos"] == []
    # leer todos otra vez no marca nada
    assert client.post("/api/avisos/leer-todos", headers=admin_headers).json()["marcados"] == 0


def test_no_se_duplica_el_mismo_aviso(limpio):
    assert _crear("Todos", "Mensaje", "dup") is True
    assert _crear("Todos", "Mensaje (otra vez)", "dup") is False
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM dbo.Avisos WHERE Tipo = :t AND Referencia = 'dup'"), {"t": TIPO}).scalar() == 1


# ---------------------------------------------------------------------------------------------
# Generación al terminar una carga
# ---------------------------------------------------------------------------------------------

def _avisos_con(referencia_like: str) -> list[tuple]:
    with engine.connect() as conn:
        return [tuple(r) for r in conn.execute(
            text("SELECT Tipo, Mensaje, Destino, Referencia FROM dbo.Avisos WHERE Referencia LIKE :r ORDER BY AvisoId"), {"r": referencia_like})]


def test_carga_de_plaguicidas_crea_avisos_y_no_los_duplica(client, admin_headers):
    anio = 2064
    limpiar_importacion_anio(anio)
    ingrediente, producto = "ZZ INGREDIENTE NUEVO AV", "ZZPROD AVISO NUEVO"
    _borrar_avisos("Plaguicidas:ZZ INGREDIENTE NUEVO AV")
    _borrar_avisos("Plaguicidas:nombres:")
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dbo.Avisos WHERE Tipo = 'Importaciones.NombresSinHomologar' AND Mensaje LIKE '%ZZPROD AVISO NUEVO%'"))
    try:
        fila = _fila_plaguicidas(640001, "EMP AV", anio, 10.0, producto=producto)
        fila["INGREDIENTEACT"] = ingrediente
        _cargar_plaguicidas(client, admin_headers, [fila])

        elemento = _avisos_con("Plaguicidas:ZZ INGREDIENTE NUEVO AV")
        assert len(elemento) == 1
        tipo, mensaje, destino, _ = elemento[0]
        assert tipo == "Importaciones.ElementoNuevo" and destino == "Todos"
        assert "Hay un elemento nuevo: ZZ INGREDIENTE NUEVO AV" in mensaje
        with engine.connect() as conn:
            nombres = conn.execute(text("SELECT Mensaje, Destino FROM dbo.Avisos WHERE Tipo = 'Importaciones.NombresSinHomologar' AND Mensaje LIKE '%ZZPROD AVISO NUEVO%'")).all()
        assert len(nombres) == 1 and nombres[0][1] == "Administrador" and "sin homologar" in nombres[0][0]

        # Recargar lo mismo no duplica
        _cargar_plaguicidas(client, admin_headers, [fila])
        assert len(_avisos_con("Plaguicidas:ZZ INGREDIENTE NUEVO AV")) == 1
        # Aunque se borre el año y se vuelva a cargar (vuelve a ser "nuevo" para la carga), el aviso no se repite
        limpiar_importacion_anio(anio)
        _cargar_plaguicidas(client, admin_headers, [fila])
        assert len(_avisos_con("Plaguicidas:ZZ INGREDIENTE NUEVO AV")) == 1
        with engine.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM dbo.Avisos WHERE Tipo = 'Importaciones.NombresSinHomologar' AND Mensaje LIKE '%ZZPROD AVISO NUEVO%'")).scalar() == 1
    finally:
        limpiar_importacion_anio(anio)
        _borrar_avisos("Plaguicidas:ZZ INGREDIENTE NUEVO AV")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM dbo.Avisos WHERE Tipo = 'Importaciones.NombresSinHomologar' AND Mensaje LIKE '%ZZPROD AVISO NUEVO%'"))
            conn.execute(text("DELETE FROM dbo.log_ExcepcionesNombresComerciales WHERE Nombre = :n"), {"n": producto})


def test_una_carga_con_ingrediente_conocido_no_crea_aviso_de_elemento(client, admin_headers):
    anio = 2063
    limpiar_importacion_anio(anio)
    producto = "ZZPROD AVISO SIN ELEM"
    try:
        fila = _fila_plaguicidas(630001, "EMP AV", anio, 10.0, producto=producto)     # GLIFOSATO ya existe en la base de pruebas
        with engine.connect() as conn:
            existia = conn.execute(text("SELECT COUNT(*) FROM dbo.Importacion WHERE UPPER(ingrediente_act) = 'GLIFOSATO'")).scalar()
        if not existia:
            pytest.skip("la base de pruebas no tiene GLIFOSATO cargado todavía")
        _cargar_plaguicidas(client, admin_headers, [fila])
        assert _avisos_con("Plaguicidas:GLIFOSATO") == []
    finally:
        limpiar_importacion_anio(anio)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM dbo.Avisos WHERE Tipo = 'Importaciones.NombresSinHomologar' AND Mensaje LIKE '%ZZPROD AVISO SIN ELEM%'"))
            conn.execute(text("DELETE FROM dbo.log_ExcepcionesNombresComerciales WHERE Nombre = :n"), {"n": producto})


def test_carga_de_nutrientes_crea_aviso_de_elemento_y_de_nombre_nuevo(client, admin_headers):
    anio = 2062
    limpiar_nutrientes_anio(anio)
    componente, nombre = "ZZ COMPONENTE NUEVO AV", "ZZNUT AVISO NUEVO"
    _borrar_avisos("Nutrientes:ZZ COMPONENTE NUEVO AV")
    try:
        fila = _fila_nutrientes("1-62", "EMP AV", anio, "$10.00", nombre=nombre)
        fila["Componentes"] = componente
        _cargar_nutrientes(client, admin_headers, [fila])
        elemento = _avisos_con("Nutrientes:ZZ COMPONENTE NUEVO AV")
        assert len(elemento) == 1 and elemento[0][2] == "Todos" and "Hay un elemento nuevo: ZZ COMPONENTE NUEVO AV" in elemento[0][1]
        with engine.connect() as conn:
            nombres = conn.execute(text("SELECT Destino FROM dbo.Avisos WHERE Tipo = 'Importaciones.NombresSinHomologar' AND Mensaje LIKE '%ZZNUT AVISO NUEVO%'")).all()
        assert [n[0] for n in nombres] == ["Administrador"]
    finally:
        limpiar_nutrientes_anio(anio)
        _borrar_avisos("Nutrientes:ZZ COMPONENTE NUEVO AV")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM dbo.Avisos WHERE Tipo = 'Importaciones.NombresSinHomologar' AND Mensaje LIKE '%ZZNUT AVISO NUEVO%'"))


def test_si_falla_la_creacion_del_aviso_la_carga_no_falla(client, admin_headers, monkeypatch):
    anio = 2061
    limpiar_importacion_anio(anio)

    def explotar(*args, **kwargs):
        raise RuntimeError("falla simulada al crear avisos")

    monkeypatch.setattr(etl_plaguicidas, "generar_avisos_carga", explotar)
    try:
        resumen = _cargar_plaguicidas(client, admin_headers, [_fila_plaguicidas(610001, "EMP AV", anio, 10.0, producto="ZZPROD AVISO FALLA")])
        assert resumen["filas_cargadas"] == 1
        with engine.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM dbo.Importacion WHERE anio = :a"), {"a": anio}).scalar() == 1
    finally:
        limpiar_importacion_anio(anio)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM dbo.log_ExcepcionesNombresComerciales WHERE Nombre = 'ZZPROD AVISO FALLA'"))

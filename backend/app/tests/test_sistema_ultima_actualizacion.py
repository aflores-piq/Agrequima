"""GET /sistema/ultima-actualizacion: lee dbo.SyncEstado (script 24); vacío o sin la tabla -> None."""

from datetime import datetime

from sqlalchemy import text

from app.core.db import engine


def _guardar(fecha):
    with engine.begin() as c:
        c.execute(text("DELETE FROM dbo.SyncEstado WHERE Proceso = 'Financiero'"))
        if fecha is not None:
            c.execute(text("INSERT INTO dbo.SyncEstado (Proceso, UltimaEjecucionOk, Filas) VALUES ('Financiero', :f, 10)"), {"f": fecha})


def test_ultima_actualizacion_sin_registro_devuelve_null(client, usuario_headers):
    _guardar(None)
    r = client.get("/api/sistema/ultima-actualizacion", headers=usuario_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"ultima_actualizacion": None}


def test_ultima_actualizacion_devuelve_la_fecha_registrada(client, usuario_headers):
    _guardar(datetime(2026, 10, 10, 2, 5, 0))
    try:
        r = client.get("/api/sistema/ultima-actualizacion", headers=usuario_headers)
        assert r.status_code == 200, r.text
        assert r.json() == {"ultima_actualizacion": "2026-10-10T02:05:00"}
    finally:
        _guardar(None)


def test_ultima_actualizacion_requiere_sesion(client):
    assert client.get("/api/sistema/ultima-actualizacion").status_code in (401, 403)

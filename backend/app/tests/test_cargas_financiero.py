from sqlalchemy import text

from app.core.db import engine
from app.tests.helpers import (
    construir_excel_otro_ingreso,
    construir_excel_saldo_bancario,
    limpiar_otro_ingreso_periodo,
    limpiar_saldo_bancario_periodo,
)

# Año/mes dedicados a este archivo de pruebas, para no pisar datos de
# otro test ni de una carga real.
ANIO_PRUEBA = 2090
MES_PRUEBA = 1


def test_carga_saldos_bancarios_happy_path(client, admin_headers):
    limpiar_saldo_bancario_periodo(ANIO_PRUEBA, MES_PRUEBA)
    contenido = construir_excel_saldo_bancario([
        {"Concepto": "Saldo inicial", "Año": ANIO_PRUEBA, "Mes": MES_PRUEBA, "Banco": "BANRURAL", "Valor": 1000.50},
        {"Concepto": "Creditos", "Año": ANIO_PRUEBA, "Mes": MES_PRUEBA, "Banco": "BANRURAL", "Valor": 500.25},
        {"Concepto": "Debitos", "Año": ANIO_PRUEBA, "Mes": MES_PRUEBA, "Banco": "BI", "Valor": -200.00},
    ])

    r = client.post(
        "/api/admin/cargas/saldos-bancarios",
        headers=admin_headers,
        files={"archivo": ("saldos.xlsx", contenido)},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 3
    assert data["periodos"] == [{"anio": ANIO_PRUEBA, "mes": MES_PRUEBA}]
    assert data["estado"] == "OK"

    with engine.connect() as conn:
        filas_bd = conn.execute(
            text("SELECT COUNT(*) FROM dbo.SaldoBancario WHERE Anio = :a AND Mes = :m"),
            {"a": ANIO_PRUEBA, "m": MES_PRUEBA},
        ).scalar()
    assert filas_bd == 3


def test_carga_saldos_bancarios_reemplaza_el_mismo_periodo(client, admin_headers):
    """DELETE + INSERT por período: volver a subir el mismo mes reemplaza,
    no duplica."""
    limpiar_saldo_bancario_periodo(ANIO_PRUEBA, MES_PRUEBA + 1)
    contenido_v1 = construir_excel_saldo_bancario([
        {"Concepto": "Saldo inicial", "Año": ANIO_PRUEBA, "Mes": MES_PRUEBA + 1, "Banco": "BANCOR", "Valor": 100.0},
    ])
    r1 = client.post(
        "/api/admin/cargas/saldos-bancarios",
        headers=admin_headers,
        files={"archivo": ("v1.xlsx", contenido_v1)},
    )
    assert r1.status_code == 200, r1.text

    contenido_v2 = construir_excel_saldo_bancario([
        {"Concepto": "Saldo inicial", "Año": ANIO_PRUEBA, "Mes": MES_PRUEBA + 1, "Banco": "BANCOR", "Valor": 999.0},
        {"Concepto": "Creditos", "Año": ANIO_PRUEBA, "Mes": MES_PRUEBA + 1, "Banco": "BANCOR", "Valor": 50.0},
    ])
    r2 = client.post(
        "/api/admin/cargas/saldos-bancarios",
        headers=admin_headers,
        files={"archivo": ("v2.xlsx", contenido_v2)},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["filas_cargadas"] == 2

    with engine.connect() as conn:
        filas_bd = conn.execute(
            text("SELECT COUNT(*) FROM dbo.SaldoBancario WHERE Anio = :a AND Mes = :m"),
            {"a": ANIO_PRUEBA, "m": MES_PRUEBA + 1},
        ).scalar()
        valor_saldo_inicial = conn.execute(
            text(
                "SELECT Valor FROM dbo.SaldoBancario "
                "WHERE Anio = :a AND Mes = :m AND Concepto = 'Saldo inicial'"
            ),
            {"a": ANIO_PRUEBA, "m": MES_PRUEBA + 1},
        ).scalar()
    assert filas_bd == 2  # no 3 -- la v1 se reemplazó, no se acumuló
    assert float(valor_saldo_inicial) == 999.0


def test_carga_saldos_bancarios_requiere_rol_administrador(client, usuario_headers):
    contenido = construir_excel_saldo_bancario([
        {"Concepto": "Saldo inicial", "Año": 2091, "Mes": 1, "Banco": "BI", "Valor": 1.0},
    ])
    r = client.post(
        "/api/admin/cargas/saldos-bancarios",
        headers=usuario_headers,
        files={"archivo": ("test.xlsx", contenido)},
    )
    assert r.status_code == 403


def test_carga_saldos_bancarios_columna_faltante(client, admin_headers):
    contenido = construir_excel_saldo_bancario([
        {"Concepto": "Saldo inicial", "Año": 2091, "Mes": 1, "Valor": 1.0},  # falta Banco
    ])
    r = client.post(
        "/api/admin/cargas/saldos-bancarios",
        headers=admin_headers,
        files={"archivo": ("test.xlsx", contenido)},
    )
    assert r.status_code == 400


def test_carga_otros_ingresos_happy_path(client, admin_headers):
    limpiar_otro_ingreso_periodo(ANIO_PRUEBA, MES_PRUEBA)
    contenido = construir_excel_otro_ingreso([
        {"Tipo": "Presupuesto", "Concepto": "Venta de Sellos", "Anio": ANIO_PRUEBA, "Mes": MES_PRUEBA, "Valor": 1500.0},
        {"Tipo": "Ejecutado", "Concepto": "Gremiagro", "Anio": ANIO_PRUEBA, "Mes": MES_PRUEBA, "Valor": 800.0},
    ])

    r = client.post(
        "/api/admin/cargas/otros-ingresos",
        headers=admin_headers,
        files={"archivo": ("otros.xlsx", contenido)},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 2
    assert data["periodos"] == [{"anio": ANIO_PRUEBA, "mes": MES_PRUEBA}]
    assert data["estado"] == "OK"

    with engine.connect() as conn:
        filas_bd = conn.execute(
            text("SELECT COUNT(*) FROM dbo.OtroIngreso WHERE Anio = :a AND Mes = :m"),
            {"a": ANIO_PRUEBA, "m": MES_PRUEBA},
        ).scalar()
    assert filas_bd == 2


def test_carga_otros_ingresos_requiere_rol_administrador(client, usuario_headers):
    contenido = construir_excel_otro_ingreso([
        {"Tipo": "Presupuesto", "Concepto": "X", "Anio": 2091, "Mes": 1, "Valor": 1.0},
    ])
    r = client.post(
        "/api/admin/cargas/otros-ingresos",
        headers=usuario_headers,
        files={"archivo": ("test.xlsx", contenido)},
    )
    assert r.status_code == 403

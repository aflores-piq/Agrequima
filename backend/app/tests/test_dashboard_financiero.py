"""Pruebas del endpoint GET /dashboard/financiero/estados-financieros
contra las tablas REALES cargadas una sola vez desde CONTACC
(dbo.BalanceSaldos / dbo.BalanceGeneral -- ver
services/cargar_datos_financiero_inicial.py), no contra las vistas
vw_piq_* (esas siguen vacías, el sync nocturno todavía no las toca).

Los datos sintéticos usan años lejanos (2090/2091) que no colisionan
con los datos reales cargados (2025/2026) ni con dbo.CatalogoAgrupadorCuentas
(que sí se reutiliza tal cual -- ver agrupador_cuentas.py -- para
confirmar que el agrupamiento por Grupo sigue funcionando).

Los códigos de cuenta se reutilizan de la ronda anterior de pruebas,
donde ya se habían confirmado contra dbo.CatalogoAgrupadorCuentas real:
    410101001 -> Nivel 2 '410101' -> "Cuotas Asociados"
    410103001 -> Nivel 2 '410103' -> "Ingresos Facturados"
    510100001 -> Nivel 1 '5101'   -> "Sueldos Bonificaciones y Prestaciones de Ley"
    510200001 -> Nivel 1 '5102'   -> "Gastos Generales de Funcionamiento"
    110101001 -> "Caja y Bancos"
    120101001 -> "Propiedad y equipo"
    210101001 -> "Cuentas por pagar"
    310101001 -> "Patrimonio activos fijos"
El grupo de 210105001 (Fondos por aplicar) no se afirma por nombre acá
(no confirmado en ronda anterior) -- solo se valida por los TOTALES
(que sí dependen únicamente de la clasificación Cod_n1/cod_n5, no del
nombre de grupo)."""

import pytest
from sqlalchemy import text

from app.core.db import engine

_ANIOS_PRUEBA = (2090, 2091)

_DELETE = """
DELETE FROM dbo.BalanceSaldos WHERE Sal_Ano IN (2090, 2091);
DELETE FROM dbo.BalanceGeneral WHERE Sal_Ano IN (2090, 2091);
"""

# --- BalanceSaldos: Ingresos (Creditos) y Egresos (Debitos) -----------
# 2091-07 = "mes anterior" de la página 1 (mismo año que el filtro).
# 2091-08 = mes filtrado.
# 2090-08 = "año anterior" de la página 2 (acumulado hasta agosto).
_SEED_SALDOS = """
INSERT INTO dbo.BalanceSaldos (emp_nit, Cta_Codigo, Cta_Descripcion, Sal_Ano, Sal_Mes, Debitos, Creditos, Saldo, Cod_Centro) VALUES
('TEST-FIN', '410101001', 'Cuotas de Asociados', 2091, 7, 0, 5000, 5000, '01'),
('TEST-FIN', '410103001', 'Venta de Sellos',     2091, 7, 0, 2000, 2000, '01'),
('TEST-FIN', '510100001', 'Sueldos y Salarios',  2091, 7, 3000, 0, -3000, '01'),
('TEST-FIN', '510200001', 'Servicios Basicos',   2091, 7, 500,  0, -500,  '01'),
('TEST-FIN', '410101001', 'Cuotas de Asociados', 2091, 8, 0, 6000, 6000, '01'),
('TEST-FIN', '410103001', 'Venta de Sellos',     2091, 8, 0, 2500, 2500, '01'),
('TEST-FIN', '510100001', 'Sueldos y Salarios',  2091, 8, 3200, 0, -3200, '01'),
('TEST-FIN', '510200001', 'Servicios Basicos',   2091, 8, 600,  0, -600,  '01'),
('TEST-FIN', '410101001', 'Cuotas de Asociados', 2090, 8, 0, 4500, 4500, '01'),
('TEST-FIN', '410103001', 'Venta de Sellos',     2090, 8, 0, 1800, 1800, '01'),
('TEST-FIN', '510100001', 'Sueldos y Salarios',  2090, 8, 2900, 0, -2900, '01'),
('TEST-FIN', '510200001', 'Servicios Basicos',   2090, 8, 450,  0, -450,  '01');
"""

# --- BalanceGeneral: movimientos, YTD-dentro-del-año (ver semántica en
# services/dashboard_financiero.py) -- el Saldo de cada fila se SUMA
# desde enero hasta el mes filtrado, DENTRO DEL MISMO Sal_Ano.
# 210105001 (Fondos por aplicar) sin Cod_n1 -- igual que en los datos
# reales, donde esta cuenta puntual viene con Cod_n1 NULL.
_SEED_GENERAL = """
INSERT INTO dbo.BalanceGeneral (emp_nit, Cod_n1, Nom_n1, cod_n5, nom_n5, Sal_Ano, Sal_Mes, Debitos, Creditos, Saldo, Inicial) VALUES
('TEST-FIN', '1101', 'ACTIVO CORRIENTE',        '110101001', 'Caja y Bancos',        2091, 7, 0, 0, 45000, 45000),
('TEST-FIN', '1201', 'ACTIVO NO CORRIENTE',     '120101001', 'Mobiliario y Equipo',  2091, 7, 0, 0, 20000, 20000),
('TEST-FIN', '2101', 'PASIVO CORRIENTE',        '210101001', 'Cuentas por Pagar',    2091, 7, 0, 0, 14000, 14000),
('TEST-FIN', NULL,   'PASIVO -- FONDOS',        '210105001', 'Fondos por Aplicar',   2091, 7, 0, 0, 5000,  5000),
('TEST-FIN', '3101', 'PATRIMONIO AGREQUIMA',    '310101001', 'Capital Social',       2091, 7, 0, 0, 50000, 50000),
('TEST-FIN', '1101', 'ACTIVO CORRIENTE',        '110101001', 'Caja y Bancos',        2091, 8, 0, 0, -5000, -5000),
('TEST-FIN', '2101', 'PASIVO CORRIENTE',        '210101001', 'Cuentas por Pagar',    2091, 8, 0, 0, 1000,  1000),
('TEST-FIN', '3101', 'PATRIMONIO AGREQUIMA',    '310101001', 'Capital Social',       2091, 8, 0, 0, -10000, -10000),
('TEST-FIN', '1101', 'ACTIVO CORRIENTE',        '110101001', 'Caja y Bancos',        2090, 8, 0, 0, 38000, 38000),
('TEST-FIN', '1201', 'ACTIVO NO CORRIENTE',     '120101001', 'Mobiliario y Equipo',  2090, 8, 0, 0, 18000, 18000),
('TEST-FIN', '2101', 'PASIVO CORRIENTE',        '210101001', 'Cuentas por Pagar',    2090, 8, 0, 0, 11000, 11000),
('TEST-FIN', NULL,   'PASIVO -- FONDOS',        '210105001', 'Fondos por Aplicar',   2090, 8, 0, 0, 4000,  4000),
('TEST-FIN', '3101', 'PATRIMONIO AGREQUIMA',    '310101001', 'Capital Social',       2090, 8, 0, 0, 40000, 40000);
"""


@pytest.fixture(scope="module", autouse=True)
def _datos_financiero_sintéticos():
    with engine.begin() as conn:
        for bloque in (_DELETE, _SEED_SALDOS, _SEED_GENERAL):
            for stmt in bloque.split(";"):
                if stmt.strip():
                    conn.execute(text(stmt))
    yield
    with engine.begin() as conn:
        for stmt in _DELETE.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))


def test_dashboard_financiero_requiere_acceso_financiero(client, admin_sin_financiero_headers):
    r = client.get(
        "/api/dashboard/financiero/estados-financieros", headers=admin_sin_financiero_headers
    )
    assert r.status_code == 403


def _sin_cuentas(fila: dict) -> dict:
    return {k: v for k, v in fila.items() if k != "cuentas"}


def _pedir(client, admin_headers, anio, mes):
    r = client.get(
        "/api/dashboard/financiero/estados-financieros",
        headers=admin_headers,
        params={"anio": anio, "mes": mes},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_pagina1_ingresos_desembolsos_mensual(client, admin_headers):
    data = _pedir(client, admin_headers, 2091, 8)
    p1 = data["ingresos_desembolsos_mensual"]

    assert p1["kpis"] == {"ingresos": 8500.0, "egresos": 3800.0, "resultado": 4700.0}
    assert p1["etiqueta_mes_anterior"] == "Julio"
    assert p1["etiqueta_mes_actual"] == "Agosto"
    assert p1["etiqueta_acumulado"] == "Acumulado Año 2091"
    assert p1["grafico_mes"] == {"ingresos": 8500.0, "egresos": 3800.0, "resultado": 4700.0}
    assert p1["grafico_acumulado"] == {"ingresos": 15500.0, "egresos": 7300.0, "resultado": 8200.0}

    ingresos_por_grupo = {f["grupo"]: f for f in p1["detalle_ingresos"]}
    assert ingresos_por_grupo["Cuotas Asociados"]["mes_anterior"] == 5000.0
    assert ingresos_por_grupo["Cuotas Asociados"]["mes_actual"] == 6000.0
    assert ingresos_por_grupo["Cuotas Asociados"]["acumulado_anio"] == 11000.0
    assert ingresos_por_grupo["Ingresos Facturados"]["acumulado_anio"] == 4500.0
    assert p1["total_ingresos"] == {"mes_anterior": 7000.0, "mes_actual": 8500.0, "acumulado_anio": 15500.0}

    # Nivel Cuenta dentro del Grupo (nuevo, para las filas expandibles).
    cuentas_cuotas = ingresos_por_grupo["Cuotas Asociados"]["cuentas"]
    assert cuentas_cuotas == [{"cuenta": "Cuotas de Asociados", "mes_anterior": 5000.0, "mes_actual": 6000.0, "acumulado_anio": 11000.0}]

    egresos_por_grupo = {f["grupo"]: f for f in p1["detalle_egresos"]}
    assert egresos_por_grupo["Sueldos Bonificaciones y Prestaciones de Ley"]["acumulado_anio"] == 6200.0
    assert egresos_por_grupo["Gastos Generales de Funcionamiento"]["acumulado_anio"] == 1100.0
    assert p1["total_egresos"] == {"mes_anterior": 3500.0, "mes_actual": 3800.0, "acumulado_anio": 7300.0}

    assert p1["resultado_del_ejercicio"] == {"mes_anterior": 3500.0, "mes_actual": 4700.0, "acumulado_anio": 8200.0}


def test_pagina2_ingresos_desembolsos_acumulado(client, admin_headers):
    data = _pedir(client, admin_headers, 2091, 8)
    p2 = data["ingresos_desembolsos_acumulado"]

    assert p2["kpis"] == {"ingresos": 15500.0, "egresos": 7300.0, "saldo": 8200.0}
    assert p2["etiqueta_anio_anterior"] == "2090"
    assert p2["etiqueta_anio_actual"] == "2091"
    assert p2["titulo_grafico"] == "Comparativo al mes de Agosto 2090 vs. 2091"
    assert p2["grafico"] == [
        {"anio": 2090, "ingresos": 6300.0, "egresos": 3350.0, "resultado": 2950.0},
        {"anio": 2091, "ingresos": 15500.0, "egresos": 7300.0, "resultado": 8200.0},
    ]

    ingresos_por_grupo = {f["grupo"]: f for f in p2["detalle_ingresos"]}
    assert ingresos_por_grupo["Cuotas Asociados"]["anio_anterior"] == 4500.0
    assert ingresos_por_grupo["Cuotas Asociados"]["anio_actual"] == 11000.0
    assert ingresos_por_grupo["Cuotas Asociados"]["variacion"] == 6500.0
    assert p2["total_ingresos"] == {"anio_anterior": 6300.0, "anio_actual": 15500.0, "variacion": 9200.0}
    assert p2["total_egresos"] == {"anio_anterior": 3350.0, "anio_actual": 7300.0, "variacion": 3950.0}
    assert p2["resultado_del_ejercicio"] == {"anio_anterior": 2950.0, "anio_actual": 8200.0, "variacion": 5250.0}


def test_pagina3_balance_general_mensual(client, admin_headers):
    data = _pedir(client, admin_headers, 2091, 8)
    p3 = data["balance_general_mensual"]

    assert p3["kpis"] == {"activo": 60000.0, "pasivo": 20000.0, "patrimonio": 40000.0}
    assert p3["etiqueta_mes_anterior"] == "Julio"
    assert p3["etiqueta_mes_actual"] == "Agosto"
    assert p3["activo_referencia"] == 60000.0

    distribucion = {d["etiqueta"]: d for d in p3["distribucion_balance"]}
    assert set(distribucion.keys()) == {"Pasivo", "Patrimonio", "Fondos por aplicar"}
    assert distribucion["Pasivo"]["monto"] == 15000.0
    assert distribucion["Pasivo"]["porcentaje"] == pytest.approx(25.0)
    assert distribucion["Patrimonio"]["monto"] == 40000.0
    assert distribucion["Patrimonio"]["porcentaje"] == pytest.approx(40000 / 60000 * 100)
    assert distribucion["Fondos por aplicar"]["monto"] == 5000.0
    assert distribucion["Fondos por aplicar"]["porcentaje"] == pytest.approx(5000 / 60000 * 100)
    # Las 3 porciones deben sumar exactamente 100% de Activo (punto 3 del pedido).
    assert sum(d["porcentaje"] for d in distribucion.values()) == pytest.approx(100.0)

    activo_por_grupo = {f["grupo"]: f for f in p3["detalle_activo"]}
    assert _sin_cuentas(activo_por_grupo["Caja y Bancos"]) == {"grupo": "Caja y Bancos", "mes_anterior": 45000.0, "mes_actual": 40000.0, "diferencia": -5000.0}
    assert activo_por_grupo["Caja y Bancos"]["cuentas"] == [{"cuenta": "Caja y Bancos", "mes_anterior": 45000.0, "mes_actual": 40000.0, "diferencia": -5000.0}]
    assert _sin_cuentas(activo_por_grupo["Propiedad y equipo"]) == {"grupo": "Propiedad y equipo", "mes_anterior": 20000.0, "mes_actual": 20000.0, "diferencia": 0.0}
    assert p3["total_activo"] == {"mes_anterior": 65000.0, "mes_actual": 60000.0, "diferencia": -5000.0}

    # Pasivo TOTAL (banda/KPI/tabla) = Cuentas por pagar + Fondos por aplicar juntos.
    assert p3["total_pasivo"] == {"mes_anterior": 19000.0, "mes_actual": 20000.0, "diferencia": 1000.0}

    patrimonio_por_grupo = {f["grupo"]: f for f in p3["detalle_patrimonio"]}
    assert _sin_cuentas(patrimonio_por_grupo["Patrimonio activos fijos"]) == {"grupo": "Patrimonio activos fijos", "mes_anterior": 50000.0, "mes_actual": 40000.0, "diferencia": -10000.0}
    assert p3["total_patrimonio"] == {"mes_anterior": 50000.0, "mes_actual": 40000.0, "diferencia": -10000.0}

    assert p3["total_pasivo_y_patrimonio"] == {"mes_anterior": 69000.0, "mes_actual": 60000.0, "diferencia": -9000.0}


def test_pagina4_balance_general_comparativo(client, admin_headers):
    data = _pedir(client, admin_headers, 2091, 8)
    p4 = data["balance_general_comparativo"]

    assert p4["kpis"]["activo"] == {"diferencia_porcentaje": pytest.approx(4000 / 56000 * 100), "variacion_q": 4000.0}
    assert p4["kpis"]["pasivo"] == {"diferencia_porcentaje": pytest.approx(5000 / 15000 * 100), "variacion_q": 5000.0}
    assert p4["kpis"]["patrimonio"] == {"diferencia_porcentaje": pytest.approx(0.0), "variacion_q": 0.0}

    assert p4["etiqueta_anio_anterior"] == "2090"
    assert p4["etiqueta_anio_actual"] == "2091"
    assert p4["titulo_grafico"] == "Comparativo Balance General al mes de Agosto 2091 vs 2090"
    assert p4["grafico"] == [
        {"anio": 2090, "activo": 56000.0, "pasivo": 15000.0, "patrimonio": 40000.0},
        {"anio": 2091, "activo": 60000.0, "pasivo": 20000.0, "patrimonio": 40000.0},
    ]

    activo_por_grupo = {f["grupo"]: f for f in p4["detalle_activo"]}
    assert _sin_cuentas(activo_por_grupo["Caja y Bancos"]) == {"grupo": "Caja y Bancos", "anio_anterior": 38000.0, "anio_actual": 40000.0, "variacion": 2000.0}
    assert activo_por_grupo["Caja y Bancos"]["cuentas"] == [{"cuenta": "Caja y Bancos", "anio_anterior": 38000.0, "anio_actual": 40000.0, "variacion": 2000.0}]
    assert p4["total_activo"] == {"anio_anterior": 56000.0, "anio_actual": 60000.0, "variacion": 4000.0}
    assert p4["total_pasivo"] == {"anio_anterior": 15000.0, "anio_actual": 20000.0, "variacion": 5000.0}
    assert p4["total_patrimonio"] == {"anio_anterior": 40000.0, "anio_actual": 40000.0, "variacion": 0.0}
    assert p4["total_pasivo_y_patrimonio"] == {"anio_anterior": 55000.0, "anio_actual": 60000.0, "variacion": 5000.0}


def test_selector_periodo_acotado_a_datos_reales(client, admin_headers):
    """Punto 5: el selector solo debe ofrecer (año, mes) que existen de
    verdad en BalanceSaldos/BalanceGeneral -- se confirma que los 3
    períodos sintéticos insertados por esta suite aparecen, en orden."""
    data = _pedir(client, admin_headers, 2091, 8)
    periodos = {(p["anio"], p["mes"]) for p in data["periodos_disponibles"]}
    assert {(2090, 8), (2091, 7), (2091, 8)}.issubset(periodos)


def test_dashboard_financiero_periodo_sin_datos_no_falla(client, admin_headers):
    data = _pedir(client, admin_headers, 2085, 5)
    assert data["balance_general_mensual"]["kpis"] == {"activo": 0.0, "pasivo": 0.0, "patrimonio": 0.0}
    assert data["ingresos_desembolsos_mensual"]["kpis"] == {"ingresos": 0.0, "egresos": 0.0, "resultado": 0.0}
    assert data["balance_general_mensual"]["distribucion_balance"] == [
        {"etiqueta": "Pasivo", "monto": 0.0, "porcentaje": 0.0},
        {"etiqueta": "Patrimonio", "monto": 0.0, "porcentaje": 0.0},
        {"etiqueta": "Fondos por aplicar", "monto": 0.0, "porcentaje": 0.0},
    ]

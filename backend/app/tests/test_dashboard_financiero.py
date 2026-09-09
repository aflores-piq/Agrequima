"""Pruebas del endpoint GET /dashboard/financiero/estados-financieros.

Las 3 tablas espejo de CONTACC (vw_piq_balance_saldos/
vw_piq_balance_general/vw_catalogo_cuentas) no las crea esta suite en
el sentido real (eso lo hace sync_piq_ia.py reflejando el esquema de
origen) -- acá se crean como stand-in local con el esquema real
confirmado por el cliente, y se siembran con datos sintéticos
(emp_nit = 'TEST-FINANCIERO') para poder probar los cálculos de
verdad, sin depender de que el sync haya corrido contra CONTACC."""

import pytest
from sqlalchemy import text

from app.core.db import engine

_DDL = """
IF OBJECT_ID('dbo.vw_piq_balance_saldos', 'U') IS NULL
CREATE TABLE dbo.vw_piq_balance_saldos (
    emp_nit VARCHAR(20) NULL, Cta_Codigo VARCHAR(20) NULL, Cta_Descripcion VARCHAR(200) NULL,
    Sal_Ano INT NULL, Sal_Mes INT NULL, Debitos DECIMAL(18,2) NULL, Creditos DECIMAL(18,2) NULL,
    Saldo DECIMAL(18,2) NULL, Cod_Centro VARCHAR(20) NULL
);
IF OBJECT_ID('dbo.vw_piq_balance_general', 'U') IS NULL
CREATE TABLE dbo.vw_piq_balance_general (
    emp_nit VARCHAR(20) NULL, Cod_n1 VARCHAR(20) NULL, Nom_n1 VARCHAR(200) NULL,
    cod_n5 VARCHAR(20) NULL, nom_n5 VARCHAR(200) NULL, Sal_Ano INT NULL, Sal_Mes INT NULL,
    Debitos DECIMAL(18,2) NULL, Creditos DECIMAL(18,2) NULL, Saldo DECIMAL(18,2) NULL, Inicial DECIMAL(18,2) NULL
);
IF OBJECT_ID('dbo.vw_catalogo_cuentas', 'U') IS NULL
CREATE TABLE dbo.vw_catalogo_cuentas (
    cta_nivel VARCHAR(10) NULL, Codigo_N1 VARCHAR(20) NULL, Nombre_n1 VARCHAR(200) NULL,
    Codigo_N5 VARCHAR(20) NULL, Nombre_N5 VARCHAR(200) NULL
);
"""

_EMP_NIT = "TEST-FINANCIERO"

# Códigos de cuenta elegidos para que emparejen de verdad contra
# dbo.CatalogoAgrupadorCuentas (ver agrupador_cuentas.py):
#   510100001 -> Nivel 1 '5101' -> "Sueldos Bonificaciones y Prestaciones de Ley"
#   510200001 -> Nivel 1 '5102' -> "Gastos Generales de Funcionamiento"
#   410101001 -> Nivel 2 '410101' -> "Cuotas Asociados"
#   410103001 -> Nivel 2 '410103' -> "Ingresos Facturados"
_SEED = f"""
DELETE FROM dbo.vw_piq_balance_saldos WHERE emp_nit = '{_EMP_NIT}';
INSERT INTO dbo.vw_piq_balance_saldos
    (emp_nit, Cta_Codigo, Cta_Descripcion, Sal_Ano, Sal_Mes, Debitos, Creditos, Saldo, Cod_Centro) VALUES
('{_EMP_NIT}', '410101001', 'Cuotas de Asociados', 2026, 7, 0, 5000, 5000, '01'),
('{_EMP_NIT}', '410103001', 'Venta de Sellos', 2026, 7, 0, 2000, 2000, '01'),
('{_EMP_NIT}', '510100001', 'Sueldos y Salarios', 2026, 7, 3000, 0, -3000, '01'),
('{_EMP_NIT}', '510200001', 'Servicios Basicos', 2026, 7, 500, 0, -500, '01'),
('{_EMP_NIT}', '410101001', 'Cuotas de Asociados', 2026, 8, 0, 6000, 6000, '01'),
('{_EMP_NIT}', '410103001', 'Venta de Sellos', 2026, 8, 0, 2500, 2500, '01'),
('{_EMP_NIT}', '510100001', 'Sueldos y Salarios', 2026, 8, 3200, 0, -3200, '01'),
('{_EMP_NIT}', '510200001', 'Servicios Basicos', 2026, 8, 600, 0, -600, '01'),
('{_EMP_NIT}', '410101001', 'Cuotas de Asociados', 2025, 8, 0, 4500, 4500, '01'),
('{_EMP_NIT}', '410103001', 'Venta de Sellos', 2025, 8, 0, 1800, 1800, '01'),
('{_EMP_NIT}', '510100001', 'Sueldos y Salarios', 2025, 8, 2900, 0, -2900, '01'),
('{_EMP_NIT}', '510200001', 'Servicios Basicos', 2025, 8, 450, 0, -450, '01');

DELETE FROM dbo.vw_piq_balance_general WHERE emp_nit = '{_EMP_NIT}';
INSERT INTO dbo.vw_piq_balance_general
    (emp_nit, Cod_n1, Nom_n1, cod_n5, nom_n5, Sal_Ano, Sal_Mes, Debitos, Creditos, Saldo, Inicial) VALUES
('{_EMP_NIT}', '1', 'ACTIVO CORRIENTE', '110101001', 'Caja y Bancos', 2026, 7, 0, 0, 50000, 45000),
('{_EMP_NIT}', '1', 'ACTIVO NO CORRIENTE', '120101001', 'Mobiliario y Equipo', 2026, 7, 0, 0, 20000, 20000),
('{_EMP_NIT}', '2', 'PASIVO CORRIENTE', '210101001', 'Cuentas por Pagar', 2026, 7, 0, 0, 15000, 14000),
('{_EMP_NIT}', '2', 'PASIVO -- FONDOS POR APLICAR', '210105001', 'Fondos por Aplicar', 2026, 7, 0, 0, 5000, 5000),
('{_EMP_NIT}', '3', 'PATRIMONIO', '310101001', 'Capital Social', 2026, 7, 0, 0, 50000, 50000),
('{_EMP_NIT}', '1', 'ACTIVO CORRIENTE', '110101001', 'Caja y Bancos', 2026, 8, 0, 0, 45000, 50000),
('{_EMP_NIT}', '1', 'ACTIVO NO CORRIENTE', '120101001', 'Mobiliario y Equipo', 2026, 8, 0, 0, 20000, 20000),
('{_EMP_NIT}', '2', 'PASIVO CORRIENTE', '210101001', 'Cuentas por Pagar', 2026, 8, 0, 0, 16000, 15000),
('{_EMP_NIT}', '2', 'PASIVO -- FONDOS POR APLICAR', '210105001', 'Fondos por Aplicar', 2026, 8, 0, 0, 5000, 5000),
('{_EMP_NIT}', '3', 'PATRIMONIO', '310101001', 'Capital Social', 2026, 8, 0, 0, 44000, 50000),
('{_EMP_NIT}', '1', 'ACTIVO CORRIENTE', '110101001', 'Caja y Bancos', 2025, 8, 0, 0, 38000, 35000),
('{_EMP_NIT}', '1', 'ACTIVO NO CORRIENTE', '120101001', 'Mobiliario y Equipo', 2025, 8, 0, 0, 18000, 18000),
('{_EMP_NIT}', '2', 'PASIVO CORRIENTE', '210101001', 'Cuentas por Pagar', 2025, 8, 0, 0, 12000, 11000),
('{_EMP_NIT}', '2', 'PASIVO -- FONDOS POR APLICAR', '210105001', 'Fondos por Aplicar', 2025, 8, 0, 0, 4000, 4000),
('{_EMP_NIT}', '3', 'PATRIMONIO', '310101001', 'Capital Social', 2025, 8, 0, 0, 40000, 40000);
"""


@pytest.fixture(scope="module", autouse=True)
def _tablas_contacc_simuladas():
    with engine.begin() as conn:
        for stmt in _DDL.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
        for stmt in _SEED.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
    yield


def test_dashboard_financiero_requiere_acceso_financiero(client, admin_sin_financiero_headers):
    r = client.get(
        "/api/dashboard/financiero/estados-financieros", headers=admin_sin_financiero_headers
    )
    assert r.status_code == 403


def test_dashboard_financiero_valores_conocidos(client, admin_headers):
    r = client.get(
        "/api/dashboard/financiero/estados-financieros",
        headers=admin_headers,
        params={"anio": 2026, "mes": 8},
    )
    assert r.status_code == 200, r.text
    data = r.json()

    kpis1 = data["ingresos_desembolsos_mensual"]["kpis"]
    assert kpis1["ingresos"] == 8500.0
    assert kpis1["egresos"] == 3800.0
    assert kpis1["resultado"] == 4700.0
    assert kpis1["saldo_mes_anterior"] == 3500.0
    assert kpis1["acumulado_saldo_mes_corriente"] == 8200.0

    # Egresos no debe incluir cuentas de Ingresos (bug real que se
    # encontró y corrigió durante el desarrollo: una cuenta con
    # Debitos=0 no debe aparecer solo porque su saldo acumulado no sea
    # cero).
    detalle_egresos = data["ingresos_desembolsos_mensual"]["detalle_egresos"]
    nombres_egresos = {f["nombre_cuenta_n5"] for f in detalle_egresos}
    assert nombres_egresos == {"Servicios Basicos", "Sueldos y Salarios"}
    detalle_ingresos = data["ingresos_desembolsos_mensual"]["detalle_ingresos"]
    nombres_ingresos = {f["nombre_cuenta_n5"] for f in detalle_ingresos}
    assert nombres_ingresos == {"Cuotas de Asociados", "Venta de Sellos"}

    # "Grupo" ahora sale de dbo.CatalogoAgrupadorCuentas (emparejamiento
    # jerárquico por código), no de vw_catalogo_cuentas/Nombre_n1.
    grupo_por_cuenta_egresos = {f["nombre_cuenta_n5"]: f["grupo"] for f in detalle_egresos}
    assert grupo_por_cuenta_egresos["Sueldos y Salarios"] == "Sueldos Bonificaciones y Prestaciones de Ley"
    assert grupo_por_cuenta_egresos["Servicios Basicos"] == "Gastos Generales de Funcionamiento"
    grupo_por_cuenta_ingresos = {f["nombre_cuenta_n5"]: f["grupo"] for f in detalle_ingresos}
    assert grupo_por_cuenta_ingresos["Cuotas de Asociados"] == "Cuotas Asociados"
    assert grupo_por_cuenta_ingresos["Venta de Sellos"] == "Ingresos Facturados"

    grupos_cascada_egresos = {f["grupo"] for f in data["ingresos_desembolsos_mensual"]["cascada_egresos_por_grupo"]}
    assert grupos_cascada_egresos == {"Sueldos Bonificaciones y Prestaciones de Ley", "Gastos Generales de Funcionamiento"}

    kpis3 = data["balance_general_mensual"]["kpis"]
    assert kpis3["activo"] == 65000.0
    assert kpis3["pasivo"] == 16000.0
    assert kpis3["patrimonio"] == 44000.0
    assert kpis3["balance_mensual"] == 0.0  # el balance contable debe cuadrar

    detalle_activo = data["balance_general_mensual"]["detalle_activo"]
    grupo_por_cuenta_activo = {f["nombre_n5"]: f["grupo"] for f in detalle_activo}
    assert grupo_por_cuenta_activo["Caja y Bancos"] == "Caja y Bancos"
    assert grupo_por_cuenta_activo["Mobiliario y Equipo"] == "Propiedad y equipo"
    detalle_pasivo = data["balance_general_mensual"]["detalle_pasivo"]
    assert detalle_pasivo[0]["grupo"] == "Cuentas por pagar"
    detalle_patrimonio = data["balance_general_mensual"]["detalle_patrimonio"]
    assert detalle_patrimonio[0]["grupo"] == "Patrimonio activos fijos"

    kpis4 = data["balance_general_comparativo"]["kpis"]
    assert kpis4["total_acumulado_anterior"] == 56000.0
    assert kpis4["total_acumulado_actual"] == 65000.0
    assert kpis4["total_variacion"] == 9000.0
    assert kpis4["balance_acumulado"] == 0.0


def test_dashboard_financiero_periodo_sin_datos_no_falla(client, admin_headers):
    r = client.get(
        "/api/dashboard/financiero/estados-financieros",
        headers=admin_headers,
        params={"anio": 2099, "mes": 5},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["balance_general_mensual"]["kpis"]["activo"] == 0.0
    assert data["balance_general_mensual"]["kpis"]["porcentaje_activo"] == 0.0

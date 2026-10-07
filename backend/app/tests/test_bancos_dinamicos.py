"""Bancos e inversiones a plazo DINÁMICOS en Conciliación bancaria y Flujo de
caja: la lista de bancos sale de los datos (SaldosBancos + ChequesCirculacion
+ SaldoBancario), nombre/color/orden salen de dbo.CatalogoBancos, y las
inversiones a plazo son todas las cuentas 110103xxx de BalanceGeneral.

Las pruebas de integración usan el año 2098 y marcadores 'ZZ ...' para no
mezclarse con datos reales ni con otras pruebas, y limpian antes y después.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.db import engine
from app.services.catalogo_bancos import (
    COLOR_BANCO_POR_DEFECTO,
    BancoCatalogo,
    ResolutorBancos,
    cargar_catalogo_bancos,
    limpiar_texto,
    normalizar_codigo_banco,
    ordenar_conciliacion,
    ordenar_flujo,
)
from app.services.dashboard_otros_informes import _etiqueta_inversion_plazo

ANIO = 2098
MES = 12
BANCO = "ZZ BANCO TEST"
NBSP = " "
CUENTA_PLAZO = "110103999"
URL_CONCILIACION = f"/api/dashboard/financiero/conciliacion-bancaria?anio={ANIO}&mes={MES}"
URL_FLUJO = f"/api/dashboard/financiero/flujo-caja?anio={ANIO}&mes={MES}"


# --- Unitarias (sin base de datos) -----------------------------------------


def _catalogo(**campos) -> BancoCatalogo:
    base = dict(
        clave="X", ban_codigo="X", nombre_conciliacion=None, nombre_flujo=None, color_hex=None,
        orden=None, orden_flujo=None, activo=True, clave_alias="",
    )
    base.update(campos)
    return BancoCatalogo(**base)


def test_normalizar_codigo_banco_une_tildes_mayusculas_y_caracteres_invisibles():
    variantes = ["PROMÉRICA", "Promerica", "PROMERICA" + NBSP, " promérica\r\n", "PROME​RICA", "\tProMérica "]
    assert {normalizar_codigo_banco(v) for v in variantes} == {"PROMERICA"}
    assert normalizar_codigo_banco("Banco  Industrial") == "BANCOINDUSTRIAL"
    assert normalizar_codigo_banco(None) == ""
    assert normalizar_codigo_banco(" \r\n" + NBSP) == ""


def test_limpiar_texto_quita_invisibles_y_colapsa_espacios():
    assert limpiar_texto("BAC - FONDO\r\n DE" + NBSP + "INVERSIÓN\n") == "BAC - FONDO DE INVERSIÓN"
    assert limpiar_texto("A​B") == "AB"
    assert limpiar_texto(None) == ""


def test_banco_fuera_del_catalogo_sale_en_gris_con_su_codigo_y_al_final():
    resolutor = ResolutorBancos([
        _catalogo(clave="BANCOR", ban_codigo="BANCOR", nombre_conciliacion="BAC", nombre_flujo="BAC Reformador",
                  color_hex="#E31B23", orden=1, orden_flujo=3),
        _catalogo(clave="BI", ban_codigo="BI", nombre_conciliacion="BI", nombre_flujo="Banco Industrial",
                  color_hex="#004B87", orden=3, orden_flujo=2),
    ])
    bancos = resolutor.resolver({"ZNUEVO": "Z Nuevo", "BI": "BI", "ANUEVO": "A Nuevo", "BANCOR": "BANCOR"})
    conc = ordenar_conciliacion(bancos)
    assert [b.nombre_conciliacion for b in conc] == ["BAC", "BI", "A Nuevo", "Z Nuevo"]
    assert [b.color for b in conc] == ["#E31B23", "#004B87", COLOR_BANCO_POR_DEFECTO, COLOR_BANCO_POR_DEFECTO]
    assert [b.nombre_flujo for b in ordenar_flujo(bancos)] == ["Banco Industrial", "BAC Reformador", "A Nuevo", "Z Nuevo"]


def test_catalogo_con_solo_codigo_y_color_usa_el_codigo_como_nombre_y_color_invalido_cae_a_gris():
    resolutor = ResolutorBancos([_catalogo(clave="NUEVO", ban_codigo="NUEVO", color_hex="#7B1FA2"),
                                 _catalogo(clave="MALO", ban_codigo="MALO", color_hex="rojo")])
    por_clave = {b.clave: b for b in resolutor.resolver({"NUEVO": "Nuevo", "MALO": "Malo"})}
    assert por_clave["NUEVO"].color == "#7B1FA2"
    assert por_clave["NUEVO"].nombre_conciliacion == "NUEVO" and por_clave["NUEVO"].nombre_flujo == "NUEVO"
    assert por_clave["MALO"].color == COLOR_BANCO_POR_DEFECTO


def test_banco_inactivo_se_oculta_y_el_alias_une_saldo_bancario_con_el_banco():
    resolutor = ResolutorBancos([
        _catalogo(clave="VIEJO", ban_codigo="VIEJO", activo=False),
        _catalogo(clave="BANCOR", ban_codigo="BANCOR", clave_alias="BAC"),
    ])
    assert resolutor.resolver({"VIEJO": "VIEJO"}) == []
    assert not resolutor.activo("VIEJO") and resolutor.activo("CUALQUIERA")
    assert resolutor.clave("bac ") == "BANCOR"  # nombre del Excel de SaldoBancario
    assert resolutor.clave("BANCOR") == "BANCOR"
    assert resolutor.clave("  ") is None


def test_orden_flujo_cae_al_orden_normal_si_es_nulo():
    resolutor = ResolutorBancos([_catalogo(clave="A", ban_codigo="A", orden=2), _catalogo(clave="B", ban_codigo="B", orden=1)])
    bancos = resolutor.resolver({"A": "A", "B": "B"})
    assert [b.clave for b in ordenar_flujo(bancos)] == ["B", "A"]


def test_catalogo_inexistente_no_rompe_la_pantalla():
    class _SesionSinTabla:
        reversada = False

        def execute(self, *_a, **_k):
            raise ProgrammingError("SELECT", {}, Exception("Invalid object name 'dbo.CatalogoBancos'"))

        def rollback(self):
            self.reversada = True

    sesion = _SesionSinTabla()
    assert cargar_catalogo_bancos(sesion) == [] and sesion.reversada


@pytest.mark.parametrize(
    "nom_n5,esperado",
    [
        ("BAC - FONDO DE INVERSIÓN", "(+) Inversiones Plazo Fijo Bac"),
        ("PROMÉRICA - FONDO DE INVERSIÓN\r\n", "(+) Inversiones Plazo Fijo Promerica"),
        ("BI" + NBSP + "- FONDO", "(+) Inversiones Plazo Fijo Bi"),  # el NBSP se limpia antes de partir por " - "
        ("INVERSION PLAZO FIJO G&T", "(+) Inversion Plazo Fijo G&T"),
        (None, "(+) Inversiones Plazo Fijo 110103999"),
    ],
)
def test_etiqueta_de_inversion_sale_de_nom_n5(nom_n5, esperado):
    assert _etiqueta_inversion_plazo(nom_n5, "110103999") == esperado


# --- Integración (base Agrequima_Test) --------------------------------------


@pytest.fixture(scope="module", autouse=True)
def tablas_de_bancos():
    """Agrequima_Test puede ser anterior a SaldosBancos/CatalogoBancos:
    se crean (mismo DDL que db/agrequima_schema_sql_server.sql) si faltan."""
    with engine.begin() as conn:
        conn.execute(text("""
            IF OBJECT_ID('dbo.SaldosBancos') IS NULL
            CREATE TABLE dbo.SaldosBancos(
                saldobancoid INT IDENTITY(1,1) NOT NULL PRIMARY KEY, ban_codigo VARCHAR(50) NULL,
                Sal_Mes INT NULL, Sal_Ano INT NULL, InicialL DECIMAL(18,2) NULL, EntradasL DECIMAL(18,2) NULL,
                SalidasL DECIMAL(18,2) NULL, FinalL DECIMAL(18,2) NULL, fechamod DATETIME NULL, userid INT NULL)
        """))
        conn.execute(text("""
            IF OBJECT_ID('dbo.CatalogoBancos') IS NULL
            CREATE TABLE dbo.CatalogoBancos(
                catalogobancoid INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_CatalogoBancos PRIMARY KEY,
                ban_codigo NVARCHAR(50) NOT NULL CONSTRAINT UQ_CatalogoBancos_ban_codigo UNIQUE,
                nombre_conciliacion NVARCHAR(100) NULL, nombre_flujo NVARCHAR(100) NULL, color_hex VARCHAR(7) NULL,
                orden INT NULL, orden_flujo INT NULL, activo BIT NOT NULL CONSTRAINT DF_CatalogoBancos_activo DEFAULT 1,
                alias_saldo_bancario NVARCHAR(100) NULL,
                fechamod DATETIME NOT NULL CONSTRAINT DF_CatalogoBancos_fechamod DEFAULT GETDATE(),
                CONSTRAINT CK_CatalogoBancos_color CHECK (
                    color_hex IS NULL OR color_hex LIKE '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'))
        """))


def _limpiar():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dbo.SaldosBancos WHERE Sal_Ano = :a"), {"a": ANIO})
        conn.execute(text("DELETE FROM dbo.ChequesCirculacion WHERE par_ano = :a"), {"a": ANIO})
        conn.execute(text("DELETE FROM dbo.SaldoBancario WHERE Anio = :a"), {"a": ANIO})
        conn.execute(text("DELETE FROM dbo.BalanceGeneral WHERE Sal_Ano = :a"), {"a": ANIO})
        conn.execute(text("DELETE FROM dbo.CatalogoBancos WHERE ban_codigo LIKE 'ZZ %'"))


@pytest.fixture(autouse=True)
def limpiar_datos_de_prueba():
    _limpiar()
    yield
    _limpiar()


def _cargar_banco_nuevo():
    """El MISMO banco escrito de tres formas distintas en las tres fuentes."""
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO dbo.SaldosBancos (ban_codigo, Sal_Mes, Sal_Ano, InicialL, EntradasL, SalidasL, FinalL) "
                 "VALUES (:b, :m, :a, 1000, 500, 200, 1300)"),
            {"b": BANCO, "m": MES, "a": ANIO},
        )
        conn.execute(
            text("INSERT INTO dbo.ChequesCirculacion (ban_codigo, cta_numero, par_ano, par_mes, doc_numero, doc_fecha, doc_fchcobro, doc_monto) "
                 "VALUES (:b, '000', :a, :m, 'ZZ1', :f, NULL, 250)"),
            {"b": BANCO + NBSP, "a": ANIO, "m": MES, "f": datetime(ANIO, 6, 15)},
        )
        conn.execute(
            text("INSERT INTO dbo.SaldoBancario (Concepto, Anio, Mes, Banco, Valor, UsuarioId) VALUES "
                 "(N'Saldo inicial', :a, :m, :b, 900, 1), (N'Creditos', :a, :m, :b, 400, 1), (N'Debitos', :a, :m, :b, 100, 1)"),
            {"a": ANIO, "m": MES, "b": BANCO.lower()},
        )


def _bancos_conciliacion(client, headers) -> list[dict]:
    r = client.get(URL_CONCILIACION, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["bancos"]


def _filas_por_descripcion(banco: dict) -> dict:
    return {f["descripcion"]: f for f in banco["filas"]}


def test_banco_nuevo_aparece_en_gris_al_final_de_conciliacion_con_sus_datos(client, admin_headers):
    _cargar_banco_nuevo()
    bancos = _bancos_conciliacion(client, admin_headers)
    nuevo = next(b for b in bancos if b["nombre"] == BANCO)
    assert nuevo["color"] == COLOR_BANCO_POR_DEFECTO
    # al final: después de todos los bancos del catálogo
    with engine.connect() as conn:
        del_catalogo = {r[0] for r in conn.execute(text("SELECT nombre_conciliacion FROM dbo.CatalogoBancos WHERE activo = 1"))}
    posiciones = [i for i, b in enumerate(bancos) if b["nombre"] in del_catalogo]
    assert not posiciones or bancos.index(nuevo) > max(posiciones)
    filas = _filas_por_descripcion(nuevo)
    # las tres fuentes (aunque el código venga con NBSP o en minúsculas) cayeron en UN solo banco
    assert sum(1 for b in bancos if b["nombre"] == BANCO) == 1
    assert filas["Saldo inicial"]["saldo_contabilidad"] == 1000 and filas["Saldo inicial"]["saldo_banco"] == 900
    assert filas["(+) Créditos"]["saldo_contabilidad"] == 500 and filas["(+) Créditos"]["saldo_banco"] == 400
    assert filas["(−) Débitos"]["saldo_contabilidad"] == 200 and filas["(−) Débitos"]["saldo_banco"] == 100
    assert filas["(−) Documentos en Circulación"]["saldo_banco"] == 250
    assert filas["Totales"]["saldo_contabilidad"] == 1300
    assert filas["Totales"]["saldo_banco"] == 900 + 400 - 100 - 250


def test_banco_nuevo_aparece_en_flujo_de_caja_y_suma_en_los_totales(client, admin_headers):
    _cargar_banco_nuevo()
    r = client.get(URL_FLUJO, headers=admin_headers)
    assert r.status_code == 200, r.text
    filas = r.json()["filas"]
    bancos = [f for f in filas if f["tipo"] == "BANCO"]
    cheques = [f for f in filas if f["tipo"] == "CHEQUE"]
    assert next(f for f in bancos if f["descripcion"] == BANCO)["saldos"] == 1300
    assert next(f for f in cheques if f["descripcion"] == BANCO)["saldos"] == 250
    caja = next(f for f in filas if f["tipo"] == "CAJA")["saldos"]
    total_bancos = next(f for f in filas if f["tipo"] == "TOTAL_BANCOS")
    assert total_bancos["saldos"] == pytest.approx(caja + sum(f["saldos"] for f in bancos))
    total_cheques = next(f for f in filas if f["tipo"] == "TOTAL_CHEQUES")
    assert total_cheques["saldos"] == pytest.approx(sum(f["saldos"] for f in cheques))


def test_ponerle_color_a_un_banco_nuevo_es_un_insert_sin_tocar_codigo(client, admin_headers):
    _cargar_banco_nuevo()
    assert next(b for b in _bancos_conciliacion(client, admin_headers) if b["nombre"] == BANCO)["color"] == COLOR_BANCO_POR_DEFECTO

    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO dbo.CatalogoBancos (ban_codigo, nombre_conciliacion, nombre_flujo, color_hex, orden, orden_flujo) "
                 "VALUES (:c, N'ZZ BANCO TEST CONC', N'ZZ Banco Test Flujo', '#7B1FA2', 1, 1)"),
            {"c": BANCO},
        )
    bancos = _bancos_conciliacion(client, admin_headers)
    nuevo = next(b for b in bancos if b["nombre"] == "ZZ BANCO TEST CONC")
    assert nuevo["color"] == "#7B1FA2" and not any(b["nombre"] == BANCO for b in bancos)
    flujo = client.get(URL_FLUJO, headers=admin_headers).json()["filas"]
    assert any(f["tipo"] == "BANCO" and f["descripcion"] == "ZZ Banco Test Flujo" for f in flujo)

    # un UPDATE basta para cambiarle el color después
    with engine.begin() as conn:
        conn.execute(text("UPDATE dbo.CatalogoBancos SET color_hex = '#112233' WHERE ban_codigo = :c"), {"c": BANCO})
    assert next(b for b in _bancos_conciliacion(client, admin_headers) if b["nombre"] == "ZZ BANCO TEST CONC")["color"] == "#112233"

    # activo = 0 lo oculta en las dos pantallas y deja de sumar en los totales
    with engine.begin() as conn:
        conn.execute(text("UPDATE dbo.CatalogoBancos SET activo = 0 WHERE ban_codigo = :c"), {"c": BANCO})
    assert not any(b["nombre"] == "ZZ BANCO TEST CONC" for b in _bancos_conciliacion(client, admin_headers))
    filas = client.get(URL_FLUJO, headers=admin_headers).json()["filas"]
    assert not any(f["descripcion"] == "ZZ Banco Test Flujo" for f in filas)


def test_cuenta_110103_nueva_aparece_como_inversion_y_suma_al_total_de_flujo(client, admin_headers):
    with engine.begin() as conn:
        for mes, saldo in ((10, Decimal("500000.00")), (12, Decimal("200000.25"))):
            conn.execute(
                text("INSERT INTO dbo.BalanceGeneral (emp_nit, Cod_n1, Nom_n1, cod_n5, nom_n5, Sal_Ano, Sal_Mes, Debitos, Creditos, Saldo, Inicial) "
                     "VALUES ('ZZ', '1101', 'CAJA Y BANCOS', :c, :n, :a, :m, 0, 0, :s, 0)"),
                {"c": CUENTA_PLAZO + NBSP, "n": "ZZ TEST - FONDO DE INVERSIÓN\r\n", "a": ANIO, "m": mes, "s": saldo},
            )
    r = client.get(URL_FLUJO, headers=admin_headers)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    filas = cuerpo["filas"]
    inversiones = [f for f in filas if f["tipo"] == "INVERSION"]
    nueva = next(f for f in inversiones if f["descripcion"] == "(+) Inversiones Plazo Fijo Zz Test")
    assert nueva["disponibilidad"] == pytest.approx(700000.25)  # acumulado del año hasta el mes
    disponibilidad = next(f for f in filas if f["tipo"] == "DISPONIBILIDAD")["disponibilidad"]
    total_final = next(f for f in filas if f["tipo"] == "TOTAL_FINAL")["disponibilidad"]
    assert total_final == pytest.approx(disponibilidad + sum(f["disponibilidad"] for f in inversiones))
    barra = next(b for b in cuerpo["grafica"] if b["etiqueta"] == "Inversiones")
    assert barra["valor"] == pytest.approx(sum(f["disponibilidad"] for f in inversiones))
    # el mes anterior al primer movimiento: la cuenta sigue en la lista, en Q0
    antes = client.get(f"/api/dashboard/financiero/flujo-caja?anio={ANIO}&mes=9", headers=admin_headers).json()["filas"]
    assert next(f for f in antes if f["descripcion"] == "(+) Inversiones Plazo Fijo Zz Test")["disponibilidad"] == 0

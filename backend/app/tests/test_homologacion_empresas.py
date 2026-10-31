"""Homologación de empresas (script 26): clave normalizada, sincronización con el catálogo, cargas y tableros.

Las pruebas corren contra Agrequima_Test, a la que hay que aplicar el script 26 (deploy_servidor_real/26_homologacion_empresas.sql,
con USE Agrequima_Test). Cada prueba usa su propio año de prueba y limpia lo que crea en dbo.CatalogoEmpresas.
"""

import re
import unicodedata

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import engine
from app.services.empresas import clave_empresa, sincronizar_empresas
from app.tests.helpers import (
    construir_csv_nutrientes,
    construir_excel_importaciones,
    limpiar_importacion_anio,
    limpiar_nutrientes_anio,
)

# ---------------------------------------------------------------------------------------------
# 1) Clave normalizada
# ---------------------------------------------------------------------------------------------

# Escritas distinto, son la MISMA empresa
PARES_QUE_SE_UNEN = [
    ("DISAGRO DE GUATEMALA, S.A", "DISAGRO DE GUATEMALA, SOCIEDAD ANONIMA"),
    ("Grupo Fert, S. A.", "GRUPO FERT, S.A"),
    ("TRIBO SA", "TRIBO, S.A."),
    ("Agrocentro Sociedad Anonima", "Agrocentro, S.A."),
    ("FERTICA GUATEMALA, SOCIEDAD ANONIMA.", "Fertica Guatemala, S.A."),
    ("Yara Guatemala, S.A.", "YARA GUATEMALA S A"),
    ("Química Stoller de Centroamérica, Sociedad Anónima", "QUIMICAS STOLLER DE CENTROAMERICA".replace("QUIMICAS", "QUIMICA") + ", S.A"),
    ("PEÑA Y CIA, S. A.", "Pena y Cia, SA"),
    ("  EL COLONO   AGROPECUARIO ,  S.A. ", "El Colono Agropecuario, Sociedad Anonima"),
]

# Son empresas DISTINTAS (o errores de tipeo que NO se deben unir)
PARES_DISTINTOS = [
    ("AGROCENTRO, S.A.", "AGROSENTRO, S.A."),                       # error de tipeo: no se une
    ("DISAGRO DE GUATEMALA, S.A", "DISAGRO DE HONDURAS, S.A"),
    ("TRIBO, S.A.", "TRIBO COMERCIAL, S.A."),                       # otra palabra: no se quita
    ("SOCIEDAD AGRICOLA UNIDA", "AGRICOLA UNIDA, S.A."),            # "SOCIEDAD" suelta no es el sufijo
    ("YARA GUATEMALA", "YARA GUATEMALA SERVICIOS"),
    ("BAYER, S.A.", "BAYER CROPSCIENCE, S.A."),
]


def _referencia(valor: str) -> str | None:
    """Implementación de referencia en Python (el oráculo de la prueba) de la clave de dbo.fn_ClaveEmpresa."""
    s = "".join(c for c in unicodedata.normalize("NFD", valor.strip()) if unicodedata.category(c) != "Mn").upper()
    s = s.replace(".", " ").replace(",", " ")
    s = re.sub(r"\s+", " ", s)
    s = (" " + s + " ").replace(" SOCIEDAD ANONIMA ", " SA ").replace(" S A ", " SA ")
    return s.strip() or None


def _clave(texto: str | None) -> str | None:
    with engine.connect() as conn:
        return clave_empresa(conn, texto)


@pytest.mark.parametrize("a,b", PARES_QUE_SE_UNEN)
def test_clave_une_las_variantes_de_la_misma_empresa(a, b):
    assert _clave(a) == _clave(b)
    assert _clave(a) is not None


@pytest.mark.parametrize("a,b", PARES_DISTINTOS)
def test_clave_no_une_empresas_distintas(a, b):
    assert _clave(a) != _clave(b)


@pytest.mark.parametrize("texto,esperada", [
    ("DISAGRO DE GUATEMALA, S.A", "DISAGRO DE GUATEMALA SA"),
    ("Disagro De Guatemala, Sociedad Anónima", "DISAGRO DE GUATEMALA SA"),
    ("TRIBO SA", "TRIBO SA"),
    ("D'MAIA, S.A", "D'MAIA SA"),                                  # el apóstrofo se conserva
    ("EXPORTADORA ATLANTICO, S.A./ GUATEMALA", "EXPORTADORA ATLANTICO SA / GUATEMALA"),
    ("Empresa sin sufijo", "EMPRESA SIN SUFIJO"),
])
def test_clave_valores_exactos(texto, esperada):
    assert _clave(texto) == esperada


@pytest.mark.parametrize("texto", [None, "", "   ", ".", " , "])
def test_clave_vacia_es_none(texto):
    assert _clave(texto) is None


def test_clave_coincide_con_la_referencia_en_python_para_muchos_nombres():
    nombres = [x for par in PARES_QUE_SE_UNEN + PARES_DISTINTOS for x in par] + [
        "AGROMAR IMPORT & EXPORT OF GUATEMALA, S.A", "Comercial Agropecuaria de Guatemala, S.A. (Coagro Guatemala)",
        "FORMAS Y FERTILIZANTES S.A / FORMULASA", "ORGANISMO INTERNACIONAL REGIONAL DE SANIDAD AGROPECUARIA (OIRSA)",
        "Ñandú Importaciones, S. A.", "Ünica Agrícola, SOCIEDAD ANÓNIMA",
    ]
    with engine.connect() as conn:
        for n in nombres:
            assert clave_empresa(conn, n) == _referencia(n), n


# ---------------------------------------------------------------------------------------------
# Utilidades de prueba
# ---------------------------------------------------------------------------------------------

def _poner_en_catalogo(nombre_variante: str, homologada: str) -> str:
    """Inserta en dbo.CatalogoEmpresas la clave de `nombre_variante` con el nombre homologado dado."""
    clave = _clave(nombre_variante)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dbo.CatalogoEmpresas WHERE EmpresaKey = :k"), {"k": clave})
        conn.execute(
            text("INSERT INTO dbo.CatalogoEmpresas (EmpresaKey, EmpresaHomologada, Confirmada) VALUES (:k, :h, 0)"),
            {"k": clave, "h": homologada},
        )
    return clave


def _limpiar_catalogo(claves: list[str | None]) -> None:
    with engine.begin() as conn:
        for k in claves:
            if k:
                conn.execute(text("DELETE FROM dbo.CatalogoEmpresas WHERE EmpresaKey = :k"), {"k": k})
                conn.execute(text("DELETE FROM dbo.log_ExcepcionesEmpresas WHERE EmpresaKey = :k"), {"k": k})


def _fila_nutrientes(licencia: str, empresa: str, anio: int, cif: str, nombre: str = "PRODUCTO HOMOLOGACION") -> dict:
    return {
        "Tipo": "LICENCIAS", "No_Licencia": licencia, "No_Registro": f"REG-F-{licencia}",
        "NombreComercial": nombre, "EmpresaImportadora": empresa,
        "FechaEmision": f"10/01/{anio}", "UMedida": "Kilogramos", "Cantidad": 10,
        "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia", "AduanadeIngreso": "Puerto A",
        " CIF_dolares ": cif, " CIF_Q ": "Q1.00", " TimbresQ ": "Q1.00",
        "Exportador": "X", "Concentraciones": "X", "Componentes": "N", "VENTANILLA": "MAGA",
    }


def _fila_plaguicidas(recibo: int, importador: str, anio: int, cif: float, producto: str = "PRODUCTO HOMOLOGACION") -> dict:
    return {
        "RECIBO": recibo, "SerieSAT": "S1", "RecSAT": None, "APLICACIoN": "HERBICIDA", "RECIBOSAT": None,
        "FECHA": f"{anio}-01-15", "IMPORTADOR": importador, "PRODUCTO": producto, "INGREDIENTEACT": "GLIFOSATO",
        "EXPORTADOR": "EXPORTADOR PRUEBA", "ORIGEN": "TESTLANDIA", "pct": "10%", "CANTIDAD": 10.0, "UNMEDIDA": "KG",
        "CIFusd": cif, "CIFQ": cif * 7.7, "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 1.0,
    }


def _cargar_nutrientes(client, admin_headers, filas: list[dict], nombre="homologacion.csv"):
    r = client.post(
        "/api/admin/cargas/nutrientes", headers=admin_headers,
        files={"archivo_nutrientes": (nombre, construir_csv_nutrientes(filas), "text/csv")},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _cargar_plaguicidas(client, admin_headers, filas: list[dict]):
    r = client.post(
        "/api/admin/cargas/plaguicidas", headers=admin_headers,
        files={"archivo_importaciones": ("homologacion.xlsx", construir_excel_importaciones(filas))},
    )
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------------------------
# 2) Sincronización con el catálogo
# ---------------------------------------------------------------------------------------------

def test_sincronizar_asigna_la_homologada_sin_tocar_el_original_y_es_idempotente(client, admin_headers):
    anio = 2083
    claves = []
    limpiar_nutrientes_anio(anio)
    limpiar_importacion_anio(anio)
    try:
        # Datos originales con variantes de la misma empresa, cargados SIN catálogo (EmpresaHomologada queda NULL)
        _cargar_nutrientes(client, admin_headers, [
            _fila_nutrientes("1-83", "SYNC PRUEBA, S.A", anio, "$100.00"),
            _fila_nutrientes("2-83", "Sync Prueba, Sociedad Anonima", anio, "$200.00"),
        ])
        _cargar_plaguicidas(client, admin_headers, [_fila_plaguicidas(830001, "SYNC PRUEBA, S. A.", anio, 300.0)])
        with engine.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM dbo.Nutrientes WHERE anio = :a AND EmpresaHomologada IS NOT NULL"), {"a": anio}).scalar() == 0

        claves.append(_poner_en_catalogo("SYNC PRUEBA SA", "Sync Prueba, S.A."))
        with Session(engine) as db:
            assert sincronizar_empresas(db) >= 3
            db.commit()
        with engine.connect() as conn:
            nut = conn.execute(text("SELECT EmpresaImportadora, EmpresaHomologada FROM dbo.Nutrientes WHERE anio = :a ORDER BY No_Licencia"), {"a": anio}).all()
            imp = conn.execute(text("SELECT importador, EmpresaHomologada FROM dbo.Importacion WHERE anio = :a"), {"a": anio}).all()
        assert [f[1] for f in nut] == ["Sync Prueba, S.A."] * 2
        assert [f[0] for f in nut] == ["SYNC PRUEBA, S.A", "Sync Prueba, Sociedad Anonima"]       # originales intactos
        assert imp == [("SYNC PRUEBA, S. A.", "Sync Prueba, S.A.")]

        with Session(engine) as db:
            assert sincronizar_empresas(db) == 0          # segunda corrida: 0 cambios
            db.commit()

        # Si la clave sale del catálogo, la homologada vuelve a NULL (queda sin homologar) y el original sigue igual
        _limpiar_catalogo(claves)
        with Session(engine) as db:
            assert sincronizar_empresas(db) >= 3
            db.commit()
        with engine.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM dbo.Nutrientes WHERE anio = :a AND EmpresaHomologada IS NOT NULL"), {"a": anio}).scalar() == 0
            assert conn.execute(text("SELECT COUNT(*) FROM dbo.Importacion WHERE anio = :a AND EmpresaHomologada IS NOT NULL"), {"a": anio}).scalar() == 0
    finally:
        _limpiar_catalogo(claves)
        _limpiar_catalogo([_clave("SYNC PRUEBA SA")])
        limpiar_nutrientes_anio(anio)
        limpiar_importacion_anio(anio)


# ---------------------------------------------------------------------------------------------
# 3) Cargas mensuales
# ---------------------------------------------------------------------------------------------

def test_carga_nutrientes_rellena_la_homologada_y_registra_empresas_nuevas(client, admin_headers):
    anio = 2082
    limpiar_nutrientes_anio(anio)
    claves = [_poner_en_catalogo("EMPRESA CARGA NUT, S.A.", "Empresa Carga Nut, S.A.")]
    nueva = "EMPRESA NUEVA NUT SIN CATALOGO, S.A."
    claves.append(_clave(nueva))
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM dbo.log_ExcepcionesEmpresas WHERE EmpresaKey = :k"), {"k": claves[1]})
        resumen = _cargar_nutrientes(client, admin_headers, [
            _fila_nutrientes("1-82", "Empresa Carga Nut, Sociedad Anonima", anio, "$100.00"),
            _fila_nutrientes("2-82", nueva, anio, "$50.00"),
            _fila_nutrientes("3-82", "EMPRESA NUEVA NUT SIN CATALOGO, SOCIEDAD ANONIMA", anio, "$25.00"),   # misma empresa nueva
        ])
        assert resumen["empresas_sin_homologar"] == 1       # una EMPRESA nueva (aunque tenga 2 filas)
        with engine.connect() as conn:
            filas = conn.execute(text("SELECT EmpresaImportadora, EmpresaHomologada FROM dbo.Nutrientes WHERE anio = :a ORDER BY No_Licencia"), {"a": anio}).all()
            log = conn.execute(text("SELECT Origen, Filas, CAST(CifUsd AS FLOAT) FROM dbo.log_ExcepcionesEmpresas WHERE EmpresaKey = :k"), {"k": claves[1]}).all()
        assert filas[0] == ("Empresa Carga Nut, Sociedad Anonima", "Empresa Carga Nut, S.A.")     # homologada; original intacto
        assert filas[1][1] is None and filas[2][1] is None                                       # sin homologar
        assert filas[1][0] == nueva
        assert log == [("Nutrientes", 2, 75.0)]
    finally:
        _limpiar_catalogo(claves)
        limpiar_nutrientes_anio(anio)


def test_carga_plaguicidas_rellena_la_homologada_y_registra_empresas_nuevas(client, admin_headers):
    anio = 2081
    limpiar_importacion_anio(anio)
    claves = [_poner_en_catalogo("EMPRESA CARGA PLAG, S.A.", "Empresa Carga Plag, S.A.")]
    nueva = "EMPRESA NUEVA PLAG SIN CATALOGO, S.A."
    claves.append(_clave(nueva))
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM dbo.log_ExcepcionesEmpresas WHERE EmpresaKey = :k"), {"k": claves[1]})
        resumen = _cargar_plaguicidas(client, admin_headers, [
            _fila_plaguicidas(810001, "EMPRESA CARGA PLAG, SOCIEDAD ANONIMA", anio, 100.0),
            _fila_plaguicidas(810002, nueva, anio, 40.0),
        ])
        assert resumen["empresas_sin_homologar"] == 1
        with engine.connect() as conn:
            filas = conn.execute(text("SELECT importador, EmpresaHomologada FROM dbo.Importacion WHERE anio = :a ORDER BY recibointerno"), {"a": anio}).all()
            log = conn.execute(text("SELECT Origen, Filas FROM dbo.log_ExcepcionesEmpresas WHERE EmpresaKey = :k"), {"k": claves[1]}).all()
        assert filas == [("EMPRESA CARGA PLAG, SOCIEDAD ANONIMA", "Empresa Carga Plag, S.A."), (nueva, None)]
        assert log == [("Plaguicidas", 1)]
    finally:
        _limpiar_catalogo(claves)
        limpiar_importacion_anio(anio)


# ---------------------------------------------------------------------------------------------
# 4) Tableros: COALESCE(EmpresaHomologada, original) da los mismos montos
# ---------------------------------------------------------------------------------------------

def _top_nutrientes(client, headers, anio):
    r = client.get("/api/dashboard/nutrientes", headers=headers, params={"anio": anio})
    assert r.status_code == 200, r.text
    d = r.json()
    return {f["etiqueta"]: f["cif_usd"] for f in d["top_empresas_importadoras"]}, d["kpis"]


def test_dashboard_nutrientes_usa_la_empresa_homologada_con_los_mismos_montos(client, admin_headers, usuario_headers):
    anio = 2080
    limpiar_nutrientes_anio(anio)
    claves = []
    try:
        _cargar_nutrientes(client, admin_headers, [
            _fila_nutrientes("1-80", "ALFA PARIDAD, S.A.", anio, "$1,000.00"),
            _fila_nutrientes("2-80", "Alfa Paridad, Sociedad Anonima", anio, "$500.00"),
            _fila_nutrientes("3-80", "BETA PARIDAD, S.A.", anio, "$300.00"),
        ])
        # Sin homologar: se ve cada empresa tal como vino
        top, kpis = _top_nutrientes(client, usuario_headers, anio)
        assert top == {"ALFA PARIDAD, S.A.": 1000.0, "Alfa Paridad, Sociedad Anonima": 500.0, "BETA PARIDAD, S.A.": 300.0}
        assert kpis["empresas"] == 3 and kpis["cif_total_usd"] == 1800.0

        claves.append(_poner_en_catalogo("ALFA PARIDAD SA", "Alfa Paridad, S.A."))
        with Session(engine) as db:
            sincronizar_empresas(db)
            db.commit()
        # Homologada la primera: las dos variantes suman en una barra; BETA (sin catálogo) sigue con su original
        top, kpis = _top_nutrientes(client, usuario_headers, anio)
        assert top == {"Alfa Paridad, S.A.": 1500.0, "BETA PARIDAD, S.A.": 300.0}
        assert kpis["empresas"] == 2
        assert kpis["cif_total_usd"] == 1800.0 and kpis["registros"] == 3          # el monto total NO cambia
        assert sum(top.values()) == kpis["cif_total_usd"]
    finally:
        _limpiar_catalogo(claves)
        with Session(engine) as db:
            sincronizar_empresas(db)
            db.commit()
        limpiar_nutrientes_anio(anio)


def test_dashboard_plaguicidas_usa_la_empresa_homologada_con_los_mismos_montos(client, admin_headers, usuario_headers):
    anio = 2079
    limpiar_importacion_anio(anio)
    claves = []
    try:
        _cargar_plaguicidas(client, admin_headers, [
            _fila_plaguicidas(790001, "GAMMA PARIDAD, S.A.", anio, 1000.0, producto="P1"),
            _fila_plaguicidas(790002, "Gamma Paridad, Sociedad Anonima", anio, 500.0, producto="P1"),
            _fila_plaguicidas(790003, "DELTA PARIDAD, S.A.", anio, 300.0, producto="P2"),
        ])

        def top_y_total():
            r = client.get("/api/dashboard/plaguicidas", headers=usuario_headers, params={"anio": anio})
            assert r.status_code == 200, r.text
            d = r.json()
            return {f["etiqueta"]: f["cif_usd"] for f in d["top_importadores"]}, d["kpis"]

        top, kpis = top_y_total()
        assert top == {"GAMMA PARIDAD, S.A.": 1000.0, "Gamma Paridad, Sociedad Anonima": 500.0, "DELTA PARIDAD, S.A.": 300.0}

        claves.append(_poner_en_catalogo("GAMMA PARIDAD SA", "Gamma Paridad, S.A."))
        with Session(engine) as db:
            sincronizar_empresas(db)
            db.commit()
        top, kpis2 = top_y_total()
        assert top == {"Gamma Paridad, S.A.": 1500.0, "DELTA PARIDAD, S.A.": 300.0}
        assert kpis2["cif_total_usd"] == kpis["cif_total_usd"] == 1800.0 and kpis2["registros"] == 3
    finally:
        _limpiar_catalogo(claves)
        with Session(engine) as db:
            sincronizar_empresas(db)
            db.commit()
        limpiar_importacion_anio(anio)


def test_la_regla_de_duplicados_exactos_de_nutrientes_sigue_usando_la_empresa_original(client, admin_headers, usuario_headers):
    """Dos filas idénticas (misma identidad con la empresa ORIGINAL) son un duplicado exacto: cuenta una sola. Dos filas que
    solo se parecen una vez homologadas (empresa original distinta) NO son duplicado: cuentan las dos."""
    anio = 2078
    limpiar_nutrientes_anio(anio)
    claves = []
    try:
        base = _fila_nutrientes("1-78", "OMEGA PARIDAD, S.A.", anio, "$100.00")
        otra_variante = _fila_nutrientes("1-78", "Omega Paridad, Sociedad Anonima", anio, "$100.00")   # misma licencia, otra variante
        _cargar_nutrientes(client, admin_headers, [base, dict(base), otra_variante])
        claves.append(_poner_en_catalogo("OMEGA PARIDAD SA", "Omega Paridad, S.A."))
        with Session(engine) as db:
            sincronizar_empresas(db)
            db.commit()
        top, kpis = _top_nutrientes(client, usuario_headers, anio)
        # 3 filas cargadas; el duplicado exacto (base repetida) se quita; la variante distinta se conserva: 2 registros
        assert kpis["registros"] == 2
        assert top == {"Omega Paridad, S.A.": 200.0}
    finally:
        _limpiar_catalogo(claves)
        with Session(engine) as db:
            sincronizar_empresas(db)
            db.commit()
        limpiar_nutrientes_anio(anio)

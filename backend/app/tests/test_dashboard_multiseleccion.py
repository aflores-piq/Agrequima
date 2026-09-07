"""Filtros con selección múltiple (semántica OR): Origen, Ingrediente
activo/Nombre comercial (incluyendo el sentinel "Sin agrupador"),
Aplicación/Componente y Producto ahora aceptan varios valores marcados a
la vez. Ver _filtro_grupo / _filtro_producto_agrupado en
dashboard_plaguicidas.py / dashboard_nutrientes.py."""

from sqlalchemy import text

from app.core.db import engine
from app.tests.helpers import (
    construir_csv_nutrientes,
    construir_excel_importaciones,
    limpiar_importacion_anio,
    limpiar_nutrientes_anio,
)

ANIO_PLAGUICIDAS = 2170
ANIO_NUTRIENTES = 2180

CLAVE_A = "INGREDIENTE MULTISEL A"
CLAVE_B = "INGREDIENTE MULTISEL B"
GRUPO_A = "Grupo Multisel A"
GRUPO_B = "Grupo Multisel B"


def _preparar_catalogo_plaguicidas():
    with engine.begin() as conn:
        for clave in (CLAVE_A, CLAVE_B):
            conn.execute(
                text("DELETE FROM dbo.CatalogoNomenclaturaPlaguicidas WHERE IngredienteActivo_Key = :k"),
                {"k": clave},
            )
        conn.execute(
            text(
                "INSERT INTO dbo.CatalogoNomenclaturaPlaguicidas "
                "(IngredienteActivo_Key, Agrupador, Codigo, FechaMod) VALUES "
                "(:ka, :ga, NULL, GETDATE()), (:kb, :gb, NULL, GETDATE())"
            ),
            {"ka": CLAVE_A, "ga": GRUPO_A, "kb": CLAVE_B, "gb": GRUPO_B},
        )


def _fila_plaguicida(recibo: int, ingrediente: str, origen: str, aplicacion: str, producto: str, cif: float) -> dict:
    return {
        "RECIBO": recibo, "SerieSAT": f"S{recibo}", "RecSAT": None, "APLICACIoN": aplicacion,
        "RECIBOSAT": None, "FECHA": f"{ANIO_PLAGUICIDAS}-01-10", "IMPORTADOR": "IMPORTADOR MULTISEL",
        "PRODUCTO": producto, "INGREDIENTEACT": ingrediente, "EXPORTADOR": "E1", "ORIGEN": origen,
        "pct": "10%", "CANTIDAD": 1.0, "UNMEDIDA": "KG", "CIFusd": cif, "CIFQ": cif * 7.7,
        "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 1.0,
    }


def _cargar_plaguicidas_multisel(client, admin_headers):
    limpiar_importacion_anio(ANIO_PLAGUICIDAS)
    _preparar_catalogo_plaguicidas()
    contenido = construir_excel_importaciones(
        [
            _fila_plaguicida(920001, CLAVE_A, "PAIS A", "HERBICIDA", "PRODUCTO MULTISEL A", 100.0),
            _fila_plaguicida(920002, CLAVE_B, "PAIS B", "FUNGICIDA", "PRODUCTO MULTISEL B", 200.0),
            _fila_plaguicida(920003, "INGREDIENTE MULTISEL C SIN CATALOGO", "PAIS C", "INSECTICIDA", "PRODUCTO MULTISEL C", 300.0),
        ]
    )
    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("multisel.xlsx", contenido)},
    )
    assert r.status_code == 200, r.text


def test_plaguicidas_origen_multiple_es_or(client, admin_headers):
    _cargar_plaguicidas_multisel(client, admin_headers)

    r = client.get(
        "/api/dashboard/plaguicidas",
        headers=admin_headers,
        params={"anio": ANIO_PLAGUICIDAS, "mes": 1, "origen": ["PAIS A", "PAIS B"]},
    )
    assert r.status_code == 200, r.text
    kpis = r.json()["kpis"]
    assert kpis["registros"] == 2
    assert kpis["cif_total_usd"] == 300.0  # 100 + 200, PAIS C excluido


def test_plaguicidas_ingrediente_activo_combina_sin_agrupador_con_valor_real(client, admin_headers):
    _cargar_plaguicidas_multisel(client, admin_headers)

    r = client.get(
        "/api/dashboard/plaguicidas",
        headers=admin_headers,
        params={"anio": ANIO_PLAGUICIDAS, "mes": 1, "ingrediente_act": [GRUPO_A, "Sin agrupador"]},
    )
    assert r.status_code == 200, r.text
    kpis = r.json()["kpis"]
    # Grupo A (100) + el ingrediente sin catálogo, Grupo NULL (300) = 400.
    # Grupo B (200) queda excluido: no es "Sin agrupador" ni GRUPO_A.
    assert kpis["registros"] == 2
    assert kpis["cif_total_usd"] == 400.0


def test_plaguicidas_aplicacion_multiple_es_or(client, admin_headers):
    _cargar_plaguicidas_multisel(client, admin_headers)

    r = client.get(
        "/api/dashboard/plaguicidas",
        headers=admin_headers,
        params={"anio": ANIO_PLAGUICIDAS, "mes": 1, "aplicacion": ["Herbicida", "Fungicida"]},
    )
    assert r.status_code == 200, r.text
    kpis = r.json()["kpis"]
    assert kpis["registros"] == 2
    assert kpis["cif_total_usd"] == 300.0  # Herbicida (100) + Fungicida (200)


def test_plaguicidas_producto_multiple_es_or(client, admin_headers):
    _cargar_plaguicidas_multisel(client, admin_headers)

    r = client.get(
        "/api/dashboard/plaguicidas",
        headers=admin_headers,
        params={
            "anio": ANIO_PLAGUICIDAS, "mes": 1,
            "producto": ["PRODUCTO MULTISEL A", "PRODUCTO MULTISEL C"],
        },
    )
    assert r.status_code == 200, r.text
    kpis = r.json()["kpis"]
    assert kpis["registros"] == 2
    assert kpis["cif_total_usd"] == 400.0  # A (100) + C (300)


def test_plaguicidas_multiseleccion_respeta_exportacion(client, admin_headers):
    """El mismo filtro múltiple debe reflejarse en el Excel exportado
    (export.py reutiliza construir_contexto_plaguicidas sin cambios)."""
    _cargar_plaguicidas_multisel(client, admin_headers)

    r = client.get(
        "/api/dashboard/plaguicidas/export/detalle",
        headers=admin_headers,
        params={"anio": ANIO_PLAGUICIDAS, "mes": 1, "origen": ["PAIS A", "PAIS B"]},
    )
    assert r.status_code == 200, r.text

    import io

    import pandas as pd

    df = pd.read_excel(io.BytesIO(r.content))
    assert len(df) == 2
    assert set(df["Origen"]) == {"PAIS A", "PAIS B"}


def _preparar_catalogo_nutrientes():
    with engine.begin() as conn:
        for clave in ("PRODUCTO MULTISEL A NUT", "PRODUCTO MULTISEL B NUT"):
            conn.execute(
                text("DELETE FROM dbo.CatalogoAgrupadorNutrientes WHERE NombreComercial_Key = :k"),
                {"k": clave},
            )
        conn.execute(
            text(
                "INSERT INTO dbo.CatalogoAgrupadorNutrientes "
                "(NombreComercial_Key, ProductoAgrupado, Codigo, FechaMod) VALUES "
                "(:ka, :ga, NULL, GETDATE()), (:kb, :gb, NULL, GETDATE())"
            ),
            {
                "ka": "PRODUCTO MULTISEL A NUT", "ga": "Grupo Nutriente Multisel A",
                "kb": "PRODUCTO MULTISEL B NUT", "gb": "Grupo Nutriente Multisel B",
            },
        )


def _fila_nutriente(licencia: str, nombre_comercial: str, origen: str, componente: str, cif: float) -> dict:
    return {
        "Tipo": "LICENCIAS", "No_Licencia": licencia, "No_Registro": f"REG-F-{licencia}",
        "NombreComercial": nombre_comercial, "EmpresaImportadora": "IMPORTADORA MULTISEL",
        "FechaEmision": f"10/01/{ANIO_NUTRIENTES}", "UMedida": "Kilogramos", "Cantidad": 1,
        "PaisProcedencia": "Testlandia", "PaisOrigen": origen,
        "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": cif,
        " CIF_Q ": cif * 7.7, " TimbresQ ": 1.0, "Exportador": "Exportador Prueba",
        "Concentraciones": "10-10-10", "Componentes": componente, "VENTANILLA": "MAGA",
    }


def _cargar_nutrientes_multisel(client, admin_headers):
    limpiar_nutrientes_anio(ANIO_NUTRIENTES)
    _preparar_catalogo_nutrientes()
    contenido = construir_csv_nutrientes(
        [
            _fila_nutriente("MS-1", "PRODUCTO MULTISEL A NUT", "PAIS NUT A", "NPK", 100.0),
            _fila_nutriente("MS-2", "PRODUCTO MULTISEL B NUT", "PAIS NUT B", "Nitrógeno", 200.0),
            _fila_nutriente("MS-3", "PRODUCTO MULTISEL C NUT SIN CATALOGO", "PAIS NUT C", "Potasio", 300.0),
        ]
    )
    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("multisel.csv", contenido, "text/csv")},
    )
    assert r.status_code == 200, r.text


def test_nutrientes_origen_multiple_es_or(client, admin_headers):
    _cargar_nutrientes_multisel(client, admin_headers)

    r = client.get(
        "/api/dashboard/nutrientes",
        headers=admin_headers,
        params={"anio": ANIO_NUTRIENTES, "mes": 1, "origen": ["PAIS NUT A", "PAIS NUT B"]},
    )
    assert r.status_code == 200, r.text
    kpis = r.json()["kpis"]
    assert kpis["registros"] == 2
    assert kpis["cif_total_usd"] == 300.0


def test_nutrientes_nombre_comercial_combina_sin_agrupador_con_valor_real(client, admin_headers):
    _cargar_nutrientes_multisel(client, admin_headers)

    r = client.get(
        "/api/dashboard/nutrientes",
        headers=admin_headers,
        params={
            "anio": ANIO_NUTRIENTES, "mes": 1,
            "nombre_comercial": ["Grupo Nutriente Multisel A", "Sin agrupador"],
        },
    )
    assert r.status_code == 200, r.text
    kpis = r.json()["kpis"]
    assert kpis["registros"] == 2
    assert kpis["cif_total_usd"] == 400.0  # A (100) + sin catálogo (300)


def test_nutrientes_componente_multiple_es_or(client, admin_headers):
    _cargar_nutrientes_multisel(client, admin_headers)

    r = client.get(
        "/api/dashboard/nutrientes",
        headers=admin_headers,
        params={"anio": ANIO_NUTRIENTES, "mes": 1, "componente": ["NPK", "Potasio"]},
    )
    assert r.status_code == 200, r.text
    kpis = r.json()["kpis"]
    assert kpis["registros"] == 2
    assert kpis["cif_total_usd"] == 400.0  # NPK (100) + Potasio (300)

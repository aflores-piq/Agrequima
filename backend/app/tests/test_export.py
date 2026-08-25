import io

import pandas as pd

from app.services import export as export_service
from app.tests.helpers import construir_csv_nutrientes, construir_excel_importaciones

ANIO_PRUEBA = 2092
IMPORTADOR_MARCADOR = "IMPORTADOR EXPORT PRUEBA"
EMPRESA_MARCADOR = "EMPRESA EXPORT PRUEBA"
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _cargar_plaguicidas_prueba(client, admin_headers):
    contenido = construir_excel_importaciones(
        [
            {
                "RECIBO": 1, "SerieSAT": "S1", "RecSAT": None, "APLICACIoN": "HERBICIDA",
                "RECIBOSAT": None, "FECHA": f"{ANIO_PRUEBA}-01-10", "IMPORTADOR": IMPORTADOR_MARCADOR,
                "PRODUCTO": "PE1", "INGREDIENTEACT": "GLIFOSATO", "EXPORTADOR": "E1", "ORIGEN": "MEXICO",
                "pct": "10%", "CANTIDAD": 10.0, "UNMEDIDA": "KG", "CIFusd": 1000.0, "CIFQ": 7700.0,
                "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 1.0,
            },
            {
                "RECIBO": 2, "SerieSAT": "S2", "RecSAT": None, "APLICACIoN": "FUNGICIDA",
                "RECIBOSAT": None, "FECHA": f"{ANIO_PRUEBA}-03-05", "IMPORTADOR": IMPORTADOR_MARCADOR,
                "PRODUCTO": "PE2", "INGREDIENTEACT": "MANCOZEB", "EXPORTADOR": "E2", "ORIGEN": "CHINA",
                "pct": "25%", "CANTIDAD": 20.0, "UNMEDIDA": "KG", "CIFusd": 2000.0, "CIFQ": 15400.0,
                "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 1.0,
            },
        ]
    )
    r = client.post(
        "/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("export_test.xlsx", contenido)},
    )
    assert r.status_code == 200, r.text


def _cargar_nutrientes_prueba(client, admin_headers):
    contenido = construir_csv_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "LE1", "No_Registro": "RE1",
                "NombreComercial": "PRODUCTO EXPORT 1", "EmpresaImportadora": EMPRESA_MARCADOR,
                "FechaEmision": f"10/01/{ANIO_PRUEBA}", "UMedida": "Kilogramos", "Cantidad": 100,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia", "AduanadeIngreso": "Puerto Export",
                " CIF_dolares ": "$1,000.00", " CIF_Q ": "Q7,700.00", " TimbresQ ": "Q10.00",
                "Exportador": "X", "Concentraciones": "X", "Componentes": "X", "VENTANILLA": "MAGA",
            },
        ]
    )
    r = client.post(
        "/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("export_test.csv", contenido, "text/csv")},
    )
    assert r.status_code == 200, r.text


def _leer_hoja(response_content: bytes, **kwargs):
    return pd.read_excel(io.BytesIO(response_content), **kwargs)


# --- require_export_permission ---


def test_require_export_permission_rechaza_usuario_sin_permiso(client, admin_headers, usuario_headers):
    _cargar_plaguicidas_prueba(client, admin_headers)
    r = client.get(
        "/dashboard/plaguicidas/export/top-paises",
        headers=usuario_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r.status_code == 403


def test_require_export_permission_permite_administrador(client, admin_headers):
    r = client.get(
        "/dashboard/plaguicidas/export/top-paises",
        headers=admin_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX_CONTENT_TYPE


def test_require_export_permission_es_por_usuario_no_por_rol(
    client, usuario_exportador_headers, admin_sin_exportar_headers
):
    """El permiso ya no depende del rol: un Usuario con PuedeExportar=1
    debe poder exportar, y un Administrador con PuedeExportar=0 no."""
    r_usuario_exportador = client.get(
        "/dashboard/plaguicidas/export/top-paises",
        headers=usuario_exportador_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r_usuario_exportador.status_code == 200
    assert r_usuario_exportador.headers["content-type"] == XLSX_CONTENT_TYPE

    r_admin_sin_exportar = client.get(
        "/dashboard/plaguicidas/export/top-paises",
        headers=admin_sin_exportar_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r_admin_sin_exportar.status_code == 403


def test_require_export_permission_requiere_autenticacion(client):
    r = client.get("/dashboard/plaguicidas/export/top-paises", params={"anio": ANIO_PRUEBA})
    assert r.status_code == 401


# --- Plaguicidas ---


def test_exportar_plaguicidas_elemento_desconocido_404(client, admin_headers):
    r = client.get(
        "/dashboard/plaguicidas/export/no-existe",
        headers=admin_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r.status_code == 404


def test_exportar_plaguicidas_detalle_coincide_con_lo_cargado(client, admin_headers):
    r = client.get(
        "/dashboard/plaguicidas/export/detalle",
        headers=admin_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX_CONTENT_TYPE
    assert f"plaguicidas_detalle_{ANIO_PRUEBA}.xlsx" in r.headers["content-disposition"]

    df = _leer_hoja(r.content)
    assert len(df) == 2
    assert set(df["Importador"]) == {IMPORTADOR_MARCADOR}
    assert "Ingrediente activo" in df.columns  # encabezado en español, no el nombre interno


def test_exportar_plaguicidas_todo_trae_una_hoja_por_elemento(client, admin_headers):
    r = client.get(
        "/dashboard/plaguicidas/export-todo",
        headers=admin_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX_CONTENT_TYPE

    hojas = _leer_hoja(r.content, sheet_name=None)
    assert len(hojas) == len(export_service.PLAGUICIDAS_ELEMENTOS)
    assert "Detalle de transacciones" in hojas
    assert len(hojas["Detalle de transacciones"]) == 2


# --- Nutrientes ---


def test_exportar_nutrientes_elemento_desconocido_404(client, admin_headers):
    r = client.get(
        "/dashboard/nutrientes/export/no-existe",
        headers=admin_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r.status_code == 404


def test_exportar_nutrientes_detalle_coincide_con_lo_cargado(client, admin_headers):
    _cargar_nutrientes_prueba(client, admin_headers)
    r = client.get(
        "/dashboard/nutrientes/export/detalle",
        headers=admin_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r.status_code == 200
    assert f"nutrientes_detalle_{ANIO_PRUEBA}.xlsx" in r.headers["content-disposition"]

    df = _leer_hoja(r.content)
    assert len(df) == 1
    assert df.iloc[0]["Empresa importadora"] == EMPRESA_MARCADOR


def test_exportar_nutrientes_todo_trae_una_hoja_por_elemento(client, admin_headers):
    r = client.get(
        "/dashboard/nutrientes/export-todo",
        headers=admin_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r.status_code == 200
    hojas = _leer_hoja(r.content, sheet_name=None)
    assert len(hojas) == len(export_service.NUTRIENTES_ELEMENTOS)


def test_require_export_permission_rechaza_usuario_en_nutrientes(client, usuario_headers):
    r = client.get(
        "/dashboard/nutrientes/export/detalle",
        headers=usuario_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r.status_code == 403

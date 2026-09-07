from sqlalchemy import text

from app.core.db import engine
from app.tests.helpers import construir_csv_nutrientes, construir_excel_importaciones

ANIO_PRUEBA = 2091
IMPORTADOR_MARCADOR = "IMPORTADOR DASHBOARD PRUEBA"
EMPRESA_MARCADOR = "EMPRESA DASHBOARD PRUEBA"


def test_dashboard_plaguicidas_requiere_autenticacion(client):
    assert client.get("/api/dashboard/plaguicidas").status_code == 401


def test_dashboard_plaguicidas_kpis_coinciden_con_suma_directa(client, admin_headers, usuario_headers):
    contenido = construir_excel_importaciones(
        [
            {
                "RECIBO": 1, "SerieSAT": "S1", "RecSAT": None, "APLICACIoN": "HERBICIDA",
                "RECIBOSAT": None, "FECHA": f"{ANIO_PRUEBA}-01-10", "IMPORTADOR": IMPORTADOR_MARCADOR,
                "PRODUCTO": "P1", "INGREDIENTEACT": "GLIFOSATO", "EXPORTADOR": "E1", "ORIGEN": "MEXICO",
                "pct": "10%", "CANTIDAD": 10.0, "UNMEDIDA": "KG", "CIFusd": 1234.56, "CIFQ": 9506.11,
                "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 1.0,
            },
            {
                "RECIBO": 2, "SerieSAT": "S2", "RecSAT": None, "APLICACIoN": "FUNGICIDA",
                "RECIBOSAT": None, "FECHA": f"{ANIO_PRUEBA}-03-05", "IMPORTADOR": IMPORTADOR_MARCADOR,
                "PRODUCTO": "P2", "INGREDIENTEACT": "MANCOZEB", "EXPORTADOR": "E2", "ORIGEN": "CHINA",
                "pct": "25%", "CANTIDAD": 20.0, "UNMEDIDA": "KG", "CIFusd": 2500.0, "CIFQ": 19250.0,
                "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 1.0,
            },
        ]
    )
    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("dashboard_test.xlsx", contenido)},
    )
    assert r.status_code == 200, r.text

    r_dashboard = client.get(
        "/api/dashboard/plaguicidas",
        headers=usuario_headers,  # cualquier usuario autenticado, no solo Administrador
        # ANIO_PRUEBA ya es exclusivo de este archivo de pruebas, así que
        # basta como aislamiento (no hay filtro de Importador: el reporte
        # real de Power BI no lo tiene, ver docs/legacy/referencia-dashboards/).
        params={"anio": ANIO_PRUEBA},
    )
    assert r_dashboard.status_code == 200, r_dashboard.text
    kpis = r_dashboard.json()["kpis"]

    with engine.connect() as conn:
        fila = conn.execute(
            text("SELECT SUM(cif_USD), SUM(cif_Q), COUNT(*) FROM dbo.Importacion WHERE anio = :anio"),
            {"anio": ANIO_PRUEBA},
        ).one()
    suma_directa_usd, suma_directa_q, conteo_directo = fila

    assert kpis["cif_total_usd"] == round(float(suma_directa_usd), 2)
    assert kpis["cif_total_q"] == round(float(suma_directa_q), 2)
    assert kpis["registros"] == conteo_directo


def test_dashboard_nutrientes_kpis_coinciden_con_suma_directa(client, admin_headers, usuario_headers):
    contenido = construir_csv_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "L1", "No_Registro": "RF1",
                "NombreComercial": "PRODUCTO DASHBOARD 1", "EmpresaImportadora": EMPRESA_MARCADOR,
                "FechaEmision": f"10/01/{ANIO_PRUEBA}", "UMedida": "Kilogramos", "Cantidad": 100,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia", "AduanadeIngreso": "Puerto A",
                " CIF_dolares ": "$1,234.56", " CIF_Q ": "Q9,506.11", " TimbresQ ": "Q10.00",
                "Exportador": "X", "Concentraciones": "X", "Componentes": "X", "VENTANILLA": "MAGA",
            },
            {
                "Tipo": "LICENCIAS", "No_Licencia": "L2", "No_Registro": "RF2",
                "NombreComercial": "PRODUCTO DASHBOARD 2", "EmpresaImportadora": EMPRESA_MARCADOR,
                "FechaEmision": f"15/06/{ANIO_PRUEBA}", "UMedida": "Litros", "Cantidad": 50,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia", "AduanadeIngreso": "Puerto B",
                " CIF_dolares ": "$2,500.00", " CIF_Q ": "Q19,250.00", " TimbresQ ": "Q5.00",
                "Exportador": "X", "Concentraciones": "X", "Componentes": "X", "VENTANILLA": "MAGA",
            },
        ]
    )
    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("dashboard_test.csv", contenido, "text/csv")},
    )
    assert r.status_code == 200, r.text

    r_dashboard = client.get(
        "/api/dashboard/nutrientes",
        headers=usuario_headers,
        params={"anio": ANIO_PRUEBA},
    )
    assert r_dashboard.status_code == 200, r_dashboard.text
    kpis = r_dashboard.json()["kpis"]

    with engine.connect() as conn:
        fila = conn.execute(
            text("SELECT SUM(CIF_dolares), SUM(CIF_Q), COUNT(*) FROM dbo.Nutrientes WHERE anio = :anio"),
            {"anio": ANIO_PRUEBA},
        ).one()
    suma_directa_usd, suma_directa_q, conteo_directo = fila

    assert kpis["cif_total_usd"] == round(float(suma_directa_usd), 2)
    assert kpis["cif_total_q"] == round(float(suma_directa_q), 2)
    assert kpis["registros"] == conteo_directo

from sqlalchemy import text

from app.core.db import engine
from app.tests.helpers import (
    construir_csv_importaciones,
    construir_excel_hoja_ambigua,
    construir_excel_importaciones,
    construir_excel_nomenclatura,
    limpiar_importacion_anio,
)

# Año dedicado a este archivo de pruebas: cada archivo de pruebas usa un
# año distinto para no pisar los datos de otro. usp_CargarImportacion ya
# no hace DELETE + INSERT por año (ver "solo cargar el mes nuevo"), así
# que cada test limpia su propio año antes de cargar.
ANIO_PRUEBA = 2090


def test_carga_plaguicidas_happy_path(client, admin_headers):
    limpiar_importacion_anio(ANIO_PRUEBA)
    contenido = construir_excel_importaciones(
        [
            {
                "RECIBO": 900001, "SerieSAT": "S1", "RecSAT": None, "APLICACIoN": "HERBICIDA",
                "RECIBOSAT": None, "FECHA": f"{ANIO_PRUEBA}-01-15", "IMPORTADOR": "IMPORTADOR PRUEBA",
                "PRODUCTO": "PRODUCTO PRUEBA", "INGREDIENTEACT": "GLIFOSATO", "EXPORTADOR": "EXPORTADOR PRUEBA",
                "ORIGEN": "TESTLANDIA", "pct": "10% + 40%", "CANTIDAD": 10.0, "UNMEDIDA": "KG",
                "CIFusd": 1000.0, "CIFQ": 7700.0, "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 5.0,
            },
            {
                "RECIBO": 900002, "SerieSAT": "S" * 100, "RecSAT": None, "APLICACIoN": "FUNGICIDA",
                "RECIBOSAT": None, "FECHA": f"{ANIO_PRUEBA}-02-20", "IMPORTADOR": "IMPORTADOR PRUEBA",
                "PRODUCTO": "PRODUCTO PRUEBA 2", "INGREDIENTEACT": "INGREDIENTE INEXISTENTE EN CATALOGO",
                "EXPORTADOR": "EXPORTADOR PRUEBA", "ORIGEN": "TESTLANDIA", "pct": "25%",
                "CANTIDAD": 5.0, "UNMEDIDA": "LITROS", "CIFusd": 500.0, "CIFQ": 3850.0,
                "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 2.0,
            },
        ]
    )

    nomenclatura = construir_excel_nomenclatura(
        [{"ingrediente": "GLIFOSATO", "agrupador": "Glifosato", "codigo": "IA-TEST"}]
    )

    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={
            "archivo_importaciones": (
                "test.xlsx", contenido,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            "archivo_nomenclatura": ("nomenclatura.xlsx", nomenclatura),
        },
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 2
    assert data["anios"] == [ANIO_PRUEBA]
    assert data["filas_truncadas"] == 1  # SerieSAT de 100 caracteres > límite de 70
    assert data["combos_porcentaje"] == 1  # "10% + 40%"
    assert data["nomenclatura_actualizada"] is True
    assert data["filas_sin_agrupador"] == 1  # solo el ingrediente inventado queda sin agrupador
    assert data["estado"] == "ConExcepciones"

    with engine.connect() as conn:
        filas_bd = conn.execute(
            text("SELECT COUNT(*) FROM dbo.Importacion WHERE anio = :anio"), {"anio": ANIO_PRUEBA}
        ).scalar()
    assert filas_bd == 2


def test_carga_plaguicidas_requiere_rol_administrador(client, usuario_headers):
    contenido = construir_excel_importaciones(
        [
            {
                "RECIBO": 1, "SerieSAT": "S", "RecSAT": None, "APLICACIoN": "HERBICIDA",
                "RECIBOSAT": None, "FECHA": "2091-01-01", "IMPORTADOR": "X", "PRODUCTO": "X",
                "INGREDIENTEACT": "X", "EXPORTADOR": "X", "ORIGEN": "X", "pct": "10%",
                "CANTIDAD": 1.0, "UNMEDIDA": "KG", "CIFusd": 1.0, "CIFQ": 1.0, "CAMBIO": 7.7,
                "Empresa": "X", "UMSP": 1.0,
            }
        ]
    )
    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=usuario_headers,
        files={"archivo_importaciones": ("test.xlsx", contenido)},
    )
    assert r.status_code == 403


def test_carga_plaguicidas_extension_invalida(client, admin_headers):
    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("test.txt", b"esto no es un excel")},
    )
    assert r.status_code == 400


def test_carga_plaguicidas_acepta_csv(client, admin_headers):
    anio_csv = 2093
    limpiar_importacion_anio(anio_csv)
    contenido = construir_csv_importaciones(
        [
            {
                # Fecha con día <= 12 para probar dayfirst=True (si se
                # interpretara mes-primero, esto caería en mayo, no enero).
                "RECIBO": 700001, "SerieSAT": "S1", "RecSAT": None, "APLICACIoN": "HERBICIDA",
                "RECIBOSAT": None, "FECHA": f"05/01/{anio_csv}", "IMPORTADOR": "IMPORTADOR CSV",
                "PRODUCTO": "PRODUCTO CSV", "INGREDIENTEACT": "CLORPIRIFOS", "EXPORTADOR": "EXPORTADOR CSV",
                "ORIGEN": "TESTLANDIA", "pct": "0.1%", "CANTIDAD": "14,250.00", "UNMEDIDA": "LITROS",
                "CIFusd": "$97,612.50", "CIFQ": "Q748,234.95", "CAMBIO": "7.66536",
                "Empresa": "Agrequima", "UMSP": "Q3,367.06",
            }
        ]
    )

    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("real.csv", contenido, "text/csv")},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 1
    assert data["anios"] == [anio_csv]

    with engine.connect() as conn:
        fila = conn.execute(
            text(
                "SELECT fecha, cantidad, cif_USD, cif_Q, umsp FROM dbo.Importacion "
                "WHERE anio = :anio"
            ),
            {"anio": anio_csv},
        ).one()
    fecha, cantidad, cif_usd, cif_q, umsp = fila

    assert fecha == f"{anio_csv}/01/05"  # confirma que se interpretó dayfirst, no mes-primero
    assert float(cantidad) == 14250.00
    assert float(cif_usd) == 97612.50
    assert float(cif_q) == 748234.95
    assert float(umsp) == 3367.06


def test_carga_plaguicidas_titulo_extra_arriba_del_encabezado_xlsx(client, admin_headers):
    """Mismo bug que en nutrientes: una fila de título (y filas en
    blanco) antes del encabezado real no debe leerse como encabezado."""
    anio = 2085
    limpiar_importacion_anio(anio)
    contenido = construir_excel_importaciones(
        [
            {
                "RECIBO": 800001, "SerieSAT": "S1", "RecSAT": None, "APLICACIoN": "HERBICIDA",
                "RECIBOSAT": None, "FECHA": f"{anio}-01-15", "IMPORTADOR": "IMPORTADOR CON TITULO",
                "PRODUCTO": "PRODUCTO CON TITULO", "INGREDIENTEACT": "GLIFOSATO",
                "EXPORTADOR": "EXPORTADOR PRUEBA", "ORIGEN": "TESTLANDIA", "pct": "10%",
                "CANTIDAD": 10.0, "UNMEDIDA": "KG", "CIFusd": 1000.0, "CIFQ": 7700.0,
                "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 5.0,
            },
        ],
        titulo=f"Consolidado importaciones de plaguicidas {anio}",
    )

    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={
            "archivo_importaciones": (
                "con_titulo.xlsx", contenido,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 1
    assert data["anios"] == [anio]

    with engine.connect() as conn:
        fila = conn.execute(
            text("SELECT importador, cif_USD FROM dbo.Importacion WHERE anio = :anio"),
            {"anio": anio},
        ).one()
    assert fila.importador == "IMPORTADOR CON TITULO"
    assert float(fila.cif_USD) == 1000.0


def test_carga_plaguicidas_titulo_extra_arriba_del_encabezado_csv(client, admin_headers):
    anio = 2084
    limpiar_importacion_anio(anio)
    contenido = construir_csv_importaciones(
        [
            {
                "RECIBO": 800002, "SerieSAT": "S1", "RecSAT": None, "APLICACIoN": "HERBICIDA",
                "RECIBOSAT": None, "FECHA": f"05/01/{anio}", "IMPORTADOR": "IMPORTADOR CON TITULO CSV",
                "PRODUCTO": "PRODUCTO CON TITULO CSV", "INGREDIENTEACT": "CLORPIRIFOS",
                "EXPORTADOR": "EXPORTADOR PRUEBA", "ORIGEN": "TESTLANDIA", "pct": "0.1%",
                "CANTIDAD": "10.00", "UNMEDIDA": "LITROS", "CIFusd": "$1,000.00",
                "CIFQ": "Q7,700.00", "CAMBIO": "7.7", "Empresa": "Agrequima", "UMSP": "5.00",
            },
        ],
        titulo=f"Consolidado importaciones de plaguicidas {anio}",
    )

    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("con_titulo.csv", contenido, "text/csv")},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 1
    assert data["anios"] == [anio]

    with engine.connect() as conn:
        fila = conn.execute(
            text("SELECT importador, cif_USD FROM dbo.Importacion WHERE anio = :anio"),
            {"anio": anio},
        ).one()
    assert fila.importador == "IMPORTADOR CON TITULO CSV"
    assert float(fila.cif_USD) == 1000.0


def test_carga_plaguicidas_hoja_ambigua_queda_en_auditoria(client, admin_headers):
    contenido = construir_excel_hoja_ambigua()

    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("ambiguo.xlsx", contenido)},
    )
    assert r.status_code == 400
    assert "hoja" in r.json()["detail"].lower()

    with engine.connect() as conn:
        estado = conn.execute(
            text(
                "SELECT TOP 1 Estado FROM dbo.AuditoriaCargas "
                "WHERE NombreArchivo = 'ambiguo.xlsx' ORDER BY CargaId DESC"
            )
        ).scalar()
    assert estado == "Error"


def _fila_plaguicida(recibo: int, anio: int, mes: int, dia: int) -> dict:
    return {
        "RECIBO": recibo, "SerieSAT": f"S{recibo}", "RecSAT": None, "APLICACIoN": "HERBICIDA",
        "RECIBOSAT": None, "FECHA": f"{anio}-{mes:02d}-{dia:02d}", "IMPORTADOR": "IMPORTADOR ACUMULADO",
        "PRODUCTO": "PRODUCTO ACUMULADO", "INGREDIENTEACT": "GLIFOSATO", "EXPORTADOR": "EXPORTADOR PRUEBA",
        "ORIGEN": "TESTLANDIA", "pct": "10%", "CANTIDAD": 1.0, "UNMEDIDA": "KG",
        "CIFusd": 100.0, "CIFQ": 770.0, "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 1.0,
    }


def test_carga_plaguicidas_solo_carga_el_mes_nuevo(client, admin_headers):
    """Simula el caso real: un archivo acumulado del año trae de nuevo los
    meses que ya se habían cargado antes, más los meses nuevos — solo
    estos últimos deben insertarse, sin duplicar ni fallar por los que ya
    estaban."""
    anio = 2094
    limpiar_importacion_anio(anio)

    primer_archivo = construir_excel_importaciones(
        [
            _fila_plaguicida(910001, anio, 1, 10),
            _fila_plaguicida(910002, anio, 2, 10),
        ]
    )
    r1 = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("mes1_2.xlsx", primer_archivo)},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["filas_cargadas"] == 2
    assert r1.json()["meses_nuevos"] == [1, 2]
    assert r1.json()["filas_ya_cargadas"] == 0

    archivo_acumulado = construir_excel_importaciones(
        [
            _fila_plaguicida(910001, anio, 1, 10),
            _fila_plaguicida(910002, anio, 2, 10),
            _fila_plaguicida(910003, anio, 3, 10),
            _fila_plaguicida(910004, anio, 4, 10),
            _fila_plaguicida(910005, anio, 5, 10),
        ]
    )
    r2 = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("acumulado_1_a_5.xlsx", archivo_acumulado)},
    )
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert data2["filas_cargadas"] == 3  # solo marzo, abril y mayo
    assert data2["meses_nuevos"] == [3, 4, 5]
    assert data2["filas_ya_cargadas"] == 2  # enero y febrero, ignorados sin error

    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM dbo.Importacion WHERE anio = :anio"), {"anio": anio}
        ).scalar()
        meses = conn.execute(
            text(
                "SELECT DISTINCT CAST(SUBSTRING(fecha, 6, 2) AS INT) FROM dbo.Importacion "
                "WHERE anio = :anio ORDER BY 1"
            ),
            {"anio": anio},
        ).scalars().all()
    assert total == 5  # no se duplicaron enero/febrero
    assert meses == [1, 2, 3, 4, 5]

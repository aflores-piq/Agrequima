from sqlalchemy import text

from app.core.db import engine
from app.tests.helpers import (
    construir_csv_nutrientes,
    construir_excel_nutrientes,
    limpiar_nutrientes_anio,
)

ANIO_PRUEBA = 2090  # ver comentario equivalente en test_cargas_plaguicidas.py
ANIO_PRUEBA_XLSX = 2089


def test_carga_nutrientes_happy_path(client, admin_headers):
    limpiar_nutrientes_anio(ANIO_PRUEBA)
    contenido = construir_csv_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "1-90", "No_Registro": "REG-F-1",
                "NombreComercial": "UREA PRUEBA", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"15/01/{ANIO_PRUEBA}", "UMedida": "Kilogramos", "Cantidad": 100,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": "$1,000.00",
                " CIF_Q ": "Q7,700.00", " TimbresQ ": "Q10.00", "Exportador": "Exportador Prueba",
                "Concentraciones": "46-0-0", "Componentes": "N", "VENTANILLA": "MAGA",
            },
            {
                "Tipo": "LICENCIAS", "No_Licencia": "2-90", "No_Registro": "REG-F-2",
                "NombreComercial": "PRODUCTO SIN AGRUPADOR EN CATALOGO", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"20/02/{ANIO_PRUEBA}", "UMedida": "Litros", "Cantidad": 50,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": "$500.00",
                " CIF_Q ": "Q3,850.00", " TimbresQ ": "Q5.00", "Exportador": "Exportador Prueba",
                "Concentraciones": "10-10-10", "Componentes": "NPK", "VENTANILLA": "MAGA",
            },
        ]
    )

    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("test.csv", contenido, "text/csv")},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 2
    assert data["anios"] == [ANIO_PRUEBA]
    assert data["filas_sin_agrupador"] == 2  # catálogo vacío en la BD de pruebas
    assert data["estado"] == "ConExcepciones"

    with engine.connect() as conn:
        filas_bd = conn.execute(
            text("SELECT COUNT(*) FROM dbo.Nutrientes WHERE anio = :anio"), {"anio": ANIO_PRUEBA}
        ).scalar()
        cif_bd = conn.execute(
            text("SELECT SUM(CIF_dolares) FROM dbo.Nutrientes WHERE anio = :anio"), {"anio": ANIO_PRUEBA}
        ).scalar()
    assert filas_bd == 2
    assert float(cif_bd) == 1500.0


def test_carga_nutrientes_mapea_tipo_punto_y_vacio_a_licencias(client, admin_headers):
    """Tipo="." (o vacío) significa "Licencias" -- confirmado por el
    cliente, ya no es un valor ambiguo que haya que dejar tal cual."""
    anio = 2093
    limpiar_nutrientes_anio(anio)
    contenido = construir_csv_nutrientes(
        [
            {
                "Tipo": ".", "No_Licencia": "1-93", "No_Registro": "REG-F-1",
                "NombreComercial": "PRODUCTO TIPO PUNTO", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"10/01/{anio}", "UMedida": "Kilogramos", "Cantidad": 10,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": "$100.00",
                " CIF_Q ": "Q770.00", " TimbresQ ": "Q1.00", "Exportador": "Exportador Prueba",
                "Concentraciones": "10-10-10", "Componentes": "NPK", "VENTANILLA": "MAGA",
            },
            {
                "Tipo": "PERMISOS", "No_Licencia": "2-93", "No_Registro": "REG-F-2",
                "NombreComercial": "PRODUCTO TIPO NORMAL", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"12/01/{anio}", "UMedida": "Kilogramos", "Cantidad": 20,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": "$200.00",
                " CIF_Q ": "Q1540.00", " TimbresQ ": "Q2.00", "Exportador": "Exportador Prueba",
                "Concentraciones": "10-10-10", "Componentes": "NPK", "VENTANILLA": "MAGA",
            },
        ]
    )

    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("test_tipo.csv", contenido, "text/csv")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["filas_cargadas"] == 2

    with engine.connect() as conn:
        filas = conn.execute(
            text("SELECT NombreComercial, Tipo FROM dbo.Nutrientes WHERE anio = :anio ORDER BY NombreComercial"),
            {"anio": anio},
        ).all()
    por_nombre = {f.NombreComercial: f.Tipo for f in filas}
    assert por_nombre["PRODUCTO TIPO PUNTO"] == "Licencias"
    assert por_nombre["PRODUCTO TIPO NORMAL"] == "PERMISOS"  # no se toca lo que ya venía distinto de "."


def test_carga_nutrientes_descarta_filas_sin_f_en_no_registro(client, admin_headers):
    """Filtro permanente: solo se cargan filas cuyo No_Registro contiene
    la letra "F" -- las demás se descartan en silencio, y el conteo
    queda visible en el resumen de la carga."""
    anio = 2094
    limpiar_nutrientes_anio(anio)
    contenido = construir_csv_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "1-94", "No_Registro": "_100-F-1-1",
                "NombreComercial": "PRODUCTO CON F", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"05/03/{anio}", "UMedida": "Kilogramos", "Cantidad": 10,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": "$100.00",
                " CIF_Q ": "Q770.00", " TimbresQ ": "Q1.00", "Exportador": "Exportador Prueba",
                "Concentraciones": "10-10-10", "Componentes": "NPK", "VENTANILLA": "MAGA",
            },
            {
                "Tipo": "LICENCIAS", "No_Licencia": "2-94", "No_Registro": "_100-ENMIENDA-1-1",
                "NombreComercial": "PRODUCTO SIN F", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"06/03/{anio}", "UMedida": "Kilogramos", "Cantidad": 20,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": "$200.00",
                " CIF_Q ": "Q1540.00", " TimbresQ ": "Q2.00", "Exportador": "Exportador Prueba",
                "Concentraciones": "10-10-10", "Componentes": "NPK", "VENTANILLA": "MAGA",
            },
        ]
    )

    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("test_no_registro.csv", contenido, "text/csv")},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 1
    assert data["filas_descartadas_sin_f"] == 1

    with engine.connect() as conn:
        nombres = [
            row[0]
            for row in conn.execute(
                text("SELECT NombreComercial FROM dbo.Nutrientes WHERE anio = :anio"), {"anio": anio}
            ).all()
        ]
    assert nombres == ["PRODUCTO CON F"]


def test_carga_nutrientes_happy_path_xlsx(client, admin_headers):
    """Mismo caso feliz que el .csv, pero subiendo un .xlsx con las
    celdas ya tipadas (fecha real, montos numéricos) — confirma que el
    endpoint ya no rechaza este formato."""
    limpiar_nutrientes_anio(ANIO_PRUEBA_XLSX)
    contenido = construir_excel_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "1-89", "No_Registro": "REG-F-1",
                "NombreComercial": "UREA PRUEBA XLSX", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"15/01/{ANIO_PRUEBA_XLSX}", "UMedida": "Kilogramos", "Cantidad": 100,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": 1000.0,
                " CIF_Q ": 7700.0, " TimbresQ ": 10.0, "Exportador": "Exportador Prueba",
                "Concentraciones": "46-0-0", "Componentes": "N", "VENTANILLA": "MAGA",
            },
            {
                "Tipo": "LICENCIAS", "No_Licencia": "2-89", "No_Registro": "REG-F-2",
                "NombreComercial": "PRODUCTO SIN AGRUPADOR EN CATALOGO", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"20/02/{ANIO_PRUEBA_XLSX}", "UMedida": "Litros", "Cantidad": 50,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": 500.0,
                " CIF_Q ": 3850.0, " TimbresQ ": 5.0, "Exportador": "Exportador Prueba",
                "Concentraciones": "10-10-10", "Componentes": "NPK", "VENTANILLA": "MAGA",
            },
        ]
    )

    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={
            "archivo_nutrientes": (
                "test.xlsx", contenido,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 2
    assert data["anios"] == [ANIO_PRUEBA_XLSX]

    with engine.connect() as conn:
        filas_bd = conn.execute(
            text("SELECT COUNT(*) FROM dbo.Nutrientes WHERE anio = :anio"), {"anio": ANIO_PRUEBA_XLSX}
        ).scalar()
        cif_bd = conn.execute(
            text("SELECT SUM(CIF_dolares) FROM dbo.Nutrientes WHERE anio = :anio"), {"anio": ANIO_PRUEBA_XLSX}
        ).scalar()
    assert filas_bd == 2
    assert float(cif_bd) == 1500.0


def test_carga_nutrientes_xlsx_fecha_como_texto_no_invierte_dia_mes(client, admin_headers):
    """Reproduce el bug real (carga del 2026-08-27, CargaId 19, 260 filas
    con fecha invertida): un .xlsx puede traer la celda de FechaEmision
    como texto "DD/MM/YYYY" aunque la columna se vea formateada como
    Fecha en Excel — si se deja que pandas adivine el formato, interpreta
    MM/DD/YYYY e invierte día/mes (12/05 -> 5 de diciembre en vez de 12
    de mayo). No debe pasar."""
    anio = 2088
    limpiar_nutrientes_anio(anio)
    contenido = construir_excel_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "500-88", "No_Registro": "REG-F-1",
                "NombreComercial": "PRODUCTO FECHA TEXTO", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"12/05/{anio}", "UMedida": "Kilogramos", "Cantidad": 100,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": 1000.0,
                " CIF_Q ": 7700.0, " TimbresQ ": 10.0, "Exportador": "Exportador Prueba",
                "Concentraciones": "46-0-0", "Componentes": "N", "VENTANILLA": "MAGA",
            },
            {
                "Tipo": "LICENCIAS", "No_Licencia": "501-88", "No_Registro": "REG-F-2",
                "NombreComercial": "PRODUCTO FECHA TEXTO DIA31", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"31/01/{anio}", "UMedida": "Litros", "Cantidad": 50,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": 500.0,
                " CIF_Q ": 3850.0, " TimbresQ ": 5.0, "Exportador": "Exportador Prueba",
                "Concentraciones": "10-10-10", "Componentes": "NPK", "VENTANILLA": "MAGA",
            },
        ],
        fecha_como_texto=True,
    )

    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={
            "archivo_nutrientes": (
                "test_fecha_texto.xlsx", contenido,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert r.status_code == 200, r.text
    assert r.json()["filas_cargadas"] == 2

    with engine.connect() as conn:
        filas = conn.execute(
            text(
                "SELECT NombreComercial, FechaEmision FROM dbo.Nutrientes "
                "WHERE anio = :anio ORDER BY NombreComercial"
            ),
            {"anio": anio},
        ).all()
    por_nombre = {f.NombreComercial: f.FechaEmision for f in filas}
    assert por_nombre["PRODUCTO FECHA TEXTO"].isoformat() == f"{anio}-05-12"
    assert por_nombre["PRODUCTO FECHA TEXTO DIA31"].isoformat() == f"{anio}-01-31"


def test_carga_nutrientes_titulo_extra_arriba_del_encabezado_csv(client, admin_headers):
    """Reproduce el bug real: el archivo trae una fila de título (y filas
    en blanco) antes del encabezado real, ej. "Consolidado Licencias de
    Importación 2023 al mes de diciembre" — no debe leerse esa fila como
    si fueran los encabezados."""
    anio = 2087
    limpiar_nutrientes_anio(anio)
    contenido = construir_csv_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "1-87", "No_Registro": "REG-F-1",
                "NombreComercial": "PRODUCTO CON TITULO CSV", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"15/01/{anio}", "UMedida": "Kilogramos", "Cantidad": 100,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": "$1,000.00",
                " CIF_Q ": "Q7,700.00", " TimbresQ ": "Q10.00", "Exportador": "Exportador Prueba",
                "Concentraciones": "46-0-0", "Componentes": "N", "VENTANILLA": "MAGA",
            },
        ],
        titulo=f"Consolidado Licencias de Importación {anio} al mes de diciembre",
    )

    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("con_titulo.csv", contenido, "text/csv")},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filas_cargadas"] == 1
    assert data["anios"] == [anio]

    with engine.connect() as conn:
        fila = conn.execute(
            text("SELECT NombreComercial, CIF_dolares FROM dbo.Nutrientes WHERE anio = :anio"),
            {"anio": anio},
        ).one()
    assert fila.NombreComercial == "PRODUCTO CON TITULO CSV"
    assert float(fila.CIF_dolares) == 1000.0


def test_carga_nutrientes_titulo_extra_arriba_del_encabezado_xlsx(client, admin_headers):
    anio = 2086
    limpiar_nutrientes_anio(anio)
    contenido = construir_excel_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "1-86", "No_Registro": "REG-F-1",
                "NombreComercial": "PRODUCTO CON TITULO XLSX", "EmpresaImportadora": "IMPORTADORA PRUEBA",
                "FechaEmision": f"15/01/{anio}", "UMedida": "Kilogramos", "Cantidad": 100,
                "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
                "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": 1000.0,
                " CIF_Q ": 7700.0, " TimbresQ ": 10.0, "Exportador": "Exportador Prueba",
                "Concentraciones": "46-0-0", "Componentes": "N", "VENTANILLA": "MAGA",
            },
        ],
        titulo=f"Consolidado Licencias de Importación {anio} al mes de diciembre",
    )

    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={
            "archivo_nutrientes": (
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
            text("SELECT NombreComercial, CIF_dolares FROM dbo.Nutrientes WHERE anio = :anio"),
            {"anio": anio},
        ).one()
    assert fila.NombreComercial == "PRODUCTO CON TITULO XLSX"
    assert float(fila.CIF_dolares) == 1000.0


def test_carga_nutrientes_requiere_rol_administrador(client, usuario_headers):
    contenido = construir_csv_nutrientes(
        [
            {
                "Tipo": "LICENCIAS", "No_Licencia": "X", "No_Registro": "XF", "NombreComercial": "X",
                "EmpresaImportadora": "X", "FechaEmision": "01/01/2091", "UMedida": "Kilogramos",
                "Cantidad": 1, "PaisProcedencia": "X", "PaisOrigen": "X", "AduanadeIngreso": "X",
                " CIF_dolares ": "$1.00", " CIF_Q ": "Q1.00", " TimbresQ ": "Q1.00",
                "Exportador": "X", "Concentraciones": "X", "Componentes": "X", "VENTANILLA": "X",
            }
        ]
    )
    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=usuario_headers,
        files={"archivo_nutrientes": ("test.csv", contenido, "text/csv")},
    )
    assert r.status_code == 403


def test_carga_nutrientes_extension_invalida(client, admin_headers):
    # .xlsx ya es válido (ver test_carga_nutrientes_happy_path_xlsx); una
    # extensión realmente no soportada como .txt debe seguir rechazándose.
    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("test.txt", b"esto no es un csv ni un excel")},
    )
    assert r.status_code == 400
    assert "csv" in r.json()["detail"].lower() and "excel" in r.json()["detail"].lower()


def test_carga_nutrientes_columnas_faltantes(client, admin_headers):
    contenido = b"Tipo;No_Licencia\nLICENCIAS;1\n"
    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("incompleto.csv", contenido, "text/csv")},
    )
    assert r.status_code == 400
    assert "columnas" in r.json()["detail"].lower()


def _fila_nutriente(licencia: str, anio: int, mes: int, dia: int) -> dict:
    return {
        "Tipo": "LICENCIAS", "No_Licencia": licencia, "No_Registro": f"REG-F-{licencia}",
        "NombreComercial": "PRODUCTO ACUMULADO", "EmpresaImportadora": "IMPORTADORA PRUEBA",
        "FechaEmision": f"{dia:02d}/{mes:02d}/{anio}", "UMedida": "Kilogramos", "Cantidad": 1,
        "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia",
        "AduanadeIngreso": "Puerto Prueba", " CIF_dolares ": "$100.00",
        " CIF_Q ": "Q770.00", " TimbresQ ": "Q1.00", "Exportador": "Exportador Prueba",
        "Concentraciones": "10-10-10", "Componentes": "NPK", "VENTANILLA": "MAGA",
    }


def test_carga_nutrientes_solo_carga_el_mes_nuevo(client, admin_headers):
    """Igual que el caso equivalente en test_cargas_plaguicidas.py: un
    archivo acumulado que repite meses ya cargados solo debe insertar los
    meses realmente nuevos, sin duplicar los anteriores."""
    anio = 2095
    limpiar_nutrientes_anio(anio)

    primer_archivo = construir_csv_nutrientes(
        [
            _fila_nutriente("1-95", anio, 1, 10),
            _fila_nutriente("2-95", anio, 2, 10),
        ]
    )
    r1 = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("mes1_2.csv", primer_archivo, "text/csv")},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["filas_cargadas"] == 2
    assert r1.json()["meses_nuevos"] == [1, 2]
    assert r1.json()["filas_ya_cargadas"] == 0

    archivo_acumulado = construir_csv_nutrientes(
        [
            _fila_nutriente("1-95", anio, 1, 10),
            _fila_nutriente("2-95", anio, 2, 10),
            _fila_nutriente("3-95", anio, 3, 10),
            _fila_nutriente("4-95", anio, 4, 10),
            _fila_nutriente("5-95", anio, 5, 10),
        ]
    )
    r2 = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("acumulado_1_a_5.csv", archivo_acumulado, "text/csv")},
    )
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert data2["filas_cargadas"] == 3  # solo marzo, abril y mayo
    assert data2["meses_nuevos"] == [3, 4, 5]
    assert data2["filas_ya_cargadas"] == 2  # enero y febrero, ignorados sin error

    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM dbo.Nutrientes WHERE anio = :anio"), {"anio": anio}
        ).scalar()
        meses = conn.execute(
            text(
                "SELECT DISTINCT MONTH(FechaEmision) FROM dbo.Nutrientes "
                "WHERE anio = :anio ORDER BY 1"
            ),
            {"anio": anio},
        ).scalars().all()
    assert total == 5  # no se duplicaron enero/febrero
    assert meses == [1, 2, 3, 4, 5]

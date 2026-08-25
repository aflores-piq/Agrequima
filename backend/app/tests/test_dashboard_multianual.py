"""Comparativo acumulado de CIF USD por año (gráfica multianual): año
seleccionado + hasta 4 anteriores, solo los que tengan datos, todos
cortados en el mismo mes ('Hasta el mes'). Ver df_acumulado_multianual
en dashboard_plaguicidas.py / dashboard_nutrientes.py."""

import io

import pandas as pd
from sqlalchemy import text

from app.core.db import engine
from app.tests.helpers import (
    construir_csv_nutrientes,
    construir_excel_importaciones,
    limpiar_importacion_anio,
    limpiar_nutrientes_anio,
)

# Bloque de años dedicado a estos tests (2100-2160), sin traslape con
# ningún otro archivo de pruebas. Cada test limpia sus propios años antes
# de cargar (ver comentario equivalente en test_cargas_plaguicidas.py):
# usp_CargarImportacion/usp_CargarNutrientes ya no hacen DELETE + INSERT
# por año.
IMPORTADOR_MARCADOR = "IMPORTADOR MULTIANUAL PRUEBA"
EMPRESA_MARCADOR = "EMPRESA MULTIANUAL PRUEBA"


def _fila_plaguicidas(anio: int, mes: int, cif_usd: float, recibo: int) -> dict:
    return {
        "RECIBO": recibo, "SerieSAT": "S1", "RecSAT": None, "APLICACIoN": "HERBICIDA",
        "RECIBOSAT": None, "FECHA": f"{anio}-{mes:02d}-10", "IMPORTADOR": IMPORTADOR_MARCADOR,
        "PRODUCTO": "P1", "INGREDIENTEACT": "GLIFOSATO", "EXPORTADOR": "E1", "ORIGEN": "MEXICO",
        "pct": "10%", "CANTIDAD": 10.0, "UNMEDIDA": "KG", "CIFusd": cif_usd, "CIFQ": cif_usd * 7.7,
        "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 1.0,
    }


def _cargar_plaguicidas(client, admin_headers, filas: list[dict]):
    contenido = construir_excel_importaciones(filas)
    r = client.post(
        "/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("multianual.xlsx", contenido)},
    )
    assert r.status_code == 200, r.text


def _series_por_anio(comparativo: list[dict]) -> dict[int, list[dict]]:
    return {serie["anio"]: serie["puntos"] for serie in comparativo}


def test_multianual_dos_anios_con_datos(client, admin_headers, usuario_headers):
    anio_actual = 2100
    limpiar_importacion_anio(anio_actual)
    limpiar_importacion_anio(anio_actual - 1)
    _cargar_plaguicidas(
        client, admin_headers,
        [
            _fila_plaguicidas(anio_actual, 1, 100.0, 5000001),
            _fila_plaguicidas(anio_actual, 2, 200.0, 5000002),
            _fila_plaguicidas(anio_actual - 1, 1, 50.0, 5000003),
            _fila_plaguicidas(anio_actual - 1, 2, 60.0, 5000004),
        ],
    )

    r = client.get(
        "/dashboard/plaguicidas",
        headers=usuario_headers,
        params={"anio": anio_actual, "mes": 2},
    )
    assert r.status_code == 200, r.text
    comparativo = r.json()["comparativo_acumulado_multianual"]

    # Solo 2 líneas: el año seleccionado y el anterior. 2049-4..2046 no
    # tienen ninguna fila, así que no deben aparecer (ni en cero).
    anios_presentes = [serie["anio"] for serie in comparativo]
    assert anios_presentes == [anio_actual, anio_actual - 1]

    series = _series_por_anio(comparativo)
    assert [p["mes"] for p in series[anio_actual]] == [1, 2]
    assert series[anio_actual][0]["cif_usd_acumulado"] == 100.0
    assert series[anio_actual][1]["cif_usd_acumulado"] == 300.0  # 100 + 200

    assert [p["mes"] for p in series[anio_actual - 1]] == [1, 2]
    assert series[anio_actual - 1][0]["cif_usd_acumulado"] == 50.0
    assert series[anio_actual - 1][1]["cif_usd_acumulado"] == 110.0  # 50 + 60


def test_multianual_tres_anios_con_datos(client, admin_headers):
    anio_actual = 2110
    limpiar_importacion_anio(anio_actual)
    limpiar_importacion_anio(anio_actual - 1)
    limpiar_importacion_anio(anio_actual - 2)
    _cargar_plaguicidas(
        client, admin_headers,
        [
            _fila_plaguicidas(anio_actual, 1, 10.0, 5000010),
            _fila_plaguicidas(anio_actual - 1, 1, 20.0, 5000011),
            _fila_plaguicidas(anio_actual - 2, 1, 30.0, 5000012),
        ],
    )

    r = client.get("/dashboard/plaguicidas", headers=admin_headers, params={"anio": anio_actual, "mes": 1})
    assert r.status_code == 200, r.text
    comparativo = r.json()["comparativo_acumulado_multianual"]

    assert [serie["anio"] for serie in comparativo] == [anio_actual, anio_actual - 1, anio_actual - 2]
    assert all(len(serie["puntos"]) == 1 for serie in comparativo)


def test_multianual_ningun_anio_de_la_ventana_tiene_datos_previos(client, admin_headers):
    """Si solo el año seleccionado tiene datos (los 4 anteriores no),
    debe devolver una sola línea, no 5 ni una lista vacía."""
    anio_actual = 2120
    limpiar_importacion_anio(anio_actual)
    _cargar_plaguicidas(client, admin_headers, [_fila_plaguicidas(anio_actual, 1, 10.0, 5000020)])

    r = client.get("/dashboard/plaguicidas", headers=admin_headers, params={"anio": anio_actual, "mes": 1})
    assert r.status_code == 200, r.text
    comparativo = r.json()["comparativo_acumulado_multianual"]
    assert [serie["anio"] for serie in comparativo] == [anio_actual]


def test_multianual_respeta_el_mes_seleccionado_no_el_maximo_de_otros_anios(client, admin_headers):
    """El año anterior tiene datos hasta junio, pero 'Hasta el mes' está
    en marzo: la línea de ese año debe cortarse en marzo igual que la
    del año seleccionado, no extenderse hasta junio."""
    anio_actual = 2130
    limpiar_importacion_anio(anio_actual)
    limpiar_importacion_anio(anio_actual - 1)
    _cargar_plaguicidas(
        client, admin_headers,
        [
            _fila_plaguicidas(anio_actual, 1, 10.0, 5000030),
            _fila_plaguicidas(anio_actual, 3, 10.0, 5000031),
            _fila_plaguicidas(anio_actual - 1, 1, 100.0, 5000032),
            _fila_plaguicidas(anio_actual - 1, 6, 999.0, 5000033),  # fuera del corte de mes=3
        ],
    )

    r = client.get("/dashboard/plaguicidas", headers=admin_headers, params={"anio": anio_actual, "mes": 3})
    assert r.status_code == 200, r.text
    comparativo = r.json()["comparativo_acumulado_multianual"]
    series = _series_por_anio(comparativo)

    # Ambas series llegan exactamente hasta el mes 3, ninguna hasta el 6.
    assert [p["mes"] for p in series[anio_actual]] == [1, 2, 3]
    assert [p["mes"] for p in series[anio_actual - 1]] == [1, 2, 3]
    # El acumulado del año anterior en el mes 3 NO debe incluir los 999
    # de junio (que quedan fuera del corte de mes seleccionado).
    assert series[anio_actual - 1][-1]["cif_usd_acumulado"] == 100.0


def test_multianual_respeta_filtros_activos(client, admin_headers):
    """Con un filtro de Grupo (agrupador) que no coincide con ninguna fila
    del año anterior, ese año no debe aparecer aunque tenga datos sin
    filtrar. El filtro de "Ingrediente activo" del dashboard filtra por
    Importacion.Grupo, así que la fila de prueba necesita su propia
    entrada de catálogo para tener un Grupo asignado (independiente de lo
    que otros archivos de prueba hayan cargado en el catálogo)."""
    anio_actual = 2140
    limpiar_importacion_anio(anio_actual)
    limpiar_importacion_anio(anio_actual - 1)

    clave_ingrediente = "INGREDIENTE MULTIANUAL FILTRO"
    grupo = "Grupo Multianual Filtro"
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM dbo.CatalogoNomenclaturaPlaguicidas WHERE IngredienteActivo_Key = :k"),
            {"k": clave_ingrediente},
        )
        conn.execute(
            text(
                "INSERT INTO dbo.CatalogoNomenclaturaPlaguicidas "
                "(IngredienteActivo_Key, Agrupador, Codigo, FechaMod) "
                "VALUES (:k, :a, NULL, GETDATE())"
            ),
            {"k": clave_ingrediente, "a": grupo},
        )

    contenido = construir_excel_importaciones(
        [
            {
                **_fila_plaguicidas(anio_actual, 1, 10.0, 5000040),
                "INGREDIENTEACT": clave_ingrediente,
            },
            {
                **_fila_plaguicidas(anio_actual - 1, 1, 20.0, 5000041),
                "INGREDIENTEACT": "OTRO INGREDIENTE SIN AGRUPADOR",
            },
        ]
    )
    r = client.post(
        "/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("multianual_filtro.xlsx", contenido)},
    )
    assert r.status_code == 200, r.text

    r_dashboard = client.get(
        "/dashboard/plaguicidas",
        headers=admin_headers,
        params={"anio": anio_actual, "mes": 1, "ingrediente_act": grupo},
    )
    assert r_dashboard.status_code == 200, r_dashboard.text
    comparativo = r_dashboard.json()["comparativo_acumulado_multianual"]
    assert [serie["anio"] for serie in comparativo] == [anio_actual]


def test_multianual_nutrientes_dos_anios_con_datos(client, admin_headers):
    anio_actual = 2150
    limpiar_nutrientes_anio(anio_actual)
    limpiar_nutrientes_anio(anio_actual - 1)

    def _fila(anio, mes, cif, licencia):
        return {
            "Tipo": "LICENCIAS", "No_Licencia": licencia, "No_Registro": "REG-1",
            "NombreComercial": "PRODUCTO MULTIANUAL", "EmpresaImportadora": EMPRESA_MARCADOR,
            "FechaEmision": f"10/{mes:02d}/{anio}", "UMedida": "Kilogramos", "Cantidad": 100,
            "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia", "AduanadeIngreso": "Puerto A",
            " CIF_dolares ": cif, " CIF_Q ": cif * 7.7, " TimbresQ ": 10.0,
            "Exportador": "X", "Concentraciones": "X", "Componentes": "X", "VENTANILLA": "MAGA",
        }

    contenido = construir_csv_nutrientes(
        [
            _fila(anio_actual, 1, 100.0, "M1"),
            _fila(anio_actual - 1, 1, 40.0, "M2"),
        ]
    )
    r = client.post(
        "/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("multianual.csv", contenido, "text/csv")},
    )
    assert r.status_code == 200, r.text

    r_dashboard = client.get(
        "/dashboard/nutrientes", headers=admin_headers, params={"anio": anio_actual, "mes": 1}
    )
    assert r_dashboard.status_code == 200, r_dashboard.text
    comparativo = r_dashboard.json()["comparativo_acumulado_multianual"]
    assert [serie["anio"] for serie in comparativo] == [anio_actual, anio_actual - 1]


def test_exportar_acumulado_multianual_plaguicidas(client, admin_headers):
    anio_actual = 2160
    limpiar_importacion_anio(anio_actual)
    limpiar_importacion_anio(anio_actual - 1)
    _cargar_plaguicidas(
        client, admin_headers,
        [
            _fila_plaguicidas(anio_actual, 1, 10.0, 5000050),
            _fila_plaguicidas(anio_actual - 1, 1, 20.0, 5000051),
        ],
    )

    r = client.get(
        "/dashboard/plaguicidas/export/acumulado-multianual",
        headers=admin_headers,
        params={"anio": anio_actual, "mes": 1},
    )
    assert r.status_code == 200, r.text
    df = pd.read_excel(io.BytesIO(r.content))
    assert list(df.columns) == ["Mes", f"CIF USD {anio_actual}", f"CIF USD {anio_actual - 1}"]
    assert len(df) == 1


def test_exportar_acumulado_multianual_requiere_permiso(client, usuario_headers):
    r = client.get(
        "/dashboard/plaguicidas/export/acumulado-multianual",
        headers=usuario_headers,
        params={"anio": 2160, "mes": 1},
    )
    assert r.status_code == 403

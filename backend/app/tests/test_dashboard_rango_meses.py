"""Selectores de mes 'Desde' / 'Hasta' de los dashboards de Plaguicidas y
Nutrientes: `mes` sigue siendo el 'Hasta' y `mes_desde` (opcional, por
defecto 1) acota el inicio del rango. Ver normalizar_rango_meses /
filtrar_rango_meses en services/df_utils.py."""

import io

import pandas as pd

from app.services.df_utils import meses_del_rango, normalizar_rango_meses
from app.tests.helpers import (
    construir_csv_nutrientes,
    construir_excel_importaciones,
    limpiar_importacion_anio,
    limpiar_nutrientes_anio,
)

ANIO_PLAGUICIDAS = 2190
ANIO_NUTRIENTES = 2200
CIF_POR_MES = {1: 1.0, 2: 10.0, 3: 100.0, 4: 1000.0, 5: 10000.0, 6: 100000.0}


def _fila_plaguicidas(anio: int, mes: int, cif_usd: float, recibo: int) -> dict:
    return {
        "RECIBO": recibo, "SerieSAT": "S1", "RecSAT": None, "APLICACIoN": "HERBICIDA",
        "RECIBOSAT": None, "FECHA": f"{anio}-{mes:02d}-10", "IMPORTADOR": "IMPORTADOR RANGO PRUEBA",
        "PRODUCTO": "P1", "INGREDIENTEACT": "GLIFOSATO", "EXPORTADOR": "E1", "ORIGEN": "MEXICO",
        "pct": "10%", "CANTIDAD": 10.0, "UNMEDIDA": "KG", "CIFusd": cif_usd, "CIFQ": cif_usd * 7.7,
        "CAMBIO": 7.7, "Empresa": "Agrequima", "UMSP": 1.0,
    }


def _cargar_plaguicidas_rango(client, admin_headers):
    """Un registro por mes (enero-junio) con CIF = potencias de 10, de modo
    que cada suma parcial identifica exactamente qué meses entraron."""
    limpiar_importacion_anio(ANIO_PLAGUICIDAS)
    limpiar_importacion_anio(ANIO_PLAGUICIDAS - 1)
    filas = [_fila_plaguicidas(ANIO_PLAGUICIDAS, m, cif, 5100000 + m) for m, cif in CIF_POR_MES.items()]
    filas.append(_fila_plaguicidas(ANIO_PLAGUICIDAS - 1, 3, 7.0, 5100100))  # año anterior, marzo
    r = client.post(
        "/api/admin/cargas/plaguicidas",
        headers=admin_headers,
        files={"archivo_importaciones": ("rango.xlsx", construir_excel_importaciones(filas))},
    )
    assert r.status_code == 200, r.text


def _dashboard_plaguicidas(client, headers, **params):
    r = client.get("/api/dashboard/plaguicidas", headers=headers, params={"anio": ANIO_PLAGUICIDAS, **params})
    assert r.status_code == 200, r.text
    return r.json()


def test_normalizar_rango_meses():
    assert normalizar_rango_meses(None, 8) == (1, 8)
    assert normalizar_rango_meses(4, 6) == (4, 6)
    assert normalizar_rango_meses(6, 6) == (6, 6)
    # Desde posterior al Hasta: el Desde se ajusta al Hasta.
    assert normalizar_rango_meses(9, 6) == (6, 6)
    assert list(meses_del_rango(4, 6)) == [4, 5, 6]


def test_plaguicidas_sin_mes_desde_es_igual_a_enero(client, admin_headers):
    _cargar_plaguicidas_rango(client, admin_headers)
    sin_param = _dashboard_plaguicidas(client, admin_headers, mes=6)
    con_enero = _dashboard_plaguicidas(client, admin_headers, mes=6, mes_desde=1)
    assert sin_param["mes_desde"] == 1
    assert sin_param["kpis"]["cif_total_usd"] == 111111.0
    assert sin_param == con_enero


def test_plaguicidas_trimestre_es_suma_de_los_meses(client, admin_headers):
    _cargar_plaguicidas_rango(client, admin_headers)
    trimestre = _dashboard_plaguicidas(client, admin_headers, mes_desde=4, mes=6)
    por_mes = [
        _dashboard_plaguicidas(client, admin_headers, mes_desde=m, mes=m)["kpis"]["cif_total_usd"]
        for m in (4, 5, 6)
    ]
    assert por_mes == [1000.0, 10000.0, 100000.0]
    assert trimestre["kpis"]["cif_total_usd"] == sum(por_mes) == 111000.0
    assert trimestre["kpis"]["registros"] == 3
    assert trimestre["mes_desde"] == 4 and trimestre["mes_seleccionado"] == 6
    # Los gráficos mensuales muestran solo los meses del rango y el
    # acumulado arranca en el mes Desde.
    assert [p["mes"] for p in trimestre["comparacion_mensual"]] == [4, 5, 6]
    acumulado = [p["cif_usd_actual_acumulado"] for p in trimestre["comparacion_acumulada_mensual"]]
    assert acumulado == [1000.0, 11000.0, 111000.0]
    serie_actual = next(s for s in trimestre["comparativo_acumulado_multianual"] if s["anio"] == ANIO_PLAGUICIDAS)
    assert [p["mes"] for p in serie_actual["puntos"]] == [4, 5, 6]


def test_plaguicidas_rango_aplica_tambien_al_anio_anterior_y_al_detalle(client, admin_headers):
    _cargar_plaguicidas_rango(client, admin_headers)
    # El único registro del año anterior es de marzo: fuera de Abril-Junio.
    fuera = _dashboard_plaguicidas(client, admin_headers, mes_desde=4, mes=6)
    assert all(p["cif_usd_anterior"] == 0 for p in fuera["comparacion_mensual"])
    # Con Marzo incluido sí entra, y el detalle de transacciones también se acota.
    dentro = _dashboard_plaguicidas(client, admin_headers, mes_desde=3, mes=3)
    assert [p["cif_usd_anterior"] for p in dentro["comparacion_mensual"]] == [7.0]
    assert dentro["detalle"]["total"] == 1
    assert dentro["detalle"]["filas"][0]["cif_usd"] == 100.0


def test_plaguicidas_desde_posterior_a_hasta_se_ajusta_solo(client, admin_headers):
    _cargar_plaguicidas_rango(client, admin_headers)
    ajustado = _dashboard_plaguicidas(client, admin_headers, mes_desde=9, mes=5)
    un_mes = _dashboard_plaguicidas(client, admin_headers, mes_desde=5, mes=5)
    assert ajustado["mes_desde"] == 5
    assert ajustado == un_mes
    assert ajustado["kpis"]["cif_total_usd"] == 10000.0


def test_plaguicidas_mes_desde_fuera_de_rango_es_rechazado(client, admin_headers):
    r = client.get("/api/dashboard/plaguicidas", headers=admin_headers, params={"mes_desde": 13})
    assert r.status_code == 422


def test_plaguicidas_exportacion_respeta_el_rango(client, admin_headers):
    _cargar_plaguicidas_rango(client, admin_headers)
    r = client.get(
        "/api/dashboard/plaguicidas/export/comparativo-mensual",
        headers=admin_headers,
        params={"anio": ANIO_PLAGUICIDAS, "mes_desde": 4, "mes": 6},
    )
    assert r.status_code == 200, r.text
    df = pd.read_excel(io.BytesIO(r.content))
    assert len(df) == 3
    assert df.iloc[:, 0].tolist() == [4, 5, 6]


def test_nutrientes_rango_trimestre_y_ajuste_de_invalidos(client, admin_headers):
    limpiar_nutrientes_anio(ANIO_NUTRIENTES)
    limpiar_nutrientes_anio(ANIO_NUTRIENTES - 1)

    def _fila(mes, cif, licencia):
        return {
            "Tipo": "LICENCIAS", "No_Licencia": licencia, "No_Registro": "REG-F-1",
            "NombreComercial": "PRODUCTO RANGO", "EmpresaImportadora": "EMPRESA RANGO PRUEBA",
            "FechaEmision": f"10/{mes:02d}/{ANIO_NUTRIENTES}", "UMedida": "Kilogramos", "Cantidad": 100,
            "PaisProcedencia": "Testlandia", "PaisOrigen": "Testlandia", "AduanadeIngreso": "Puerto A",
            " CIF_dolares ": cif, " CIF_Q ": cif * 7.7, " TimbresQ ": 10.0,
            "Exportador": "X", "Concentraciones": "X", "Componentes": "X", "VENTANILLA": "MAGA",
        }

    contenido = construir_csv_nutrientes([_fila(m, cif, f"R{m}") for m, cif in CIF_POR_MES.items()])
    r = client.post(
        "/api/admin/cargas/nutrientes",
        headers=admin_headers,
        files={"archivo_nutrientes": ("rango.csv", contenido, "text/csv")},
    )
    assert r.status_code == 200, r.text

    def consultar(**params):
        r = client.get(
            "/api/dashboard/nutrientes", headers=admin_headers, params={"anio": ANIO_NUTRIENTES, **params}
        )
        assert r.status_code == 200, r.text
        return r.json()

    assert consultar(mes=6)["kpis"]["cif_total_usd"] == consultar(mes=6, mes_desde=1)["kpis"]["cif_total_usd"] == 111111.0
    trimestre = consultar(mes_desde=4, mes=6)
    por_mes = [consultar(mes_desde=m, mes=m)["kpis"]["cif_total_usd"] for m in (4, 5, 6)]
    assert trimestre["kpis"]["cif_total_usd"] == sum(por_mes) == 111000.0
    assert [p["mes"] for p in trimestre["comparacion_mensual"]] == [4, 5, 6]
    ajustado = consultar(mes_desde=9, mes=5)
    assert ajustado["mes_desde"] == 5 and ajustado["kpis"]["cif_total_usd"] == 10000.0

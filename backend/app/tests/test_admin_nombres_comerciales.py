"""Homologación de nombres comerciales (/api/admin/nombres-comerciales/{plaguicidas|nutrientes}): permisos, unir, renombrar,
separar, confirmar, nuevos sin homologar, Excel estándar y reflejo en los tableros sin que cambien filas ni CIF.

Cada prueba usa su propio año de prueba y limpia lo que crea en los catálogos."""

from io import BytesIO

import pandas as pd
import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.core.db import engine
from app.services.homologacion_catalogo import CONFIG_NUTRIENTES, CONFIG_PLAGUICIDAS, _claves_de
from app.services.nombres_comerciales import sincronizar_nombres_plaguicidas
from app.services.sincronizacion_agrupador import sincronizar_agrupador_nutrientes
from app.tests.helpers import limpiar_importacion_anio, limpiar_nutrientes_anio
from app.tests.test_homologacion_empresas import (
    _cargar_nutrientes,
    _cargar_plaguicidas,
    _fila_nutrientes,
    _fila_plaguicidas,
)

P = "/api/admin/nombres-comerciales/plaguicidas"
N = "/api/admin/nombres-comerciales/nutrientes"


def _clave_p(nombre: str) -> str:
    with Session(engine) as db:
        return _claves_de(db, CONFIG_PLAGUICIDAS, [nombre])[nombre]


def _clave_n(nombre: str) -> str:
    with Session(engine) as db:
        return _claves_de(db, CONFIG_NUTRIENTES, [nombre])[nombre]


def _limpiar_p(claves: list[str], anios: list[int]) -> None:
    with engine.begin() as conn:
        for k in claves:
            conn.execute(text("DELETE FROM dbo.CatalogoNombresComerciales WHERE NombreKey = :k"), {"k": k})
            conn.execute(text("DELETE FROM dbo.log_ExcepcionesNombresComerciales WHERE NombreKey = :k"), {"k": k})
    for a in anios:
        limpiar_importacion_anio(a)
    with Session(engine) as db:
        sincronizar_nombres_plaguicidas(db)
        db.commit()


def _limpiar_n(claves: list[str], anios: list[int]) -> None:
    for a in anios:
        limpiar_nutrientes_anio(a)
    with engine.begin() as conn:
        for k in claves:
            conn.execute(text("DELETE FROM dbo.CatalogoAgrupadorNutrientes WHERE NombreComercial_Key = :k"), {"k": k})
    with Session(engine) as db:
        sincronizar_agrupador_nutrientes(db)
        db.commit()


def _totales() -> tuple:
    with engine.connect() as conn:
        imp = conn.execute(text("SELECT COUNT(*), CAST(SUM(CAST(cif_USD AS FLOAT)) AS FLOAT) FROM dbo.Importacion")).one()
        nut = conn.execute(text("SELECT COUNT(*), CAST(SUM(CAST(CIF_dolares AS FLOAT)) AS FLOAT) FROM dbo.Nutrientes")).one()
    return (imp[0], round(imp[1] or 0, 2), nut[0], round(nut[1] or 0, 2))


def _productos_originales(anio: int) -> list:
    with engine.connect() as conn:
        return [r[0] for r in conn.execute(text("SELECT producto FROM dbo.Importacion WHERE anio = :a ORDER BY recibointerno"), {"a": anio})]


def _tabla_nombres(client, headers, anio) -> dict:
    r = client.get("/api/dashboard/plaguicidas", headers=headers, params={"anio": anio})
    assert r.status_code == 200, r.text
    d = r.json()
    por_nombre: dict[str, float] = {}
    for f in d["tabla_nombres_comerciales"]:
        por_nombre[f["producto"]] = round(por_nombre.get(f["producto"], 0) + f["cif_usd"], 2)
    return por_nombre


def _top_formulas(client, headers, anio) -> dict:
    r = client.get("/api/dashboard/nutrientes", headers=headers, params={"anio": anio})
    assert r.status_code == 200, r.text
    return {f["etiqueta"]: f["cif_usd"] for f in r.json()["top_formulas"]}


def _excel(filas: list[tuple]) -> bytes:
    buf = BytesIO()
    pd.DataFrame(filas, columns=["Nombre comercial", "Nombre estándar"]).to_excel(buf, index=False)
    return buf.getvalue()


# ---------------------------------------------------------------------------------------------

ENDPOINTS = [
    ("get", "/grupos", None),
    ("get", "/nuevos-sin-homologar", None),
    ("post", "/unir", {"claves": ["A", "B"], "nombre_oficial": "X"}),
    ("put", "/renombrar", {"nombre_actual": "A", "nombre_nuevo": "B"}),
    ("post", "/separar", {"clave": "A"}),
    ("post", "/confirmar", {"nombres": ["A"]}),
    ("post", "/confirmar-pendientes", {}),
    ("post", "/nuevos-sin-homologar/asignar", {"claves": ["A"], "nombre_grupo": "X", "grupo_nuevo": True}),
]


@pytest.mark.parametrize("base", [P, N])
@pytest.mark.parametrize("metodo,ruta,cuerpo", ENDPOINTS)
def test_permisos_solo_administrador(client, usuario_headers, admin_usuarios_headers, base, metodo, ruta, cuerpo):
    kw = {"json": cuerpo} if cuerpo is not None else {}
    llamar = getattr(client, metodo)
    assert llamar(base + ruta, headers=usuario_headers, **kw).status_code == 403
    assert llamar(base + ruta, headers=admin_usuarios_headers, **kw).status_code == 403
    assert llamar(base + ruta, **kw).status_code == 401


def test_excel_requiere_administrador_y_tipo_valido(client, usuario_headers, admin_headers):
    archivo = {"archivo": ("x.xlsx", _excel([("A", "B")]), "application/octet-stream")}
    assert client.post(P + "/excel", headers=usuario_headers, files=archivo).status_code == 403
    assert client.post(P + "/excel", files=archivo).status_code == 401
    assert client.get("/api/admin/nombres-comerciales/otracosa/grupos", headers=admin_headers).status_code == 404
    r = client.post(P + "/excel", headers=admin_headers, files={"archivo": ("x.csv", b"a,b", "text/csv")})
    assert r.status_code == 400


# ---------------------------------------------------------------------------------------------
# Plaguicidas
# ---------------------------------------------------------------------------------------------

def test_carga_rellena_y_registra_nombres_nuevos(client, admin_headers):
    anio = 2071
    limpiar_importacion_anio(anio)
    a, a2, b = "ZZPROD CARGA 50 SC", "Zzprod Carga 50 Sc", "ZZPROD OTRO"
    claves = [_clave_p(a), _clave_p(b)]
    assert _clave_p(a) == _clave_p(a2)
    try:
        resumen = _cargar_plaguicidas(client, admin_headers, [
            _fila_plaguicidas(710001, "EMP CARGA", anio, 100.0, producto=a),
            _fila_plaguicidas(710002, "EMP CARGA", anio, 50.0, producto=a2),
            _fila_plaguicidas(710003, "EMP CARGA", anio, 25.0, producto=b),
        ])
        assert resumen["nombres_sin_homologar"] == 2              # dos nombres (A y A2 son el mismo)
        with engine.connect() as conn:
            log = conn.execute(text("SELECT Origen, Filas, CAST(CifUsd AS FLOAT) FROM dbo.log_ExcepcionesNombresComerciales WHERE NombreKey = :k"),
                               {"k": claves[0]}).all()
            filas = conn.execute(text("SELECT producto, NombreComercialHomologado FROM dbo.Importacion WHERE anio = :a"), {"a": anio}).all()
        assert log == [("Plaguicidas", 2, 150.0)]
        assert all(f[1] is None for f in filas)

        # Con catálogo la siguiente carga lo rellena: se carga otro año con el mismo nombre
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO dbo.CatalogoNombresComerciales (NombreKey, NombreHomologado, Confirmada) VALUES (:k, :n, 1)"),
                         {"k": claves[0], "n": "Zzprod Estandar"})
        anio2 = 2070
        limpiar_importacion_anio(anio2)
        try:
            r2 = _cargar_plaguicidas(client, admin_headers, [_fila_plaguicidas(700001, "EMP CARGA", anio2, 10.0, producto=a2)])
            assert r2["nombres_sin_homologar"] == 0
            with engine.connect() as conn:
                assert conn.execute(text("SELECT NombreComercialHomologado FROM dbo.Importacion WHERE anio = :a"), {"a": anio2}).scalar() == "Zzprod Estandar"
        finally:
            limpiar_importacion_anio(anio2)
    finally:
        _limpiar_p(claves, [anio])


def test_plaguicidas_flujo_con_tablero_y_totales_intactos(client, admin_headers, usuario_headers):
    anio = 2069
    limpiar_importacion_anio(anio)
    p1, p2, p3 = "ZZFLUJO UNO 10 EC", "ZZFLUJO DOS 10 EC", "ZZFLUJO TRES"
    k1, k2, k3 = _clave_p(p1), _clave_p(p2), _clave_p(p3)
    try:
        _cargar_plaguicidas(client, admin_headers, [
            _fila_plaguicidas(690001, "EMP", anio, 100.0, producto=p1),
            _fila_plaguicidas(690002, "EMP", anio, 50.0, producto=p2),
            _fila_plaguicidas(690003, "EMP", anio, 25.0, producto=p3),
        ])
        totales, originales = _totales(), _productos_originales(anio)

        r = client.get(P + "/nuevos-sin-homologar", headers=admin_headers, params={"busqueda": "zzflujo"})
        assert r.status_code == 200 and r.json()["total"] == 3
        assert {n["clave"] for n in r.json()["nombres"]} == {k1, k2, k3}
        for k, n in ((k1, p1), (k2, p2), (k3, p3)):
            r = client.post(P + "/nuevos-sin-homologar/asignar", headers=admin_headers, json={"claves": [k], "nombre_grupo": n, "grupo_nuevo": True})
            assert r.status_code == 200, r.text
        assert client.get(P + "/nuevos-sin-homologar", headers=admin_headers, params={"busqueda": "zzflujo"}).json()["total"] == 0

        assert _tabla_nombres(client, usuario_headers, anio) == {p1: 100.0, p2: 50.0, p3: 25.0}

        # Unir
        r = client.post(P + "/unir", headers=admin_headers, json={"claves": [k1, k2], "nombre_oficial": "Zzflujo Estandar 10 EC"})
        assert r.status_code == 200, r.text
        grupos = {g["nombre_homologado"]: g for g in client.get(P + "/grupos", headers=admin_headers, params={"busqueda": "zzflujo"}).json()["grupos"]}
        assert set(grupos) == {"Zzflujo Estandar 10 EC", p3}
        g = grupos["Zzflujo Estandar 10 EC"]
        assert g["confirmada"] and g["puede_separar"] and sorted(g["claves"]) == sorted([k1, k2]) and g["cif_usd"] == 150.0
        assert g["usuario_mod"] is not None
        assert _tabla_nombres(client, usuario_headers, anio) == {"Zzflujo Estandar 10 EC": 150.0, p3: 25.0}
        opciones = client.get("/api/dashboard/plaguicidas/opciones", headers=usuario_headers)
        assert opciones.status_code == 200
        assert "Zzflujo Estandar 10 EC" in opciones.json()["productos"] and p1 not in opciones.json()["productos"]
        # Filtrar por el nombre estándar trae las dos filas unidas
        r = client.get("/api/dashboard/plaguicidas", headers=usuario_headers, params={"anio": anio, "producto": "Zzflujo Estandar 10 EC"})
        assert r.status_code == 200 and r.json()["kpis"]["registros"] == 2
        assert _totales() == totales and _productos_originales(anio) == originales

        # Renombrar
        assert client.put(P + "/renombrar", headers=admin_headers,
                          json={"nombre_actual": "Zzflujo Estandar 10 EC", "nombre_nuevo": "Zzflujo Final"}).status_code == 200
        assert _tabla_nombres(client, usuario_headers, anio) == {"Zzflujo Final": 150.0, p3: 25.0}

        # Separar
        r = client.post(P + "/separar", headers=admin_headers, json={"clave": k2})
        assert r.status_code == 200, r.text
        assert r.json()["nombre_oficial"] == p2
        assert _tabla_nombres(client, usuario_headers, anio) == {"Zzflujo Final": 100.0, p2: 50.0, p3: 25.0}
        assert _totales() == totales and _productos_originales(anio) == originales
    finally:
        _limpiar_p([k1, k2, k3], [anio])


def test_confirmar_y_validaciones(client, admin_headers):
    anio = 2068
    limpiar_importacion_anio(anio)
    pa, pb = "ZQVAL AAA", "ZQVAL BBB"
    ka, kb = _clave_p(pa), _clave_p(pb)
    try:
        _cargar_plaguicidas(client, admin_headers, [
            _fila_plaguicidas(680001, "EMP", anio, 10.0, producto=pa), _fila_plaguicidas(680002, "EMP", anio, 20.0, producto=pb),
        ])
        with engine.begin() as conn:      # entran PENDIENTES (Confirmada = 0), como la semilla del script 27
            for k, n in ((ka, pa), (kb, pb)):
                conn.execute(text("INSERT INTO dbo.CatalogoNombresComerciales (NombreKey, NombreHomologado, Confirmada) VALUES (:k, :n, 0)"), {"k": k, "n": n})
        with Session(engine) as db:
            sincronizar_nombres_plaguicidas(db)
            db.commit()
        pend = client.get(P + "/grupos", headers=admin_headers, params={"busqueda": "zqval", "estado": "pendientes"}).json()
        assert pend["total"] == 2 and pend["pendientes_en_filtro"] == 2
        assert client.post(P + "/confirmar", headers=admin_headers, json={"nombres": [pa]}).status_code == 200
        assert [g["nombre_homologado"] for g in client.get(P + "/grupos", headers=admin_headers, params={"busqueda": "zqval", "estado": "confirmadas"}).json()["grupos"]] == [pa]
        r = client.post(P + "/confirmar-pendientes", headers=admin_headers, json={"busqueda": "zqval"})
        assert r.status_code == 200 and r.json()["grupos_afectados"] == 1
        assert client.get(P + "/grupos", headers=admin_headers, params={"busqueda": "zqval", "estado": "pendientes"}).json()["total"] == 0

        # Validaciones
        assert client.post(P + "/unir", headers=admin_headers, json={"claves": [ka, kb], "nombre_oficial": "   "}).status_code == 422
        assert client.post(P + "/unir", headers=admin_headers, json={"claves": [ka, ka], "nombre_oficial": "X"}).status_code == 400
        assert client.post(P + "/unir", headers=admin_headers, json={"claves": [ka, "NO EXISTE"], "nombre_oficial": "X"}).status_code == 404
        assert client.post(P + "/separar", headers=admin_headers, json={"clave": ka}).status_code == 400
        assert client.put(P + "/renombrar", headers=admin_headers, json={"nombre_actual": pa, "nombre_nuevo": pb.lower()}).status_code == 409
        assert client.put(P + "/renombrar", headers=admin_headers, json={"nombre_actual": "NO HAY", "nombre_nuevo": "Y"}).status_code == 404
        assert client.post(P + "/confirmar", headers=admin_headers, json={"nombres": ["NO HAY"]}).status_code == 404
        assert client.get(P + "/grupos", headers=admin_headers, params={"estado": "otra"}).status_code == 400
        assert client.post(P + "/nuevos-sin-homologar/asignar", headers=admin_headers,
                           json={"claves": [ka], "nombre_grupo": pb}).status_code == 409                # ya está en el catálogo
        assert client.post(P + "/nuevos-sin-homologar/asignar", headers=admin_headers,
                           json={"claves": ["NUNCA LLEGO"], "nombre_grupo": pb}).status_code == 404
    finally:
        _limpiar_p([ka, kb], [anio])


def test_excel_estandar_vista_previa_y_aplicar_plaguicidas(client, admin_headers, usuario_headers):
    anio = 2067
    limpiar_importacion_anio(anio)
    e1, e2, e3, e4 = "ZZXL UNO", "ZZXL DOS", "ZZXL TRES", "ZZXL CUATRO"
    claves = [_clave_p(x) for x in (e1, e2, e3, e4)]
    nuevo_en_excel = "ZZXL SOLO EN EXCEL"
    claves.append(_clave_p(nuevo_en_excel))
    try:
        _cargar_plaguicidas(client, admin_headers, [
            _fila_plaguicidas(670001, "EMP", anio, 100.0, producto=e1), _fila_plaguicidas(670002, "EMP", anio, 50.0, producto=e2),
            _fila_plaguicidas(670003, "EMP", anio, 25.0, producto=e3), _fila_plaguicidas(670004, "EMP", anio, 5.0, producto=e4),
        ])
        # e3 ya está en el catálogo con otro nombre -> "se unirá"; e4 ya tiene el nombre estándar -> "sin cambio"
        with engine.begin() as conn:
            for k, n in ((claves[2], "Antiguo Tres"), (claves[3], "Zzxl Estandar B")):
                conn.execute(text("INSERT INTO dbo.CatalogoNombresComerciales (NombreKey, NombreHomologado, Confirmada) VALUES (:k, :n, 0)"), {"k": k, "n": n})
        with Session(engine) as db:
            sincronizar_nombres_plaguicidas(db)
            db.commit()
        totales = _totales()

        excel = _excel([
            (e1, "Zzxl Estandar A"),                 # nuevo
            (e2.lower(), "Zzxl Estandar A"),         # nuevo (misma clave que e2 con otra capitalización), mismo estándar -> se une con e1
            (e3, "Zzxl Estandar B"),                 # se unirá (estaba como "Antiguo Tres")
            (e4, "Zzxl Estandar B"),                 # sin cambio
            (nuevo_en_excel, "Zzxl Estandar A"),     # nuevo (no existe en los datos)
            ("", "Sin nombre"),                      # conflicto: falta el nombre
            ("ZZXL DOBLE", "Estandar 1"),            # conflicto: dos estándares distintos
            ("zzxl doble", "Estandar 2"),
            ("ZZXL CADENA A", "ZZXL CADENA B"),      # conflicto: cadena A -> B y B -> C (solo se marca la fila A)
            ("ZZXL CADENA B", "ZZXL CADENA C"),      # nuevo
        ])
        archivo = {"archivo": ("estandar.xlsx", excel, "application/octet-stream")}
        r = client.post(P + "/excel", headers=admin_headers, files=archivo)         # vista previa
        assert r.status_code == 200, r.text
        v = r.json()
        assert v["aplicado"] is False and v["filas_leidas"] == 10
        assert (v["nuevos"], v["se_uniran"], v["sin_cambio"], v["conflictos"]) == (4, 1, 1, 4), v
        assert any(d["estado"] == "se_unira" and d["nombre_actual"] == "Antiguo Tres" for d in v["detalle"])
        # La vista previa no cambió nada
        with engine.connect() as conn:
            assert conn.execute(text("SELECT NombreHomologado FROM dbo.CatalogoNombresComerciales WHERE NombreKey = :k"), {"k": claves[2]}).scalar() == "Antiguo Tres"
            assert conn.execute(text("SELECT COUNT(*) FROM dbo.CatalogoNombresComerciales WHERE NombreKey = :k"), {"k": claves[0]}).scalar() == 0

        r = client.post(P + "/excel", headers=admin_headers, params={"aplicar": True}, files=archivo)    # aplicar
        assert r.status_code == 200, r.text
        assert r.json()["aplicado"] is True and r.json()["filas_sincronizadas"] >= 3
        assert _tabla_nombres(client, usuario_headers, anio) == {"Zzxl Estandar A": 150.0, "Zzxl Estandar B": 30.0}
        with engine.connect() as conn:
            estado = {k: (n, bool(c)) for k, n, c in conn.execute(
                text("SELECT NombreKey, NombreHomologado, Confirmada FROM dbo.CatalogoNombresComerciales WHERE NombreKey IN :ks").bindparams(
                    bindparam("ks", expanding=True)), {"ks": claves})}
        assert estado[claves[0]] == ("Zzxl Estandar A", True) and estado[claves[4]] == ("Zzxl Estandar A", True)
        assert estado[claves[2]] == ("Zzxl Estandar B", True)
        assert _totales() == totales

        # Aplicar otra vez no cambia nada (todo queda "sin cambio")
        r = client.post(P + "/excel", headers=admin_headers, params={"aplicar": True}, files=archivo)
        assert (r.json()["nuevos"], r.json()["se_uniran"]) == (0, 0)
    finally:
        _limpiar_p(claves + [_clave_p(x) for x in ("ZZXL DOBLE", "ZZXL CADENA A", "ZZXL CADENA B", "ZZXL CADENA C")], [anio])


def test_excel_invalido(client, admin_headers):
    r = client.post(P + "/excel", headers=admin_headers, files={"archivo": ("x.xlsx", b"no es un excel", "application/octet-stream")})
    assert r.status_code == 400
    una_columna = BytesIO()
    pd.DataFrame({"a": ["x"]}).to_excel(una_columna, index=False)
    r = client.post(P + "/excel", headers=admin_headers, files={"archivo": ("x.xlsx", una_columna.getvalue(), "application/octet-stream")})
    assert r.status_code == 400 and "dos columnas" in r.json()["detail"]


# ---------------------------------------------------------------------------------------------
# Nutrientes (reutiliza dbo.CatalogoAgrupadorNutrientes)
# ---------------------------------------------------------------------------------------------

def test_nutrientes_flujo_con_catalogo_existente(client, admin_headers, usuario_headers):
    anio = 2066
    limpiar_nutrientes_anio(anio)
    n1, n2, n3 = "ZZNUT UNO 20-20-20", "ZZNUT DOS 20-20-20", "ZZNUT TRES"
    k1, k2, k3 = _clave_n(n1), _clave_n(n2), _clave_n(n3)
    try:
        _cargar_nutrientes(client, admin_headers, [
            _fila_nutrientes("1-66", "EMP N", anio, "$100.00", nombre=n1),
            _fila_nutrientes("2-66", "EMP N", anio, "$50.00", nombre=n2),
            _fila_nutrientes("3-66", "EMP N", anio, "$25.00", nombre=n3),
        ])
        totales = _totales()
        # Sin entrada en el catálogo: aparecen como nuevos
        r = client.get(N + "/nuevos-sin-homologar", headers=admin_headers, params={"busqueda": "zznut"})
        assert r.status_code == 200 and {x["clave"] for x in r.json()["nombres"]} == {k1, k2, k3}
        assert _top_formulas(client, usuario_headers, anio) == {}

        for k, n in ((k1, n1), (k2, n2), (k3, n3)):
            r = client.post(N + "/nuevos-sin-homologar/asignar", headers=admin_headers, json={"claves": [k], "nombre_grupo": n, "grupo_nuevo": True})
            assert r.status_code == 200, r.text
        assert _top_formulas(client, usuario_headers, anio) == {n1: 100.0, n2: 50.0, n3: 25.0}
        # Quedó en el catálogo EXISTENTE (ProductoAgrupado), confirmado y con el usuario
        with engine.connect() as conn:
            fila = conn.execute(text("SELECT ProductoAgrupado, Confirmada, UsuarioMod, Excluido FROM dbo.CatalogoAgrupadorNutrientes WHERE NombreComercial_Key = :k"), {"k": k1}).one()
        assert fila[0] == n1 and bool(fila[1]) and fila[2] is not None and not fila[3]

        # Unir -> la Fórmula del tablero suma los dos nombres
        r = client.post(N + "/unir", headers=admin_headers, json={"claves": [k1, k2], "nombre_oficial": "ZZNUT 20-20-20"})
        assert r.status_code == 200, r.text
        assert _top_formulas(client, usuario_headers, anio) == {"ZZNUT 20-20-20": 150.0, n3: 25.0}
        g = [x for x in client.get(N + "/grupos", headers=admin_headers, params={"busqueda": "zznut"}).json()["grupos"] if x["nombre_homologado"] == "ZZNUT 20-20-20"][0]
        assert sorted(g["claves"]) == sorted([k1, k2]) and g["cif_usd"] == 150.0 and g["puede_separar"]

        # Renombrar y separar
        assert client.put(N + "/renombrar", headers=admin_headers, json={"nombre_actual": "ZZNUT 20-20-20", "nombre_nuevo": "ZZNUT FORMULA"}).status_code == 200
        assert _top_formulas(client, usuario_headers, anio) == {"ZZNUT FORMULA": 150.0, n3: 25.0}
        assert client.post(N + "/separar", headers=admin_headers, json={"clave": k2}).status_code == 200
        assert _top_formulas(client, usuario_headers, anio) == {"ZZNUT FORMULA": 100.0, n2: 50.0, n3: 25.0}

        # Nombre demasiado largo para ProductoAgrupado (150) -> 400
        r = client.put(N + "/renombrar", headers=admin_headers, json={"nombre_actual": n3, "nombre_nuevo": "X" * 200})
        assert r.status_code == 400
        assert _totales() == totales
    finally:
        _limpiar_n([k1, k2, k3], [anio])


def test_nutrientes_excel_estandar(client, admin_headers, usuario_headers):
    anio = 2065
    limpiar_nutrientes_anio(anio)
    a, b = "ZZNXL UNO", "ZZNXL DOS"
    ka, kb = _clave_n(a), _clave_n(b)
    try:
        _cargar_nutrientes(client, admin_headers, [
            _fila_nutrientes("1-65", "EMP N", anio, "$100.00", nombre=a), _fila_nutrientes("2-65", "EMP N", anio, "$40.00", nombre=b),
        ])
        excel = _excel([(a, "ZZNXL ESTANDAR"), (b, "ZZNXL ESTANDAR")])
        archivo = {"archivo": ("estandar.xlsx", excel, "application/octet-stream")}
        v = client.post(N + "/excel", headers=admin_headers, files=archivo).json()
        assert (v["nuevos"], v["se_uniran"], v["conflictos"]) == (2, 0, 0)
        assert _top_formulas(client, usuario_headers, anio) == {}                 # la vista previa no aplica nada
        assert client.post(N + "/excel", headers=admin_headers, params={"aplicar": True}, files=archivo).json()["aplicado"] is True
        assert _top_formulas(client, usuario_headers, anio) == {"ZZNXL ESTANDAR": 140.0}
    finally:
        _limpiar_n([ka, kb], [anio])

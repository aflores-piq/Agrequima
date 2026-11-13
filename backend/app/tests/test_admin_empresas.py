"""Pantalla de mantenimiento de homologación de empresas (/api/admin/empresas): permisos, unir, renombrar, separar,
confirmar, nuevas sin homologar y reflejo en los tableros sin que cambien filas ni CIF.

Cada prueba usa su propio año de prueba y limpia lo que crea en dbo.CatalogoEmpresas y dbo.log_ExcepcionesEmpresas."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import engine
from app.services.empresas import sincronizar_empresas
from app.tests.helpers import limpiar_importacion_anio, limpiar_nutrientes_anio
from app.tests.test_homologacion_empresas import (
    _cargar_nutrientes,
    _cargar_plaguicidas,
    _clave,
    _fila_nutrientes,
    _fila_plaguicidas,
    _limpiar_catalogo,
    _poner_en_catalogo,
    _top_nutrientes,
)

BASE = "/api/admin/empresas"


def _totales() -> dict:
    with engine.connect() as conn:
        imp = conn.execute(text("SELECT COUNT(*), CAST(SUM(CAST(cif_USD AS FLOAT)) AS FLOAT) FROM dbo.Importacion")).one()
        nut = conn.execute(text("SELECT COUNT(*), CAST(SUM(CAST(CIF_dolares AS FLOAT)) AS FLOAT) FROM dbo.Nutrientes")).one()
    return {"imp": (imp[0], round(imp[1] or 0, 2)), "nut": (nut[0], round(nut[1] or 0, 2))}


def _originales(anio: int) -> list[tuple]:
    with engine.connect() as conn:
        a = conn.execute(text("SELECT importador FROM dbo.Importacion WHERE anio = :a ORDER BY recibointerno"), {"a": anio}).all()
        b = conn.execute(text("SELECT EmpresaImportadora FROM dbo.Nutrientes WHERE anio = :a ORDER BY No_Licencia"), {"a": anio}).all()
    return [tuple(x) for x in a + b]


def _grupo(client, headers, nombre_busqueda: str, **params) -> list[dict]:
    r = client.get(f"{BASE}/grupos", headers=headers, params={"busqueda": nombre_busqueda, "tamano_pagina": 200, **params})
    assert r.status_code == 200, r.text
    return r.json()["grupos"]


def _top_plaguicidas(client, headers, anio):
    r = client.get("/api/dashboard/plaguicidas", headers=headers, params={"anio": anio})
    assert r.status_code == 200, r.text
    d = r.json()
    return {f["etiqueta"]: f["cif_usd"] for f in d["top_importadores"]}, d["kpis"]


def _limpiar(claves, anios):
    _limpiar_catalogo(claves)
    with Session(engine) as db:
        sincronizar_empresas(db)
        db.commit()
    for a in anios:
        limpiar_nutrientes_anio(a)
        limpiar_importacion_anio(a)


def _asignar_nuevo(client, headers, clave, nombre):
    r = client.post(f"{BASE}/nuevas-sin-homologar/asignar", headers=headers,
                    json={"claves": [clave], "nombre_grupo": nombre, "grupo_nuevo": True})
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------------------------

ENDPOINTS = [
    ("get", "/grupos", None),
    ("get", "/nuevas-sin-homologar", None),
    ("post", "/unir", {"claves": ["A", "B"], "nombre_oficial": "X"}),
    ("put", "/renombrar", {"nombre_actual": "A", "nombre_nuevo": "B"}),
    ("post", "/separar", {"clave": "A"}),
    ("post", "/confirmar", {"nombres": ["A"]}),
    ("post", "/confirmar-pendientes", {}),
    ("post", "/nuevas-sin-homologar/asignar", {"claves": ["A"], "nombre_grupo": "X", "grupo_nuevo": True}),
]


@pytest.mark.parametrize("metodo,ruta,cuerpo", ENDPOINTS)
def test_permisos_por_rol(client, usuario_headers, admin_headers, admin_usuarios_headers, metodo, ruta, cuerpo):
    """Administrador y Administrador de Usuarios (el administrador del cliente) entran; Usuario 403; sin sesión 401."""
    kw = {"json": cuerpo} if cuerpo is not None else {}
    llamar = getattr(client, metodo)
    assert llamar(BASE + ruta, headers=usuario_headers, **kw).status_code == 403
    assert llamar(BASE + ruta, **kw).status_code == 401
    for headers in (admin_headers, admin_usuarios_headers):
        codigo = llamar(BASE + ruta, headers=headers, **kw).status_code
        assert codigo not in (401, 403), (metodo, ruta, codigo)
        if metodo == "get":
            assert codigo == 200


def test_administrador_de_usuarios_ve_la_lista_igual_que_el_administrador(client, admin_headers, admin_usuarios_headers):
    a = client.get(f"{BASE}/grupos", headers=admin_headers, params={"tamano_pagina": 5})
    b = client.get(f"{BASE}/grupos", headers=admin_usuarios_headers, params={"tamano_pagina": 5})
    assert a.status_code == b.status_code == 200 and a.json()["total"] == b.json()["total"]


def test_sin_acceso_a_importaciones_es_403(client, usuario_sin_importaciones_headers):
    assert client.get(f"{BASE}/grupos", headers=usuario_sin_importaciones_headers).status_code == 403


# ---------------------------------------------------------------------------------------------

def test_flujo_unir_renombrar_separar_con_tableros_y_totales_intactos(client, admin_headers, usuario_headers):
    anio = 2077
    claves: list[str | None] = []
    limpiar_nutrientes_anio(anio)
    limpiar_importacion_anio(anio)
    n1, n2, n3 = "ZETAFLUJO UNO, S.A.", "ZETAFLUJO DOS, S.A.", "ZETAFLUJO TRES, S.A."
    try:
        _cargar_nutrientes(client, admin_headers, [
            _fila_nutrientes("1-77", n1, anio, "$100.00"),
            _fila_nutrientes("2-77", n2, anio, "$50.00"),
            _fila_nutrientes("3-77", n3, anio, "$25.00"),
        ])
        _cargar_plaguicidas(client, admin_headers, [_fila_plaguicidas(770001, n2, anio, 200.0)])
        k1, k2, k3 = _clave(n1), _clave(n2), _clave(n3)
        claves += [k1, k2, k3]
        totales = _totales()
        originales = _originales(anio)

        # Recién cargadas: están en "nuevas sin homologar", con montos actuales
        r = client.get(f"{BASE}/nuevas-sin-homologar", headers=admin_headers)
        assert r.status_code == 200
        nuevas = {e["clave"]: e for e in r.json()["empresas"]}
        assert {k1, k2, k3} <= set(nuevas)
        assert nuevas[k2]["nutrientes"] == {"filas": 1, "cif_usd": 50.0}
        assert nuevas[k2]["plaguicidas"] == {"filas": 1, "cif_usd": 200.0}
        assert sorted(nuevas[k2]["origenes"]) == ["Nutrientes", "Plaguicidas"]
        assert nuevas[k2]["cif_total_usd"] == 250.0

        # Cada una crea su grupo (confirmado); salen de "nuevas"
        for n, k in ((n1, k1), (n2, k2), (n3, k3)):
            _asignar_nuevo(client, admin_headers, k, n)
        r = client.get(f"{BASE}/nuevas-sin-homologar", headers=admin_headers)
        assert not ({k1, k2, k3} & {e["clave"] for e in r.json()["empresas"]})
        grupos = _grupo(client, admin_headers, "ZETAFLUJO")
        assert sorted(g["nombre_homologado"] for g in grupos) == sorted([n1, n2, n3])
        assert all(g["confirmada"] for g in grupos)
        g2 = next(g for g in grupos if g["nombre_homologado"] == n2)
        assert g2["origen"] == "ambas" and g2["cif_total_usd"] == 250.0 and g2["puede_separar"] is False

        top_n, kpis = _top_nutrientes(client, usuario_headers, anio)
        assert top_n == {n1: 100.0, n2: 50.0, n3: 25.0} and kpis["empresas"] == 3
        top_p, _ = _top_plaguicidas(client, usuario_headers, anio)
        assert top_p == {n2: 200.0}

        # ---- Unir UNO + DOS bajo un nombre oficial nuevo
        r = client.post(f"{BASE}/unir", headers=admin_headers, json={"claves": [k1, k2], "nombre_oficial": "  Zetaflujo   Unido, S.A. "})
        assert r.status_code == 200, r.text
        assert r.json()["nombre_oficial"] == "Zetaflujo Unido, S.A." and r.json()["filas_sincronizadas"] >= 3
        grupos = _grupo(client, admin_headers, "ZETAFLUJO")
        assert sorted(g["nombre_homologado"] for g in grupos) == sorted(["Zetaflujo Unido, S.A.", n3])
        unido = next(g for g in grupos if g["nombre_homologado"] == "Zetaflujo Unido, S.A.")
        assert unido["confirmada"] and unido["puede_separar"] and sorted(unido["claves"]) == sorted([k1, k2])
        assert sorted(v["nombre_original"] for v in unido["variantes"]) == sorted([n1, n2])
        assert unido["cif_total_usd"] == 350.0
        assert unido["plaguicidas"] == {"filas": 1, "cif_usd": 200.0} and unido["nutrientes"] == {"filas": 2, "cif_usd": 150.0}
        assert unido["usuario_mod"] is not None and unido["fecha_mod"] is not None

        top_n, kpis = _top_nutrientes(client, usuario_headers, anio)
        assert top_n == {"Zetaflujo Unido, S.A.": 150.0, n3: 25.0} and kpis["empresas"] == 2
        assert kpis["cif_total_usd"] == 175.0                                       # el total no cambia (100+50+25)
        top_p, _ = _top_plaguicidas(client, usuario_headers, anio)
        assert top_p == {"Zetaflujo Unido, S.A.": 200.0}
        assert _totales() == totales and _originales(anio) == originales

        # ---- Renombrar
        r = client.put(f"{BASE}/renombrar", headers=admin_headers,
                       json={"nombre_actual": "Zetaflujo Unido, S.A.", "nombre_nuevo": "Grupo Zetaflujo, S.A."})
        assert r.status_code == 200, r.text
        top_n, _ = _top_nutrientes(client, usuario_headers, anio)
        assert top_n == {"Grupo Zetaflujo, S.A.": 150.0, n3: 25.0}
        assert _totales() == totales and _originales(anio) == originales

        # ---- Separar DOS: vuelve a quedar sola con su nombre original
        r = client.post(f"{BASE}/separar", headers=admin_headers, json={"clave": k2})
        assert r.status_code == 200, r.text
        assert r.json()["nombre_oficial"] == n2
        grupos = {g["nombre_homologado"]: g for g in _grupo(client, admin_headers, "ZETAFLUJO")}
        assert set(grupos) == {"Grupo Zetaflujo, S.A.", n2, n3}
        assert grupos[n2]["claves"] == [k2] and grupos[n2]["confirmada"]
        assert grupos["Grupo Zetaflujo, S.A."]["claves"] == [k1]
        top_n, kpis = _top_nutrientes(client, usuario_headers, anio)
        assert top_n == {"Grupo Zetaflujo, S.A.": 100.0, n2: 50.0, n3: 25.0} and kpis["empresas"] == 3
        top_p, _ = _top_plaguicidas(client, usuario_headers, anio)
        assert top_p == {n2: 200.0}
        assert _totales() == totales and _originales(anio) == originales
    finally:
        _limpiar(claves, [anio])


def test_separar_cuando_la_variante_se_llama_igual_que_el_grupo(client, admin_headers, usuario_headers):
    """Si el nombre del grupo coincide con el de la variante que se separa, el resto del grupo toma el nombre de su variante
    principal: nunca quedan dos grupos con el mismo nombre."""
    anio = 2076
    claves = []
    limpiar_nutrientes_anio(anio)
    na, nb = "ZETASEP ALFA, S.A.", "ZETASEP BETA, S.A."
    try:
        _cargar_nutrientes(client, admin_headers, [
            _fila_nutrientes("1-76", na, anio, "$300.00"), _fila_nutrientes("2-76", nb, anio, "$40.00"),
        ])
        ka, kb = _clave(na), _clave(nb)
        claves += [ka, kb]
        _asignar_nuevo(client, admin_headers, ka, na)
        _asignar_nuevo(client, admin_headers, kb, nb)
        # Se unen bajo el nombre de ALFA; separar ALFA -> el resto (BETA) se queda con su nombre
        assert client.post(f"{BASE}/unir", headers=admin_headers, json={"claves": [ka, kb], "nombre_oficial": na}).status_code == 200
        r = client.post(f"{BASE}/separar", headers=admin_headers, json={"clave": ka})
        assert r.status_code == 200, r.text
        grupos = {g["nombre_homologado"]: g for g in _grupo(client, admin_headers, "ZETASEP")}
        assert set(grupos) == {na, nb} and grupos[na]["claves"] == [ka] and grupos[nb]["claves"] == [kb]
    finally:
        _limpiar(claves, [anio])


def test_confirmar_grupos_y_confirmar_pendientes_del_filtro(client, admin_headers):
    anio = 2075
    claves = []
    limpiar_nutrientes_anio(anio)
    nombres = {"ZQCONF AAA UNO, S.A.": "$10.00", "ZQCONF AAA DOS, S.A.": "$20.00", "ZQCONF BBB TRES, S.A.": "$30.00"}
    try:
        _cargar_nutrientes(client, admin_headers, [
            _fila_nutrientes(f"{i}-75", n, anio, cif) for i, (n, cif) in enumerate(nombres.items(), 1)
        ])
        for n in nombres:
            claves.append(_poner_en_catalogo(n, n))          # entran PENDIENTES (Confirmada = 0), como la semilla del script 26
        with Session(engine) as db:
            sincronizar_empresas(db)
            db.commit()

        pend = _grupo(client, admin_headers, "ZQCONF", estado="pendientes")
        assert sorted(g["nombre_homologado"] for g in pend) == sorted(nombres)
        assert not _grupo(client, admin_headers, "ZQCONF", estado="confirmadas")
        r = client.get(f"{BASE}/grupos", headers=admin_headers, params={"busqueda": "zqconf aaa"})
        assert r.json()["pendientes_en_filtro"] == 2                                    # búsqueda sin tildes ni mayúsculas

        # Confirmar uno
        r = client.post(f"{BASE}/confirmar", headers=admin_headers, json={"nombres": ["ZQCONF AAA UNO, S.A."]})
        assert r.status_code == 200 and r.json()["grupos_afectados"] == 1
        assert [g["nombre_homologado"] for g in _grupo(client, admin_headers, "ZQCONF", estado="confirmadas")] == ["ZQCONF AAA UNO, S.A."]

        # Confirmar todos los pendientes del filtro "zqconf aaa": confirma DOS y deja pendiente a OTRACONF
        r = client.post(f"{BASE}/confirmar-pendientes", headers=admin_headers, json={"busqueda": "zqconf aaa", "origen": "N"})
        assert r.status_code == 200 and r.json()["grupos_afectados"] == 1, r.text
        assert [g["nombre_homologado"] for g in _grupo(client, admin_headers, "ZQCONF", estado="pendientes")] == ["ZQCONF BBB TRES, S.A."]

        # Filtro de origen: ninguno de estos tiene Plaguicidas
        assert _grupo(client, admin_headers, "ZQCONF", origen="P") == []
        assert len(_grupo(client, admin_headers, "ZQCONF", origen="N")) == 3
        assert _grupo(client, admin_headers, "ZQCONF", origen="ambas") == []
    finally:
        _limpiar(claves, [anio])


def test_validaciones(client, admin_headers):
    anio = 2074
    claves = []
    limpiar_nutrientes_anio(anio)
    na, nb = "ZETAVAL UNO, S.A.", "ZETAVAL DOS, S.A."
    try:
        _cargar_nutrientes(client, admin_headers, [_fila_nutrientes("1-74", na, anio, "$10.00"), _fila_nutrientes("2-74", nb, anio, "$20.00")])
        ka, kb = _clave(na), _clave(nb)
        claves += [ka, kb]
        _asignar_nuevo(client, admin_headers, ka, na)
        _asignar_nuevo(client, admin_headers, kb, nb)

        # Nombre oficial vacío -> 422
        assert client.post(f"{BASE}/unir", headers=admin_headers, json={"claves": [ka, kb], "nombre_oficial": "   "}).status_code == 422
        assert client.put(f"{BASE}/renombrar", headers=admin_headers, json={"nombre_actual": na, "nombre_nuevo": ""}).status_code == 422
        # Menos de 2 claves -> 422; un grupo consigo mismo (la misma clave repetida) -> 400
        assert client.post(f"{BASE}/unir", headers=admin_headers, json={"claves": [ka], "nombre_oficial": "X"}).status_code == 422
        r = client.post(f"{BASE}/unir", headers=admin_headers, json={"claves": [ka, ka], "nombre_oficial": "X"})
        assert r.status_code == 400 and "consigo mismo" in r.json()["detail"]
        # Clave inexistente -> 404
        r = client.post(f"{BASE}/unir", headers=admin_headers, json={"claves": [ka, "NO EXISTE ESTA CLAVE"], "nombre_oficial": "X"})
        assert r.status_code == 404 and "NO EXISTE ESTA CLAVE" in r.json()["detail"]
        assert client.post(f"{BASE}/separar", headers=admin_headers, json={"clave": "NO EXISTE ESTA CLAVE"}).status_code == 404
        # Separar una variante que ya está sola -> 400
        assert client.post(f"{BASE}/separar", headers=admin_headers, json={"clave": ka}).status_code == 400
        # Renombrar un grupo con el nombre de otro -> 409; grupo inexistente -> 404
        r = client.put(f"{BASE}/renombrar", headers=admin_headers, json={"nombre_actual": na, "nombre_nuevo": nb.lower()})
        assert r.status_code == 409
        assert client.put(f"{BASE}/renombrar", headers=admin_headers, json={"nombre_actual": "NO HAY ESE GRUPO", "nombre_nuevo": "Y"}).status_code == 404
        # Nombre nuevo de una unión que ya usa un grupo FUERA de la selección -> 409
        r = client.post(f"{BASE}/unir", headers=admin_headers, json={"claves": [ka, "ZZZ"], "nombre_oficial": nb})
        assert r.status_code == 404                                                       # (clave ZZZ no existe)
        # Confirmar grupo inexistente -> 404; filtros inválidos -> 400
        assert client.post(f"{BASE}/confirmar", headers=admin_headers, json={"nombres": ["NO HAY ESE GRUPO"]}).status_code == 404
        assert client.get(f"{BASE}/grupos", headers=admin_headers, params={"estado": "otra"}).status_code == 400
        assert client.get(f"{BASE}/grupos", headers=admin_headers, params={"origen": "X"}).status_code == 400
        # Asignar una empresa que ya está en el catálogo -> 409; una que no llegó en cargas -> 404; grupo existente/nuevo mal -> 409/404
        r = client.post(f"{BASE}/nuevas-sin-homologar/asignar", headers=admin_headers, json={"claves": [ka], "nombre_grupo": nb})
        assert r.status_code == 409
        r = client.post(f"{BASE}/nuevas-sin-homologar/asignar", headers=admin_headers, json={"claves": ["CLAVE QUE NUNCA LLEGO"], "nombre_grupo": nb})
        assert r.status_code == 404
        # Nada de lo anterior modificó el catálogo
        assert sorted(g["nombre_homologado"] for g in _grupo(client, admin_headers, "ZETAVAL")) == sorted([na, nb])
    finally:
        _limpiar(claves, [anio])


def test_nuevas_sin_homologar_asignar_a_grupo_existente(client, admin_headers, usuario_headers):
    anio, anio2 = 2073, 2072
    claves = []
    limpiar_nutrientes_anio(anio)
    limpiar_nutrientes_anio(anio2)
    base, variante, sola = "ZETANUEVA BASE, S.A.", "ZETANUEVA VARIANTE, S.A.", "ZETANUEVA OTRA, S.A."
    try:
        _cargar_nutrientes(client, admin_headers, [_fila_nutrientes("1-73", base, anio, "$100.00")])
        kb = _clave(base)
        claves.append(kb)
        _asignar_nuevo(client, admin_headers, kb, base)

        # Llega una carga nueva con dos empresas desconocidas
        _cargar_nutrientes(client, admin_headers, [
            _fila_nutrientes("2-72", variante, anio2, "$40.00"), _fila_nutrientes("3-72", sola, anio2, "$7.00"),
        ], nombre="nueva_carga.csv")
        kv, ks = _clave(variante), _clave(sola)
        claves += [kv, ks]
        r = client.get(f"{BASE}/nuevas-sin-homologar", headers=admin_headers)
        mias = [e for e in r.json()["empresas"] if e["clave"] in (kv, ks)]
        assert len(mias) == 2 and r.json()["total"] == len(r.json()["empresas"])
        assert {e["nombre_ejemplo"] for e in mias} == {variante, sola}
        # Sin homologar: el tablero las muestra con su nombre original
        top, _ = _top_nutrientes(client, usuario_headers, anio2)
        assert top == {variante: 40.0, sola: 7.0}

        # Asignar una al grupo existente (grupo_nuevo = False) y la otra a un grupo nuevo
        r = client.post(f"{BASE}/nuevas-sin-homologar/asignar", headers=admin_headers,
                        json={"claves": [kv], "nombre_grupo": base, "grupo_nuevo": False})
        assert r.status_code == 200 and r.json()["nombre_oficial"] == base
        # Grupo nuevo con un nombre que ya existe -> 409; grupo existente que no existe -> 404
        assert client.post(f"{BASE}/nuevas-sin-homologar/asignar", headers=admin_headers,
                           json={"claves": [ks], "nombre_grupo": base, "grupo_nuevo": True}).status_code == 409
        assert client.post(f"{BASE}/nuevas-sin-homologar/asignar", headers=admin_headers,
                           json={"claves": [ks], "nombre_grupo": "NO HAY ESE GRUPO", "grupo_nuevo": False}).status_code == 404
        assert _asignar_nuevo(client, admin_headers, ks, "Zetanueva Otra Oficial, S.A.")["claves_afectadas"] == 1

        r = client.get(f"{BASE}/nuevas-sin-homologar", headers=admin_headers)
        assert not ({kv, ks} & {e["clave"] for e in r.json()["empresas"]})
        top, kpis = _top_nutrientes(client, usuario_headers, anio2)
        assert top == {base: 40.0, "Zetanueva Otra Oficial, S.A.": 7.0} and kpis["empresas"] == 2
        assert kpis["cif_total_usd"] == 47.0
    finally:
        _limpiar(claves, [anio, anio2])


def test_nuevas_sin_homologar_vacia_tiene_forma_valida(client, admin_headers):
    """Si no hay empresas nuevas la respuesta es una lista vacía válida (la pantalla muestra «todo al día»)."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dbo.log_ExcepcionesEmpresas WHERE EmpresaKey NOT IN (SELECT EmpresaKey FROM dbo.CatalogoEmpresas)"))
    r = client.get(f"{BASE}/nuevas-sin-homologar", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == {"total": 0, "empresas": []}

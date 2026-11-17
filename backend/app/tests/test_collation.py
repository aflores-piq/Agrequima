"""Collation de las columnas homologadas (script 29, app/core/collation.py).

Causa del error 446/468 en produccion: las columnas originales estan en Modern_Spanish_CI_AS y las que agregaron los scripts 26/27
(EmpresaHomologada, NombreComercialHomologado) en la collation por defecto de la base (SQL_Latin1_General_CP1_CI_AS); COALESCE entre
las dos no se puede resolver. Estas pruebas corren en las DOS configuraciones:
  - collations iguales (Agrequima_Test normal): el helper no cambia ningun resultado;
  - collations distintas (una copia de Agrequima_Test con las homologadas en SQL_Latin1; se elige con PIQ_TEST_DB): el helper
    funciona y el COALESCE sin helper SI falla (confirma la causa).
"""

import re
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.dialects import mssql
from sqlalchemy.exc import DBAPIError

from app.core.collation import (
    COLLATION_ORIGINALES,
    coalesce_homologado,
    sql_coalesce_homologado,
)
from app.core.db import engine
from app.models.importacion import Importacion
from app.models.nutriente import Nutriente, NutrienteActivo

DEPLOY = Path(__file__).resolve().parents[2] / "deploy_servidor_real"
PARES = [  # (tabla, columna homologada, columna original)
    ("Importacion", "EmpresaHomologada", "importador"),
    ("Importacion", "NombreComercialHomologado", "producto"),
    ("Nutrientes", "EmpresaHomologada", "EmpresaImportadora"),
]


def _collation(conn, tabla: str, columna: str) -> str:
    return conn.execute(
        text("SELECT collation_name FROM sys.columns WHERE object_id = OBJECT_ID(:t) AND name = :c"),
        {"t": f"dbo.{tabla}", "c": columna},
    ).scalar()


def _collations_coinciden() -> bool:
    with engine.connect() as conn:
        return all(_collation(conn, t, h) == _collation(conn, t, o) for t, h, o in PARES)


# ---------------------------------------------------------------------------------------------
# 1) El helper genera COLLATE explicito en los dos lados (Modern_Spanish_CI_AS, NO DATABASE_DEFAULT)
# ---------------------------------------------------------------------------------------------

def _sql(expresion) -> str:
    return str(select(expresion).compile(dialect=mssql.dialect(), compile_kwargs={"literal_binds": True}))


@pytest.mark.parametrize("expresion", [
    Importacion.importador_efectivo,
    Importacion.producto_efectivo,
    Nutriente.empresa_efectiva,
    NutrienteActivo.empresa_efectiva,
])
def test_las_expresiones_efectivas_usan_collate_explicito_en_los_dos_lados(expresion):
    sql = _sql(expresion)
    assert COLLATION_ORIGINALES == "Modern_Spanish_CI_AS"
    assert sql.count("COLLATE Modern_Spanish_CI_AS") == 2, sql
    assert "DATABASE_DEFAULT" not in sql.upper()
    assert "coalesce(" in sql.lower()


def test_el_helper_de_sql_escrito_a_mano_es_equivalente():
    texto = sql_coalesce_homologado("EmpresaHomologada", "importador")
    assert texto == ("COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, importador COLLATE Modern_Spanish_CI_AS)")


# ---------------------------------------------------------------------------------------------
# 2) Ninguna consulta mezcla homologada con original sin pasar por el helper
# ---------------------------------------------------------------------------------------------

def test_ningun_servicio_hace_coalesce_directo_entre_homologada_y_original():
    """Regla del proyecto: toda mezcla pasa por app/core/collation.py. Busca func.coalesce(...) con columnas homologadas."""
    raiz = Path(__file__).resolve().parents[1]
    patron = re.compile(r"func\.coalesce\(.*Homologad", re.IGNORECASE)
    ofensores = []
    for archivo in raiz.rglob("*.py"):
        if "tests" in archivo.parts or archivo.name == "collation.py" or "__pycache__" in archivo.parts:
            continue
        for n, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
            if patron.search(linea):
                ofensores.append(f"{archivo.relative_to(raiz)}:{n}: {linea.strip()}")
    assert not ofensores, "COALESCE de columnas homologadas sin pasar por app/core/collation.py:" + chr(10) + chr(10).join(ofensores)


# ---------------------------------------------------------------------------------------------
# 3) Resultados: con el helper el COALESCE responde siempre; sin helper se confirma la causa del error
# ---------------------------------------------------------------------------------------------

def test_el_helper_responde_en_cualquier_configuracion():
    with engine.connect() as conn:
        n_emp = conn.execute(select(func.count(NutrienteActivo.empresa_efectiva.distinct()))).scalar()
        top = conn.execute(
            select(Importacion.importador_efectivo, func.sum(Importacion.cif_USD))
            .where(Importacion.importador_efectivo.isnot(None))
            .group_by(Importacion.importador_efectivo)
            .order_by(func.sum(Importacion.cif_USD).desc())
            .limit(10)
        ).all()
        distintos = conn.execute(select(func.count(Importacion.producto_efectivo.distinct()))).scalar()
    assert n_emp is not None and distintos is not None and len(top) <= 10


def test_con_collations_iguales_el_helper_no_cambia_ningun_resultado():
    if not _collations_coinciden():
        pytest.skip("las collations difieren en esta base: la comparacion contra el COALESCE sin helper no aplica")
    with engine.connect() as conn:
        for modelo, hom, orig in ((Importacion, Importacion.EmpresaHomologada, Importacion.importador),
                                  (Importacion, Importacion.NombreComercialHomologado, Importacion.producto),
                                  (NutrienteActivo, NutrienteActivo.EmpresaHomologada, NutrienteActivo.EmpresaImportadora)):
            sin = conn.execute(select(func.coalesce(hom, orig), func.count()).group_by(func.coalesce(hom, orig)).order_by(func.coalesce(hom, orig))).all()
            con = conn.execute(select(coalesce_homologado(hom, orig), func.count()).group_by(coalesce_homologado(hom, orig)).order_by(coalesce_homologado(hom, orig))).all()
            assert [tuple(f) for f in sin] == [tuple(f) for f in con]


def test_con_collations_distintas_el_coalesce_sin_helper_falla_y_con_helper_no():
    if _collations_coinciden():
        pytest.skip("en esta base las collations coinciden: el conflicto no se reproduce (es el caso de desarrollo)")
    with engine.connect() as conn:
        with pytest.raises(DBAPIError) as e:
            conn.execute(select(func.count(func.coalesce(Importacion.EmpresaHomologada, Importacion.importador).distinct()))).scalar()
        assert "446" in str(e.value) or "468" in str(e.value) or "4191" in str(e.value) or "intercalaci" in str(e.value).lower() or "collation" in str(e.value).lower()
    with engine.connect() as conn:
        assert conn.execute(select(func.count(Importacion.importador_efectivo.distinct()))).scalar() is not None


# ---------------------------------------------------------------------------------------------
# 4) Prueba de humo SQL (la misma del runner) y script 29
# ---------------------------------------------------------------------------------------------

def _bloque(archivo: Path, nombre: str) -> str:
    texto = archivo.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    m = re.search(rf"-- >>> PRUEBA DE HUMO {nombre}\n.*?-- <<< PRUEBA DE HUMO {nombre}\n", texto, flags=re.S)
    assert m, f"falta el bloque {nombre} en {archivo.name}"
    return m.group(0)


@pytest.mark.parametrize("script,bloques", [
    ("26_homologacion_empresas.sql", ["EMPRESAS"]),
    ("27_homologacion_nombres_comerciales.sql", ["NOMBRES"]),
    ("29_alinear_collation_homologadas.sql", ["EMPRESAS", "NOMBRES"]),
])
def test_la_prueba_de_humo_de_cada_script_es_identica_a_la_del_runner(script, bloques):
    for nombre in bloques:
        assert _bloque(DEPLOY / script, nombre) == _bloque(DEPLOY / "prueba_humo_dashboards.sql", nombre)


def test_la_prueba_de_humo_usa_la_misma_expresion_que_la_aplicacion():
    humo = (DEPLOY / "prueba_humo_dashboards.sql").read_text(encoding="utf-8")
    assert sql_coalesce_homologado("EmpresaHomologada", "EmpresaImportadora") in humo
    assert sql_coalesce_homologado("EmpresaHomologada", "importador") in humo
    assert sql_coalesce_homologado("NombreComercialHomologado", "producto") in humo


def test_la_prueba_de_humo_responde_sin_error_contra_la_base():
    humo = DEPLOY / "prueba_humo_dashboards.sql"
    with engine.connect() as conn:
        for nombre in ("EMPRESAS", "NOMBRES"):
            bloque = _bloque(humo, nombre).replace("SET NOCOUNT ON;", "")
            filas = conn.execute(text(bloque)).all()
            assert filas and all(f[2] == "OK" for f in filas)


def test_script_29_en_vista_previa_no_cambia_nada_y_reporta_las_collations():
    """Corre el script 29 con @SoloVistaPrevia = 1 contra la base de pruebas: no cambia nada y no da error."""
    sql = (DEPLOY / "29_alinear_collation_homologadas.sql").read_text(encoding="utf-8-sig")
    sql = re.sub(r"(?im)^\s*USE\s+PIQ_IA\s*;", "", sql).replace("DECLARE @SoloVistaPrevia BIT = 0;", "DECLARE @SoloVistaPrevia BIT = 1;")
    antes = _collations_actuales()
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        mensajes = []
        for lote in re.split(r"(?im)^\s*GO\s*$", sql):
            if lote.strip():
                cur.execute(lote)
                while True:
                    mensajes += [m[1] for m in (cur.messages or [])]
                    if not cur.nextset():
                        break
        raw.commit()
    finally:
        # el script deja SET NOCOUNT ON en la sesion: se descarta la conexion para no contaminar el pool (rowcount = -1 en otras pruebas)
        raw.invalidate()
    assert _collations_actuales() == antes
    assert any("@SoloVistaPrevia = 1" in m for m in mensajes)
    if _collations_coinciden():
        assert any("ya coinciden" in m for m in mensajes)


def _collations_actuales() -> list:
    with engine.connect() as conn:
        return [(t, h, _collation(conn, t, h)) for t, h, _ in PARES]

"""Mantenimiento de la homologación de nombres comerciales (pantalla de administración, Plaguicidas y Nutrientes).

Mismo modelo que la homologación de empresas (services/homologacion_empresas.py) pero sobre dos catálogos distintos, descritos por
una Config:
  - Plaguicidas: dbo.CatalogoNombresComerciales (script 27) -> dbo.Importacion.NombreComercialHomologado; los datos son los
    nombres de dbo.Importacion.producto.
  - Nutrientes: se REUTILIZA dbo.CatalogoAgrupadorNutrientes (ProductoAgrupado es el nombre estándar), que ya se sincroniza con
    sincronizar_agrupador_nutrientes; los datos son los NombreComercial de los activos (vw_NutrientesActivos). Un nombre sin
    entrada en el catálogo es un nombre "nuevo sin homologar".

Un GRUPO es el conjunto de claves con el mismo nombre estándar; sus VARIANTES son los nombres originales tal como vienen en los
datos. Los datos originales nunca se modifican: cada operación cambia el catálogo (nombre, Confirmada, FechaMod, UsuarioMod) y
sincroniza las filas ya cargadas en la misma transacción; quien llama hace el commit (o el rollback si hay un error).

Nada une por orden de palabras ni por errores de tipeo: las variantes que difieren solo en mayúsculas, tildes o puntuación (Plaguicidas)
comparten clave y se tratan como el mismo nombre; el resto lo une el administrador a mano o con el Excel estándar.
"""

import io
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.services.homologacion_empresas import ESTADOS, ErrorHomologacion
from app.services.nombres_comerciales import sincronizar_nombres_plaguicidas
from app.services.sincronizacion_agrupador import _normalizar_sql, sincronizar_agrupador_nutrientes

_BIN2 = "COLLATE Latin1_General_BIN2"
MAX_FILAS_EXCEL = 20000
TAMANO_LOTE_CLAVES = 400


@dataclass(frozen=True)
class Config:
    tipo: str
    etiqueta: str
    tabla: str
    col_clave: str
    col_nombre: str
    max_len: int
    # SQL que devuelve (nombre, filas, cif, clave) por nombre original distinto; {filtro} = condición extra opcional
    sql_variantes: str
    filtro_sin_homologar: str
    sincronizar: Callable[[Session], int]
    # SQL que devuelve la clave de un literal: SELECT <expr> con :t
    sql_clave: str
    sql_insertar: str
    tiene_codigo: bool = False
    columnas_extra_select: list[str] = field(default_factory=list)


def _sql_variantes_plaguicidas() -> str:
    return f"""
        SELECT nombre, filas, cif, dbo.fn_ClaveNombreComercial(nombre) AS clave
        FROM (
            SELECT producto {_BIN2} AS nombre, COUNT(*) AS filas, SUM(CAST(cif_USD AS FLOAT)) AS cif
            FROM dbo.Importacion
            WHERE producto IS NOT NULL AND LTRIM(RTRIM(producto)) <> N'' {{filtro}}
            GROUP BY producto {_BIN2}
        ) d"""


def _sql_variantes_nutrientes() -> str:
    return f"""
        SELECT nombre, filas, cif, {_normalizar_sql("nombre")} AS clave
        FROM (
            SELECT NombreComercial {_BIN2} AS nombre, COUNT(*) AS filas, SUM(CAST(CIF_dolares AS FLOAT)) AS cif
            FROM dbo.vw_NutrientesActivos
            WHERE NombreComercial IS NOT NULL AND LTRIM(RTRIM(NombreComercial)) <> N'' {{filtro}}
            GROUP BY NombreComercial {_BIN2}
        ) d"""


CONFIG_PLAGUICIDAS = Config(
    tipo="plaguicidas",
    etiqueta="Plaguicidas",
    tabla="dbo.CatalogoNombresComerciales",
    col_clave="NombreKey",
    col_nombre="NombreHomologado",
    max_len=400,
    sql_variantes=_sql_variantes_plaguicidas(),
    filtro_sin_homologar="AND NombreComercialHomologado IS NULL",
    sincronizar=sincronizar_nombres_plaguicidas,
    sql_clave="SELECT dbo.fn_ClaveNombreComercial(:t)",
    sql_insertar="""
        INSERT INTO dbo.CatalogoNombresComerciales (NombreKey, NombreHomologado, Confirmada, FechaMod, UsuarioMod)
        VALUES (:clave, :nombre, 1, GETDATE(), :usuario)""",
)

CONFIG_NUTRIENTES = Config(
    tipo="nutrientes",
    etiqueta="Nutrientes",
    tabla="dbo.CatalogoAgrupadorNutrientes",
    col_clave="NombreComercial_Key",
    col_nombre="ProductoAgrupado",
    max_len=150,
    sql_variantes=_sql_variantes_nutrientes(),
    filtro_sin_homologar="AND ProductoAgrupado IS NULL",
    sincronizar=sincronizar_agrupador_nutrientes,
    sql_clave=f"SELECT {_normalizar_sql(':t')}",
    sql_insertar="""
        INSERT INTO dbo.CatalogoAgrupadorNutrientes (NombreComercial_Key, ProductoAgrupado, Codigo, FechaMod, Excluido, Confirmada, UsuarioMod)
        VALUES (:clave, :nombre, :codigo, GETDATE(), 0, 1, :usuario)""",
    tiene_codigo=True,
)

CONFIGS = {c.tipo: c for c in (CONFIG_PLAGUICIDAS, CONFIG_NUTRIENTES)}


def obtener_config(tipo: str) -> Config:
    cfg = CONFIGS.get(tipo)
    if cfg is None:
        raise ErrorHomologacion(f"Tipo inválido: {tipo}. Use: plaguicidas o nutrientes.", 404)
    return cfg


@dataclass
class _Variante:
    clave: str
    nombre: str
    filas: int = 0
    cif: float = 0.0


def _plano(texto: str | None) -> str:
    s = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper()


# ---------------------------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------------------------

def _variantes_en_datos(db: Session, cfg: Config, solo_sin_homologar: bool = False) -> list[_Variante]:
    sql = cfg.sql_variantes.replace("{filtro}", cfg.filtro_sin_homologar if solo_sin_homologar else "")
    variantes: dict[tuple[str, str], _Variante] = {}
    for nombre, filas, cif, clave in db.execute(text(sql)).all():
        if clave is None:
            continue
        v = variantes.setdefault((clave, nombre), _Variante(clave=clave, nombre=nombre))
        v.filas += int(filas)
        v.cif += float(cif or 0)
    return list(variantes.values())


def _catalogo(db: Session, cfg: Config) -> dict[str, dict]:
    filas = db.execute(text(
        f"SELECT {cfg.col_clave}, {cfg.col_nombre}, Confirmada, FechaMod, UsuarioMod FROM {cfg.tabla} "
        f"WHERE {cfg.col_nombre} IS NOT NULL"
    )).all()
    return {k: {"nombre": n, "confirmada": bool(c), "fecha_mod": f, "usuario_mod": u} for k, n, c, f, u in filas}


def _nombres_usuarios(db: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {i: n for i, n in db.query(Usuario.UsuarioId, Usuario.NombreUsuario).filter(Usuario.UsuarioId.in_(ids)).all()}


def construir_grupos(db: Session, cfg: Config) -> list[dict]:
    """Todos los grupos del catálogo con sus variantes, ordenados por CIF USD total descendente."""
    catalogo = _catalogo(db, cfg)
    por_clave: dict[str, list[_Variante]] = {}
    for v in _variantes_en_datos(db, cfg):
        if v.clave in catalogo:
            por_clave.setdefault(v.clave, []).append(v)

    grupos: dict[str, dict] = {}
    for clave, info in catalogo.items():
        g = grupos.setdefault(info["nombre"].casefold(), {"nombre": info["nombre"], "claves": [], "confirmada": True,
                                                          "fecha_mod": None, "usuario_mod": None})
        g["claves"].append(clave)
        g["confirmada"] = g["confirmada"] and info["confirmada"]
        if info["fecha_mod"] is not None and (g["fecha_mod"] is None or info["fecha_mod"] > g["fecha_mod"]):
            g["fecha_mod"], g["usuario_mod"] = info["fecha_mod"], info["usuario_mod"]

    nombres_usuario = _nombres_usuarios(db, {g["usuario_mod"] for g in grupos.values() if g["usuario_mod"] is not None})
    salida = []
    for g in grupos.values():
        variantes = sorted((v for c in g["claves"] for v in por_clave.get(c, [])), key=lambda v: (-v.cif, v.nombre))
        g.update(
            variantes=variantes, filas=sum(v.filas for v in variantes), cif=sum(v.cif for v in variantes),
            usuario_mod=nombres_usuario.get(g["usuario_mod"]) if g["usuario_mod"] is not None else None,
            texto=_plano(" ".join([g["nombre"]] + g["claves"] + [v.nombre for v in variantes])),
        )
        salida.append(g)
    salida.sort(key=lambda g: (-g["cif"], g["nombre"]))
    return salida


def _cumple_busqueda(g: dict, busqueda: str | None) -> bool:
    return not busqueda or _plano(busqueda.strip()) in g["texto"]


def _validar_estado(estado: str) -> None:
    if estado not in ESTADOS:
        raise ErrorHomologacion(f"Estado inválido: {estado}. Use: {', '.join(ESTADOS)}.")


def _dict_variante(v: _Variante) -> dict:
    return {"clave": v.clave, "nombre_original": v.nombre, "filas": v.filas, "cif_usd": round(v.cif, 2)}


def _dict_grupo(g: dict) -> dict:
    return {
        "nombre_homologado": g["nombre"], "confirmada": g["confirmada"], "claves": sorted(g["claves"]),
        "filas": g["filas"], "cif_usd": round(g["cif"], 2), "puede_separar": len(g["claves"]) > 1,
        "fecha_mod": g["fecha_mod"], "usuario_mod": g["usuario_mod"],
        "variantes": [_dict_variante(v) for v in g["variantes"]],
    }


def listar_grupos(db: Session, cfg: Config, busqueda: str | None, estado: str, pagina: int, tamano_pagina: int) -> dict:
    _validar_estado(estado)
    todos = [g for g in construir_grupos(db, cfg) if _cumple_busqueda(g, busqueda)]
    pendientes = [g for g in todos if not g["confirmada"]]
    confirmadas = [g for g in todos if g["confirmada"]]
    filtrados = {"todas": todos, "pendientes": pendientes, "confirmadas": confirmadas}[estado]
    ini = (pagina - 1) * tamano_pagina
    return {
        "total": len(filtrados), "pagina": pagina, "tamano_pagina": tamano_pagina,
        "pendientes_en_filtro": len(pendientes), "total_pendientes": len(pendientes), "total_confirmadas": len(confirmadas),
        "grupos": [_dict_grupo(g) for g in filtrados[ini:ini + tamano_pagina]],
    }


def nuevas_sin_homologar(db: Session, cfg: Config, busqueda: str | None, pagina: int, tamano_pagina: int) -> dict:
    """Nombres que están en los datos y todavía no tienen entrada en el catálogo (una fila por clave), por CIF descendente."""
    catalogo = _catalogo(db, cfg)
    por_clave: dict[str, list[_Variante]] = {}
    for v in _variantes_en_datos(db, cfg, solo_sin_homologar=True):
        if v.clave not in catalogo:
            por_clave.setdefault(v.clave, []).append(v)
    filas = []
    for clave, vs in por_clave.items():
        vs.sort(key=lambda v: (-v.cif, v.nombre))
        fila = {"clave": clave, "nombre_ejemplo": vs[0].nombre, "variantes": [_dict_variante(v) for v in vs],
                "filas": sum(v.filas for v in vs), "cif_usd": round(sum(v.cif for v in vs), 2)}
        if _cumple_busqueda({"texto": _plano(" ".join([clave] + [v.nombre for v in vs]))}, busqueda):
            filas.append(fila)
    filas.sort(key=lambda f: (-f["cif_usd"], f["nombre_ejemplo"]))
    ini = (pagina - 1) * tamano_pagina
    return {"total": len(filas), "pagina": pagina, "tamano_pagina": tamano_pagina, "nombres": filas[ini:ini + tamano_pagina]}


def _claves_nuevas(db: Session, cfg: Config) -> set[str]:
    catalogo = _catalogo(db, cfg)
    return {v.clave for v in _variantes_en_datos(db, cfg, solo_sin_homologar=True) if v.clave not in catalogo}


# ---------------------------------------------------------------------------------------------
# Escritura (el commit lo hace quien llama)
# ---------------------------------------------------------------------------------------------

def _validar_nombre(cfg: Config, nombre: str) -> None:
    if len(nombre) > cfg.max_len:
        raise ErrorHomologacion(f"El nombre es demasiado largo (máximo {cfg.max_len} caracteres para {cfg.etiqueta}).")


def _claves_existentes(db: Session, cfg: Config, claves: list[str]) -> dict[str, str]:
    unicas = list(dict.fromkeys(c for c in claves if c and c.strip()))
    if not unicas:
        raise ErrorHomologacion("No se indicó ninguna clave.")
    catalogo = _catalogo(db, cfg)
    faltan = [c for c in unicas if c not in catalogo]
    if faltan:
        raise ErrorHomologacion(f"Claves que no existen en el catálogo: {', '.join(faltan)}.", 404)
    return {c: catalogo[c]["nombre"] for c in unicas}


def _claves_del_grupo(db: Session, cfg: Config, nombre: str) -> list[str]:
    return [r[0] for r in db.execute(
        text(f"SELECT {cfg.col_clave} FROM {cfg.tabla} WHERE {cfg.col_nombre} = :n"), {"n": nombre}
    )]


def _nombre_en_uso_fuera(db: Session, cfg: Config, nombre: str, claves_propias: set[str]) -> bool:
    return bool(set(_claves_del_grupo(db, cfg, nombre)) - claves_propias)


def _marcar(db: Session, cfg: Config, claves: list[str], nombre: str | None, usuario_id: int | None, confirmada: bool = True) -> None:
    # El nombre solo se toca si viene (no ISNULL(:nombre, col): con un NULL sin tipo SQL Server lo trunca a 1 caracter)
    set_nombre = f"{cfg.col_nombre} = :nombre, " if nombre is not None else ""
    extra = {"nombre": nombre} if nombre is not None else {}
    for clave in claves:
        db.execute(
            text(f"UPDATE {cfg.tabla} SET {set_nombre}Confirmada = :conf, FechaMod = GETDATE(), UsuarioMod = :usuario "
                 f"WHERE {cfg.col_clave} = :clave"),
            {**extra, "conf": 1 if confirmada else 0, "usuario": usuario_id, "clave": clave},
        )


def _resultado(db: Session, cfg: Config, mensaje: str, nombre: str | None, claves: int, grupos: int) -> dict:
    filas = cfg.sincronizar(db)
    return {"mensaje": mensaje, "nombre_oficial": nombre, "claves_afectadas": claves, "grupos_afectados": grupos,
            "filas_sincronizadas": filas}


def unir(db: Session, cfg: Config, claves: list[str], nombre_oficial: str, usuario_id: int) -> dict:
    _validar_nombre(cfg, nombre_oficial)
    actuales = _claves_existentes(db, cfg, claves)
    grupos_distintos = {n.casefold() for n in actuales.values()}
    if len(actuales) < 2 or len(grupos_distintos) < 2:
        raise ErrorHomologacion("Selecciona al menos dos grupos distintos: un grupo no se puede unir consigo mismo.")
    if _nombre_en_uso_fuera(db, cfg, nombre_oficial, set(actuales)):
        raise ErrorHomologacion(
            f"Ya existe otro grupo llamado «{nombre_oficial}» que no está en la selección. Inclúyelo en la unión "
            "o elige otro nombre.", 409)
    _marcar(db, cfg, list(actuales), nombre_oficial, usuario_id)
    return _resultado(db, cfg, f"Se unieron {len(grupos_distintos)} grupos bajo «{nombre_oficial}».", nombre_oficial,
                      len(actuales), len(grupos_distintos))


def renombrar(db: Session, cfg: Config, nombre_actual: str, nombre_nuevo: str, usuario_id: int) -> dict:
    _validar_nombre(cfg, nombre_nuevo)
    claves = _claves_del_grupo(db, cfg, nombre_actual)
    if not claves:
        raise ErrorHomologacion(f"No existe un grupo llamado «{nombre_actual}».", 404)
    if _nombre_en_uso_fuera(db, cfg, nombre_nuevo, set(claves)):
        raise ErrorHomologacion(f"Ya existe otro grupo llamado «{nombre_nuevo}». Para fusionarlos usa «Unir».", 409)
    _marcar(db, cfg, claves, nombre_nuevo, usuario_id)
    return _resultado(db, cfg, f"Grupo renombrado a «{nombre_nuevo}».", nombre_nuevo, len(claves), 1)


def _mejor_nombre_por_clave(db: Session, cfg: Config) -> dict[str, str]:
    mejor: dict[str, _Variante] = {}
    for v in _variantes_en_datos(db, cfg):
        actual = mejor.get(v.clave)
        if actual is None or (-v.cif, v.nombre) < (-actual.cif, actual.nombre):
            mejor[v.clave] = v
    return {c: v.nombre for c, v in mejor.items()}


def separar(db: Session, cfg: Config, clave: str, usuario_id: int) -> dict:
    actuales = _claves_existentes(db, cfg, [clave])
    clave = next(iter(actuales))
    nombre_grupo = actuales[clave]
    del_grupo = _claves_del_grupo(db, cfg, nombre_grupo)
    if len(del_grupo) < 2:
        raise ErrorHomologacion(
            "Esa variante ya está sola en su grupo. Las variantes que solo difieren en mayúsculas, tildes o puntuación "
            "comparten la misma clave y no se pueden separar entre sí.")
    mejores = _mejor_nombre_por_clave(db, cfg)
    nombre_propio = mejores.get(clave)
    if not nombre_propio:
        raise ErrorHomologacion("No se encontró el nombre original de esa variante en los datos.", 404)
    _validar_nombre(cfg, nombre_propio)
    restantes = [c for c in del_grupo if c != clave]
    if nombre_propio.casefold() == nombre_grupo.casefold():
        candidatos = [mejores[c] for c in restantes if c in mejores and mejores[c].casefold() != nombre_propio.casefold()]
        if not candidatos:
            raise ErrorHomologacion(
                "No se puede separar: el resto del grupo no tiene un nombre original distinto con el cual quedarse. "
                "Renombra el grupo y vuelve a intentar.", 409)
        _marcar(db, cfg, restantes, candidatos[0], usuario_id, confirmada=True)
    elif _nombre_en_uso_fuera(db, cfg, nombre_propio, {clave}):
        raise ErrorHomologacion(f"Ya existe un grupo llamado «{nombre_propio}»; renómbralo antes de separar.", 409)
    _marcar(db, cfg, [clave], nombre_propio, usuario_id)
    return _resultado(db, cfg, f"Variante separada: ahora es el grupo «{nombre_propio}».", nombre_propio, 1, 1)


def confirmar(db: Session, cfg: Config, nombres: list[str], usuario_id: int) -> dict:
    claves: list[str] = []
    for nombre in dict.fromkeys(n for n in nombres if n and n.strip()):
        del_grupo = _claves_del_grupo(db, cfg, nombre)
        if not del_grupo:
            raise ErrorHomologacion(f"No existe un grupo llamado «{nombre}».", 404)
        claves.extend(del_grupo)
    claves = list(dict.fromkeys(claves))
    if not claves:
        raise ErrorHomologacion("No se indicó ningún grupo.")
    _marcar(db, cfg, claves, None, usuario_id)
    n_grupos = len({n.casefold() for n in nombres if n and n.strip()})
    return _resultado(db, cfg, f"{n_grupos} grupo(s) confirmado(s).", None, len(claves), n_grupos)


def confirmar_pendientes(db: Session, cfg: Config, busqueda: str | None, usuario_id: int) -> dict:
    pendientes = [g for g in construir_grupos(db, cfg) if not g["confirmada"] and _cumple_busqueda(g, busqueda)]
    if not pendientes:
        return {"mensaje": "No hay grupos pendientes en el filtro actual.", "nombre_oficial": None,
                "claves_afectadas": 0, "grupos_afectados": 0, "filas_sincronizadas": 0}
    claves = [c for g in pendientes for c in g["claves"]]
    _marcar(db, cfg, claves, None, usuario_id)
    return _resultado(db, cfg, f"{len(pendientes)} grupo(s) pendiente(s) confirmado(s).", None, len(claves), len(pendientes))


def _codigo_del_grupo(db: Session, cfg: Config, nombre: str) -> str | None:
    if not cfg.tiene_codigo:
        return None
    return db.execute(
        text(f"SELECT TOP 1 Codigo FROM {cfg.tabla} WHERE {cfg.col_nombre} = :n AND Codigo IS NOT NULL"), {"n": nombre}
    ).scalar()


def _insertar_clave(db: Session, cfg: Config, clave: str, nombre: str, usuario_id: int, codigo: str | None = None) -> None:
    params = {"clave": clave, "nombre": nombre, "usuario": usuario_id}
    if cfg.tiene_codigo:
        params["codigo"] = codigo
    db.execute(text(cfg.sql_insertar), params)


def asignar_nuevas(db: Session, cfg: Config, claves: list[str], nombre_grupo: str, grupo_nuevo: bool, usuario_id: int) -> dict:
    _validar_nombre(cfg, nombre_grupo)
    unicas = list(dict.fromkeys(c for c in claves if c and c.strip()))
    if not unicas:
        raise ErrorHomologacion("No se indicó ningún nombre.")
    catalogo = _catalogo(db, cfg)
    ya = [c for c in unicas if c in catalogo]
    if ya:
        raise ErrorHomologacion(f"Esos nombres ya están en el catálogo: {', '.join(ya)}.", 409)
    validas = _claves_nuevas(db, cfg)
    desconocidas = [c for c in unicas if c not in validas]
    if desconocidas:
        raise ErrorHomologacion(
            f"Esos nombres no están en la lista de nuevos sin homologar: {', '.join(desconocidas)}.", 404)
    existentes = _claves_del_grupo(db, cfg, nombre_grupo)
    if grupo_nuevo and existentes:
        raise ErrorHomologacion(f"Ya existe un grupo llamado «{nombre_grupo}»; asígnalos a ese grupo.", 409)
    if not grupo_nuevo and not existentes:
        raise ErrorHomologacion(f"No existe un grupo llamado «{nombre_grupo}».", 404)
    nombre_final = nombre_grupo if grupo_nuevo else catalogo[existentes[0]]["nombre"]
    codigo = None if grupo_nuevo else _codigo_del_grupo(db, cfg, nombre_final)
    for clave in unicas:
        _insertar_clave(db, cfg, clave, nombre_final, usuario_id, codigo)
    return _resultado(db, cfg, f"{len(unicas)} nombre(s) asignado(s) a «{nombre_final}».", nombre_final, len(unicas), 1)


# ---------------------------------------------------------------------------------------------
# Excel estándar: dos columnas (nombre comercial / nombre estándar)
# ---------------------------------------------------------------------------------------------

def _leer_excel(contenido: bytes) -> list[tuple[int, str, str]]:
    """Filas (número de fila del Excel, nombre comercial, nombre estándar) de la primera hoja. Si la primera fila parece un
    encabezado (contiene «nombre»/«comercial»/«estándar») se salta. Las filas totalmente vacías se ignoran."""
    try:
        df = pd.read_excel(io.BytesIO(contenido), sheet_name=0, header=None, dtype=str)
    except Exception as exc:
        raise ErrorHomologacion(f"No se pudo leer el Excel: {exc}") from exc
    if df.shape[1] < 2:
        raise ErrorHomologacion("El Excel debe tener dos columnas: nombre comercial y nombre estándar.")
    df = df.iloc[:, :2]
    if len(df) > MAX_FILAS_EXCEL:
        raise ErrorHomologacion(f"El Excel tiene demasiadas filas (máximo {MAX_FILAS_EXCEL}).")
    filas: list[tuple[int, str, str]] = []
    for pos, (a, b) in enumerate(df.itertuples(index=False, name=None)):
        a = "" if pd.isna(a) else " ".join(str(a).split())
        b = "" if pd.isna(b) else " ".join(str(b).split())
        if pos == 0 and "NOMBRE" in _plano(a + " " + b):
            continue
        if not a and not b:
            continue
        filas.append((pos + 1, a, b))
    return filas


def _claves_de(db: Session, cfg: Config, nombres: list[str]) -> dict[str, str | None]:
    """Clave de cada texto, calculada en SQL (la misma de las cargas y del catálogo), por lotes."""
    unicos = list(dict.fromkeys(nombres))
    claves: dict[str, str | None] = {}
    for i in range(0, len(unicos), TAMANO_LOTE_CLAVES):
        lote = unicos[i:i + TAMANO_LOTE_CLAVES]
        valores = ", ".join(f"(:v{j})" for j in range(len(lote)))
        expr = cfg.sql_clave.replace("SELECT ", "", 1).replace(":t", "v.t")
        filas = db.execute(
            text(f"SELECT v.t, {expr} FROM (VALUES {valores}) AS v(t)"), {f"v{j}": n for j, n in enumerate(lote)}
        ).all()
        for t, k in filas:
            claves[t] = k
    return claves


def procesar_excel(db: Session, cfg: Config, contenido: bytes, aplicar: bool, usuario_id: int) -> dict:
    """Vista previa (aplicar=False) o aplicación (aplicar=True, una sola transacción; el commit lo hace quien llama) del Excel
    estándar. Cada fila dice «este nombre comercial es el mismo que este nombre estándar».
      - se_uniran: el nombre ya está en el catálogo con otro nombre estándar -> pasa al indicado (Confirmada = 1)
      - nuevos: el nombre no estaba en el catálogo -> se agrega con el nombre estándar indicado (Confirmada = 1)
      - sin_cambio: ya tenía exactamente ese nombre estándar
      - conflictos: no se aplican (celda vacía, nombre demasiado largo, el mismo nombre con dos estándares distintos en el archivo,
        o cadena A -> B y B -> C)."""
    filas = _leer_excel(contenido)
    if not filas:
        raise ErrorHomologacion("El Excel no tiene filas con datos.")
    claves = _claves_de(db, cfg, [a for _, a, _ in filas if a] + [b for _, _, b in filas if b])
    catalogo = _catalogo(db, cfg)
    por_clave_std: dict[str, set[str]] = {}
    for _, a, b in filas:
        if a and b and claves.get(a):
            por_clave_std.setdefault(claves[a], set()).add(b.casefold())

    items: list[dict] = []
    vistos: set[str] = set()
    for nfila, a, b in filas:
        item = {"fila": nfila, "nombre": a, "nombre_estandar": b, "clave": claves.get(a) if a else None, "estado": "", "motivo": None}
        if not a or not b:
            item.update(estado="conflicto", motivo="Falta el nombre comercial o el nombre estándar.")
        elif item["clave"] is None:
            item.update(estado="conflicto", motivo="El nombre comercial queda vacío al normalizarlo.")
        elif len(b) > cfg.max_len or len(a) > 400:
            item.update(estado="conflicto", motivo=f"Nombre demasiado largo (máximo {cfg.max_len} caracteres para el estándar).")
        elif len(por_clave_std[item["clave"]]) > 1:
            item.update(estado="conflicto", motivo="El mismo nombre aparece con dos nombres estándar distintos en el archivo.")
        elif claves.get(b) and claves[b] != item["clave"] and claves[b] in por_clave_std and b.casefold() not in por_clave_std[claves[b]]:
            item.update(estado="conflicto", motivo="Cadena: el nombre estándar de esta fila es a su vez un nombre comercial con otro estándar.")
        elif item["clave"] in vistos:
            item.update(estado="repetida", motivo="Fila repetida (se aplica una sola vez).")
        else:
            vistos.add(item["clave"])
            actual = catalogo.get(item["clave"])
            if actual is None:
                item["estado"] = "nuevo"
            elif actual["nombre"] == b:
                item["estado"] = "sin_cambio"
            else:
                item.update(estado="se_unira", nombre_actual=actual["nombre"])
        items.append(item)

    conteo = {e: sum(1 for i in items if i["estado"] == e) for e in ("se_unira", "nuevo", "sin_cambio", "conflicto", "repetida")}
    resultado = {
        "aplicado": False, "filas_leidas": len(filas), "se_uniran": conteo["se_unira"], "nuevos": conteo["nuevo"],
        "sin_cambio": conteo["sin_cambio"], "conflictos": conteo["conflicto"], "repetidas": conteo["repetida"],
        "detalle": [i for i in items if i["estado"] in ("se_unira", "nuevo", "conflicto")][:200],
        "filas_sincronizadas": 0, "mensaje": "",
    }
    if not aplicar:
        resultado["mensaje"] = (f"Vista previa: {conteo['se_unira']} se unirán, {conteo['nuevo']} son nuevos, "
                                f"{conteo['sin_cambio']} no cambian y {conteo['conflicto']} tienen conflicto (no se aplican).")
        return resultado

    for i in items:
        if i["estado"] == "se_unira":
            _marcar(db, cfg, [i["clave"]], i["nombre_estandar"], usuario_id)
        elif i["estado"] == "nuevo":
            _insertar_clave(db, cfg, i["clave"], i["nombre_estandar"], usuario_id, _codigo_del_grupo(db, cfg, i["nombre_estandar"]))
    resultado["filas_sincronizadas"] = cfg.sincronizar(db)
    resultado["aplicado"] = True
    resultado["mensaje"] = (f"Excel aplicado: {conteo['se_unira']} unidos, {conteo['nuevo']} nuevos, "
                            f"{conteo['conflicto']} con conflicto sin aplicar.")
    return resultado

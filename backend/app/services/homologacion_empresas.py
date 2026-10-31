"""Mantenimiento de la homologación de empresas (pantalla de administración).

Trabaja sobre dbo.CatalogoEmpresas (una fila por clave normalizada, ver services/empresas.py). Un GRUPO es el conjunto de
claves que comparten el mismo EmpresaHomologada; sus VARIANTES son los nombres originales, tal como vienen en los datos
(dbo.Importacion.importador y los activos de dbo.Nutrientes.EmpresaImportadora). Los datos originales nunca se modifican:
cada operación cambia el catálogo (EmpresaHomologada, Confirmada, FechaMod, UsuarioMod) y luego sincroniza las filas ya
cargadas con sincronizar_empresas() en la misma transacción; quien llama hace el commit (o rollback si hay error).

La clave de cada variante la calcula dbo.fn_ClaveEmpresa en SQL (la misma de las cargas), solo sobre los nombres distintos
de cada tabla, no fila por fila. Variantes que difieren solo en mayúsculas, puntuación o "S.A." comparten clave: no se pueden
separar entre sí, solo se separan claves distintas.
"""

import unicodedata
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.services.empresas import sincronizar_empresas

_BIN2 = "COLLATE Latin1_General_BIN2"
ORIGENES = ("todas", "P", "N", "ambas")
ESTADOS = ("todas", "pendientes", "confirmadas")


class ErrorHomologacion(Exception):
    def __init__(self, mensaje: str, status_code: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.status_code = status_code


@dataclass
class _Monto:
    filas: int = 0
    cif: float = 0.0


@dataclass
class _Variante:
    clave: str
    nombre: str
    p: _Monto = field(default_factory=_Monto)
    n: _Monto = field(default_factory=_Monto)

    @property
    def cif_total(self) -> float:
        return self.p.cif + self.n.cif


def _plano(texto: str | None) -> str:
    """Mayúsculas sin tildes, para buscar."""
    s = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper()


# ---------------------------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------------------------

def _variantes_en_datos(db: Session, solo_sin_homologar: bool = False) -> list[_Variante]:
    """Nombres originales distintos de ambas tablas con filas y CIF USD. Plaguicidas: todo dbo.Importacion; Nutrientes:
    solo los activos (vw_NutrientesActivos), igual que los tableros."""
    filtro = "AND EmpresaHomologada IS NULL" if solo_sin_homologar else ""
    filas = db.execute(text(f"""
        SELECT origen, nombre, filas, cif, dbo.fn_ClaveEmpresa(nombre) AS clave
        FROM (
            SELECT 'P' AS origen, importador {_BIN2} AS nombre, COUNT(*) AS filas, SUM(CAST(cif_USD AS FLOAT)) AS cif
            FROM dbo.Importacion
            WHERE importador IS NOT NULL AND LTRIM(RTRIM(importador)) <> N'' {filtro}
            GROUP BY importador {_BIN2}
            UNION ALL
            SELECT 'N', EmpresaImportadora {_BIN2}, COUNT(*), SUM(CAST(CIF_dolares AS FLOAT))
            FROM dbo.vw_NutrientesActivos
            WHERE EmpresaImportadora IS NOT NULL AND LTRIM(RTRIM(EmpresaImportadora)) <> N'' {filtro}
            GROUP BY EmpresaImportadora {_BIN2}
        ) d
    """)).all()
    variantes: dict[tuple[str, str], _Variante] = {}
    for origen, nombre, n_filas, cif, clave in filas:
        if clave is None:
            continue
        v = variantes.setdefault((clave, nombre), _Variante(clave=clave, nombre=nombre))
        monto = v.p if origen == "P" else v.n
        monto.filas += int(n_filas)
        monto.cif += float(cif or 0)
    return list(variantes.values())


def _catalogo(db: Session) -> dict[str, dict]:
    filas = db.execute(text(
        "SELECT EmpresaKey, EmpresaHomologada, Confirmada, FechaMod, UsuarioMod FROM dbo.CatalogoEmpresas"
    )).all()
    return {
        k: {"nombre": n, "confirmada": bool(c), "fecha_mod": f, "usuario_mod": u}
        for k, n, c, f, u in filas
    }


def _nombres_usuarios(db: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    filas = db.query(Usuario.UsuarioId, Usuario.NombreUsuario).filter(Usuario.UsuarioId.in_(ids)).all()
    return {i: n for i, n in filas}


def _origen_de(p: _Monto, n: _Monto) -> str:
    if p.filas and n.filas:
        return "ambas"
    if p.filas:
        return "P"
    if n.filas:
        return "N"
    return ""


def construir_grupos(db: Session) -> list[dict]:
    """Todos los grupos del catálogo con sus variantes, ordenados por CIF total descendente."""
    catalogo = _catalogo(db)
    por_clave: dict[str, list[_Variante]] = {}
    for v in _variantes_en_datos(db):
        if v.clave in catalogo:
            por_clave.setdefault(v.clave, []).append(v)

    grupos: dict[str, dict] = {}
    for clave, info in catalogo.items():
        # El catálogo compara nombres sin distinguir mayúsculas: el grupo se identifica igual
        g = grupos.setdefault(info["nombre"].casefold(), {"nombre": info["nombre"], "claves": [], "confirmada": True,
                                                          "fecha_mod": None, "usuario_mod": None})
        g["claves"].append(clave)
        g["confirmada"] = g["confirmada"] and info["confirmada"]
        if info["fecha_mod"] is not None and (g["fecha_mod"] is None or info["fecha_mod"] > g["fecha_mod"]):
            g["fecha_mod"], g["usuario_mod"] = info["fecha_mod"], info["usuario_mod"]

    nombres_usuario = _nombres_usuarios(db, {g["usuario_mod"] for g in grupos.values() if g["usuario_mod"] is not None})
    salida = []
    for g in grupos.values():
        variantes = [v for c in g["claves"] for v in por_clave.get(c, [])]
        variantes.sort(key=lambda v: (-v.cif_total, v.nombre))
        p, n = _Monto(), _Monto()
        for v in variantes:
            p.filas += v.p.filas
            p.cif += v.p.cif
            n.filas += v.n.filas
            n.cif += v.n.cif
        g.update(
            variantes=variantes, p=p, n=n, cif_total=p.cif + n.cif, origen=_origen_de(p, n),
            usuario_mod=nombres_usuario.get(g["usuario_mod"]) if g["usuario_mod"] is not None else None,
            texto=_plano(" ".join([g["nombre"]] + g["claves"] + [v.nombre for v in variantes])),
        )
        salida.append(g)
    salida.sort(key=lambda g: (-g["cif_total"], g["nombre"]))
    return salida


def _cumple_busqueda_origen(g: dict, busqueda: str | None, origen: str) -> bool:
    if busqueda and _plano(busqueda.strip()) not in g["texto"]:
        return False
    if origen == "P":
        return g["p"].filas > 0
    if origen == "N":
        return g["n"].filas > 0
    if origen == "ambas":
        return g["p"].filas > 0 and g["n"].filas > 0
    return True


def _validar_filtros(estado: str, origen: str) -> None:
    if estado not in ESTADOS:
        raise ErrorHomologacion(f"Estado inválido: {estado}. Use: {', '.join(ESTADOS)}.")
    if origen not in ORIGENES:
        raise ErrorHomologacion(f"Origen inválido: {origen}. Use: todas, P, N o ambas.")


def listar_grupos(db: Session, busqueda: str | None, estado: str, origen: str, pagina: int, tamano_pagina: int) -> dict:
    _validar_filtros(estado, origen)
    todos = [g for g in construir_grupos(db) if _cumple_busqueda_origen(g, busqueda, origen)]
    pendientes = [g for g in todos if not g["confirmada"]]
    confirmadas = [g for g in todos if g["confirmada"]]
    filtrados = {"todas": todos, "pendientes": pendientes, "confirmadas": confirmadas}[estado]
    ini = (pagina - 1) * tamano_pagina
    return {
        "total": len(filtrados),
        "pagina": pagina,
        "tamano_pagina": tamano_pagina,
        "pendientes_en_filtro": len(pendientes),
        "total_pendientes": len(pendientes),
        "total_confirmadas": len(confirmadas),
        "grupos": [_a_dict_grupo(g) for g in filtrados[ini:ini + tamano_pagina]],
    }


def _a_dict_monto(m: _Monto) -> dict:
    return {"filas": m.filas, "cif_usd": round(m.cif, 2)}


def _a_dict_grupo(g: dict) -> dict:
    return {
        "nombre_homologado": g["nombre"],
        "confirmada": g["confirmada"],
        "origen": g["origen"],
        "claves": sorted(g["claves"]),
        "plaguicidas": _a_dict_monto(g["p"]),
        "nutrientes": _a_dict_monto(g["n"]),
        "cif_total_usd": round(g["cif_total"], 2),
        "puede_separar": len(g["claves"]) > 1,
        "fecha_mod": g["fecha_mod"],
        "usuario_mod": g["usuario_mod"],
        "variantes": [
            {
                "clave": v.clave, "nombre_original": v.nombre,
                "plaguicidas": _a_dict_monto(v.p), "nutrientes": _a_dict_monto(v.n),
                "cif_total_usd": round(v.cif_total, 2),
            }
            for v in g["variantes"]
        ],
    }


def nuevas_sin_homologar(db: Session) -> dict:
    """Empresas registradas en dbo.log_ExcepcionesEmpresas (llegaron en cargas) cuya clave sigue fuera del catálogo y que
    todavía tienen filas sin homologar. Los montos son los actuales de los datos, no los del momento de la carga."""
    catalogo = _catalogo(db)
    log = db.execute(text("""
        SELECT EmpresaKey, Origen, MAX(FechaCorrida) AS ultima
        FROM dbo.log_ExcepcionesEmpresas
        WHERE EmpresaKey IS NOT NULL
        GROUP BY EmpresaKey, Origen
    """)).all()
    claves_log: dict[str, dict] = {}
    for clave, origen, ultima in log:
        if clave in catalogo:
            continue
        d = claves_log.setdefault(clave, {"origenes": set(), "ultima": None})
        d["origenes"].add(origen)
        if d["ultima"] is None or ultima > d["ultima"]:
            d["ultima"] = ultima
    if not claves_log:
        return {"total": 0, "empresas": []}

    por_clave: dict[str, list[_Variante]] = {}
    for v in _variantes_en_datos(db, solo_sin_homologar=True):
        if v.clave in claves_log:
            por_clave.setdefault(v.clave, []).append(v)

    empresas = []
    for clave, d in claves_log.items():
        variantes = sorted(por_clave.get(clave, []), key=lambda v: (-v.cif_total, v.nombre))
        if not variantes:
            continue                   # ya no hay filas con esa empresa (se recargó el año): nada que homologar
        p, n = _Monto(), _Monto()
        for v in variantes:
            p.filas += v.p.filas
            p.cif += v.p.cif
            n.filas += v.n.filas
            n.cif += v.n.cif
        empresas.append({
            "clave": clave, "nombre_ejemplo": variantes[0].nombre, "origenes": sorted(d["origenes"]),
            "plaguicidas": _a_dict_monto(p), "nutrientes": _a_dict_monto(n), "cif_total_usd": round(p.cif + n.cif, 2),
            "ultima_carga": d["ultima"],
        })
    empresas.sort(key=lambda e: (-e["cif_total_usd"], e["nombre_ejemplo"]))
    return {"total": len(empresas), "empresas": empresas}


# ---------------------------------------------------------------------------------------------
# Escritura (el commit lo hace quien llama)
# ---------------------------------------------------------------------------------------------

def _claves_existentes(db: Session, claves: list[str]) -> dict[str, str]:
    """clave -> nombre homologado actual; ErrorHomologacion 404 si alguna no está en el catálogo."""
    unicas = list(dict.fromkeys(c for c in claves if c and c.strip()))
    if not unicas:
        raise ErrorHomologacion("No se indicó ninguna clave.")
    catalogo = _catalogo(db)
    faltan = [c for c in unicas if c not in catalogo]
    if faltan:
        raise ErrorHomologacion(f"Claves que no existen en el catálogo: {', '.join(faltan)}.", 404)
    return {c: catalogo[c]["nombre"] for c in unicas}


def _claves_del_grupo(db: Session, nombre: str) -> list[str]:
    """Claves cuyo nombre homologado es `nombre` (sin distinguir mayúsculas, igual que el catálogo)."""
    return [r[0] for r in db.execute(
        text("SELECT EmpresaKey FROM dbo.CatalogoEmpresas WHERE EmpresaHomologada = :n"), {"n": nombre}
    )]


def _nombre_en_uso_fuera(db: Session, nombre: str, claves_propias: set[str]) -> bool:
    otras = set(_claves_del_grupo(db, nombre)) - claves_propias
    return bool(otras)


def _marcar(db: Session, claves: list[str], nombre: str | None, usuario_id: int | None, confirmada: bool = True) -> None:
    # El nombre solo se toca si viene (no ISNULL(:nombre, col): con un NULL sin tipo SQL Server lo trunca a 1 caracter)
    set_nombre = "EmpresaHomologada = :nombre, " if nombre is not None else ""
    params_extra = {"nombre": nombre} if nombre is not None else {}
    for clave in claves:
        db.execute(
            text(f"""
                UPDATE dbo.CatalogoEmpresas
                SET {set_nombre}Confirmada = :conf, FechaMod = GETDATE(), UsuarioMod = :usuario
                WHERE EmpresaKey = :clave
            """),
            {**params_extra, "conf": 1 if confirmada else 0, "usuario": usuario_id, "clave": clave},
        )


def _resultado(db: Session, mensaje: str, nombre: str | None, claves: int, grupos: int) -> dict:
    filas = sincronizar_empresas(db)
    return {"mensaje": mensaje, "nombre_oficial": nombre, "claves_afectadas": claves, "grupos_afectados": grupos,
            "filas_sincronizadas": filas}


def unir(db: Session, claves: list[str], nombre_oficial: str, usuario_id: int) -> dict:
    actuales = _claves_existentes(db, claves)
    grupos_distintos = {n.casefold() for n in actuales.values()}
    if len(actuales) < 2 or len(grupos_distintos) < 2:
        raise ErrorHomologacion("Selecciona al menos dos grupos distintos: un grupo no se puede unir consigo mismo.")
    if _nombre_en_uso_fuera(db, nombre_oficial, set(actuales)):
        raise ErrorHomologacion(
            f"Ya existe otro grupo llamado «{nombre_oficial}» que no está en la selección. Inclúyelo en la unión "
            "o elige otro nombre.", 409)
    _marcar(db, list(actuales), nombre_oficial, usuario_id)
    return _resultado(db, f"Se unieron {len(grupos_distintos)} grupos bajo «{nombre_oficial}».", nombre_oficial,
                      len(actuales), len(grupos_distintos))


def renombrar(db: Session, nombre_actual: str, nombre_nuevo: str, usuario_id: int) -> dict:
    claves = _claves_del_grupo(db, nombre_actual)
    if not claves:
        raise ErrorHomologacion(f"No existe un grupo llamado «{nombre_actual}».", 404)
    if _nombre_en_uso_fuera(db, nombre_nuevo, set(claves)):
        raise ErrorHomologacion(
            f"Ya existe otro grupo llamado «{nombre_nuevo}». Para fusionarlos usa «Unir».", 409)
    _marcar(db, claves, nombre_nuevo, usuario_id)
    return _resultado(db, f"Grupo renombrado a «{nombre_nuevo}».", nombre_nuevo, len(claves), 1)


def _mejor_nombre_por_clave(db: Session) -> dict[str, str]:
    """clave -> nombre original con más CIF (desempata por nombre)."""
    mejor: dict[str, _Variante] = {}
    for v in _variantes_en_datos(db):
        actual = mejor.get(v.clave)
        if actual is None or (-v.cif_total, v.nombre) < (-actual.cif_total, actual.nombre):
            mejor[v.clave] = v
    return {c: v.nombre for c, v in mejor.items()}


def separar(db: Session, clave: str, usuario_id: int) -> dict:
    actuales = _claves_existentes(db, [clave])
    clave = next(iter(actuales))
    nombre_grupo = actuales[clave]
    del_grupo = _claves_del_grupo(db, nombre_grupo)
    if len(del_grupo) < 2:
        raise ErrorHomologacion(
            "Esa variante ya está sola en su grupo. Las variantes que solo difieren en mayúsculas, puntuación o "
            '"S.A." comparten la misma clave y no se pueden separar entre sí.')
    mejores = _mejor_nombre_por_clave(db)
    nombre_propio = mejores.get(clave)
    if not nombre_propio:
        raise ErrorHomologacion("No se encontró el nombre original de esa variante en los datos.", 404)
    restantes = [c for c in del_grupo if c != clave]
    if nombre_propio.casefold() == nombre_grupo.casefold():
        # La variante separada se llama igual que el grupo: el resto del grupo toma el nombre de su variante principal,
        # para que no queden dos grupos con el mismo nombre.
        candidatos = [mejores[c] for c in restantes if c in mejores and mejores[c].casefold() != nombre_propio.casefold()]
        if not candidatos:
            raise ErrorHomologacion(
                "No se puede separar: el resto del grupo no tiene un nombre original distinto con el cual quedarse. "
                "Renombra el grupo y vuelve a intentar.", 409)
        _marcar(db, restantes, candidatos[0], usuario_id, confirmada=True)
    elif _nombre_en_uso_fuera(db, nombre_propio, {clave}):
        raise ErrorHomologacion(f"Ya existe un grupo llamado «{nombre_propio}»; renómbralo antes de separar.", 409)
    _marcar(db, [clave], nombre_propio, usuario_id)
    return _resultado(db, f"Variante separada: ahora es el grupo «{nombre_propio}».", nombre_propio, 1, 1)


def confirmar(db: Session, nombres: list[str], usuario_id: int) -> dict:
    claves: list[str] = []
    for nombre in dict.fromkeys(n for n in nombres if n and n.strip()):
        del_grupo = _claves_del_grupo(db, nombre)
        if not del_grupo:
            raise ErrorHomologacion(f"No existe un grupo llamado «{nombre}».", 404)
        claves.extend(del_grupo)
    claves = list(dict.fromkeys(claves))
    if not claves:
        raise ErrorHomologacion("No se indicó ningún grupo.")
    _marcar(db, claves, None, usuario_id)
    n_grupos = len({n.casefold() for n in nombres if n and n.strip()})
    return _resultado(db, f"{n_grupos} grupo(s) confirmado(s).", None, len(claves), n_grupos)


def confirmar_pendientes(db: Session, busqueda: str | None, origen: str, usuario_id: int) -> dict:
    _validar_filtros("pendientes", origen)
    pendientes = [g for g in construir_grupos(db) if not g["confirmada"] and _cumple_busqueda_origen(g, busqueda, origen)]
    if not pendientes:
        return {"mensaje": "No hay grupos pendientes en el filtro actual.", "nombre_oficial": None,
                "claves_afectadas": 0, "grupos_afectados": 0, "filas_sincronizadas": 0}
    claves = [c for g in pendientes for c in g["claves"]]
    _marcar(db, claves, None, usuario_id)
    return _resultado(db, f"{len(pendientes)} grupo(s) pendiente(s) confirmado(s).", None, len(claves), len(pendientes))


def asignar_nuevas(db: Session, claves: list[str], nombre_grupo: str, grupo_nuevo: bool, usuario_id: int) -> dict:
    unicas = list(dict.fromkeys(c for c in claves if c and c.strip()))
    if not unicas:
        raise ErrorHomologacion("No se indicó ninguna empresa.")
    catalogo = _catalogo(db)
    ya = [c for c in unicas if c in catalogo]
    if ya:
        raise ErrorHomologacion(f"Esas empresas ya están en el catálogo: {', '.join(ya)}.", 409)
    conocidas = {r[0] for r in db.execute(text("SELECT DISTINCT EmpresaKey FROM dbo.log_ExcepcionesEmpresas"))}
    desconocidas = [c for c in unicas if c not in conocidas]
    if desconocidas:
        raise ErrorHomologacion(
            f"Esas empresas no están en la lista de nuevas sin homologar: {', '.join(desconocidas)}.", 404)
    existentes = _claves_del_grupo(db, nombre_grupo)
    if grupo_nuevo and existentes:
        raise ErrorHomologacion(f"Ya existe un grupo llamado «{nombre_grupo}»; asígnalas a ese grupo.", 409)
    if not grupo_nuevo and not existentes:
        raise ErrorHomologacion(f"No existe un grupo llamado «{nombre_grupo}».", 404)
    nombre_final = nombre_grupo if grupo_nuevo else catalogo[existentes[0]]["nombre"]
    for clave in unicas:
        db.execute(
            text("""
                INSERT INTO dbo.CatalogoEmpresas (EmpresaKey, EmpresaHomologada, Confirmada, FechaMod, UsuarioMod)
                VALUES (:clave, :nombre, 1, GETDATE(), :usuario)
            """),
            {"clave": clave, "nombre": nombre_final, "usuario": usuario_id},
        )
    return _resultado(db, f"{len(unicas)} empresa(s) asignada(s) a «{nombre_final}».", nombre_final, len(unicas), 1)

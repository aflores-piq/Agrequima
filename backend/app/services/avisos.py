"""Avisos (campanita): generación al terminar cada carga y lectura por usuario.

dbo.Avisos (AvisoId, Tipo, Mensaje, Referencia, FechaCreacion, Destino 'Todos' | 'Administrador') y dbo.AvisosLeidos
(AvisoId, UsuarioId, FechaLectura): cada usuario marca LEÍDO por su cuenta. Script 28.

Generación (después de cada carga de Plaguicidas o Nutrientes, nunca hace fallar la carga):
  a) elemento nuevo: ingrediente activo (Plaguicidas) o Componentes (Nutrientes) que NO existía en la tabla antes de la carga ->
     un aviso por valor, Destino 'Todos'. Si una sola carga trae más de MAX_AVISOS_INDIVIDUALES, el resto va en un aviso resumen.
  b) nombres comerciales nuevos sin catálogo -> un aviso por carga con la lista, Destino 'Administrador'.
Un aviso con la misma (Tipo, Referencia) no se vuelve a crear (índice único): recargar lo mismo no duplica.
"""

import hashlib
import logging
from dataclasses import dataclass, field

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.services.text_utils import normalizar

logger = logging.getLogger(__name__)

TIPO_ELEMENTO_NUEVO = "Importaciones.ElementoNuevo"
TIPO_NOMBRES_NUEVOS = "Importaciones.NombresSinHomologar"
PREFIJO_IMPORTACIONES = "Importaciones."
DESTINO_TODOS = "Todos"
DESTINO_ADMINISTRADOR = "Administrador"
# Roles que reciben los avisos con Destino 'Administrador': el administrador general y el del cliente (Administrador de Usuarios)
ROLES_ADMINISTRACION = ("Administrador", "Administrador de Usuarios")
MAX_AVISOS_INDIVIDUALES = 20
MAX_NOMBRES_EN_MENSAJE = 5


@dataclass(frozen=True)
class OrigenCarga:
    nombre: str          # "Plaguicidas" / "Nutrientes"
    tabla: str
    col_id: str
    col_elemento: str
    col_nombre: str
    etiqueta_elemento: str


ORIGEN_PLAGUICIDAS = OrigenCarga("Plaguicidas", "dbo.Importacion", "importacionplaguicidaid", "ingrediente_act", "producto", "ingrediente activo")
ORIGEN_NUTRIENTES = OrigenCarga("Nutrientes", "dbo.Nutrientes", "nutrienteid", "Componentes", "NombreComercial", "componente")


@dataclass
class InstantaneaCarga:
    """Lo que había en la tabla ANTES de la carga."""
    origen: OrigenCarga
    id_antes: int
    elementos: set[str] = field(default_factory=set)
    nombres: set[str] = field(default_factory=set)


def _claves_distintas(conn, tabla: str, columna: str) -> set[str]:
    filas = conn.execute(text(f"SELECT DISTINCT {columna} FROM {tabla} WHERE {columna} IS NOT NULL")).all()
    return {k for (v,) in filas if (k := normalizar(v)) is not None}


def tomar_instantanea(conn, origen: OrigenCarga) -> InstantaneaCarga:
    """Se llama justo antes del EXEC de la carga."""
    id_antes = int(conn.execute(text(f"SELECT ISNULL(MAX({origen.col_id}), 0) FROM {origen.tabla}")).scalar() or 0)
    return InstantaneaCarga(
        origen=origen,
        id_antes=id_antes,
        elementos=_claves_distintas(conn, origen.tabla, origen.col_elemento),
        nombres=_claves_distintas(conn, origen.tabla, origen.col_nombre) if origen is ORIGEN_NUTRIENTES else set(),
    )


def crear_aviso(conn, tipo: str, mensaje: str, destino: str, referencia: str | None) -> bool:
    """Inserta el aviso si no existe ya uno con el mismo (Tipo, Referencia). Devuelve True si lo creó."""
    mensaje = mensaje if len(mensaje) <= 500 else mensaje[:497] + "..."
    r = conn.execute(
        text("""
            INSERT INTO dbo.Avisos (Tipo, Mensaje, Referencia, Destino)
            SELECT :tipo, :mensaje, :referencia, :destino
            WHERE :referencia IS NULL
               OR NOT EXISTS (SELECT 1 FROM dbo.Avisos WHERE Tipo = :tipo AND Referencia = :referencia)
        """),
        {"tipo": tipo, "mensaje": mensaje, "referencia": referencia, "destino": destino},
    )
    return r.rowcount > 0


def _valores_de_filas_nuevas(conn, ins: InstantaneaCarga, columna: str) -> dict[str, str]:
    """clave normalizada -> valor de ejemplo, de las filas que agregó la carga (id > id_antes)."""
    o = ins.origen
    filas = conn.execute(
        text(f"SELECT DISTINCT {columna} FROM {o.tabla} WHERE {o.col_id} > :id AND {columna} IS NOT NULL"), {"id": ins.id_antes}
    ).all()
    salida: dict[str, str] = {}
    for (v,) in filas:
        k = normalizar(v)
        if k is not None:
            salida.setdefault(k, " ".join(str(v).split()))
    return salida


def _hash(valores: list[str]) -> str:
    return hashlib.sha1("|".join(sorted(valores)).encode("utf-8")).hexdigest()[:16]


def generar_avisos_carga(conn, ins: InstantaneaCarga, nombres_nuevos_sin_catalogo: list[str] | None = None) -> int:
    """Crea los avisos de una carga ya terminada. `nombres_nuevos_sin_catalogo`: para Plaguicidas, la lista que devuelve
    registrar_nombres_sin_homologar; para Nutrientes se calcula aquí (nombres que no existían ni tienen entrada en el catálogo).
    Devuelve cuántos avisos nuevos se crearon."""
    o = ins.origen
    creados = 0

    # a) elementos nuevos (valores que no existían antes de la carga)
    nuevos = {k: v for k, v in _valores_de_filas_nuevas(conn, ins, o.col_elemento).items() if k not in ins.elementos}
    ordenados = sorted(nuevos.items(), key=lambda kv: kv[1].upper())
    for clave, valor in ordenados[:MAX_AVISOS_INDIVIDUALES]:
        if crear_aviso(conn, TIPO_ELEMENTO_NUEVO, f"Hay un elemento nuevo: {valor} ({o.etiqueta_elemento} en {o.nombre}).",
                       DESTINO_TODOS, f"{o.nombre}:{clave}"):
            creados += 1
    resto = ordenados[MAX_AVISOS_INDIVIDUALES:]
    if resto and crear_aviso(
        conn, TIPO_ELEMENTO_NUEVO, f"Hay {len(resto)} elementos nuevos más en {o.nombre} ({o.etiqueta_elemento}).",
        DESTINO_TODOS, f"{o.nombre}:resumen:{_hash([c for c, _ in resto])}",
    ):
        creados += 1

    # b) nombres comerciales nuevos sin catálogo -> solo para el Administrador
    if o is ORIGEN_NUTRIENTES:
        nombres = _nombres_nuevos_nutrientes(conn, ins)
    else:
        nombres = nombres_nuevos_sin_catalogo or []
    if nombres:
        muestra = ", ".join(nombres[:MAX_NOMBRES_EN_MENSAJE]) + (f" y {len(nombres) - MAX_NOMBRES_EN_MENSAJE} más" if len(nombres) > MAX_NOMBRES_EN_MENSAJE else "")
        plural = len(nombres) != 1
        if crear_aviso(
            conn, TIPO_NOMBRES_NUEVOS,
            f"Hay {len(nombres)} nombre{'s' if plural else ''} comercial{'es' if plural else ''} nuevo{'s' if plural else ''} sin homologar "
            f"en {o.nombre}: {muestra}. Revisa «Homologación de nombres comerciales».",
            DESTINO_ADMINISTRADOR, f"{o.nombre}:nombres:{_hash(nombres)}",
        ):
            creados += 1
    return creados


def _nombres_nuevos_nutrientes(conn, ins: InstantaneaCarga) -> list[str]:
    en_catalogo = {k for (k,) in conn.execute(text("SELECT NombreComercial_Key FROM dbo.CatalogoAgrupadorNutrientes"))}
    nuevos = {
        k: v for k, v in _valores_de_filas_nuevas(conn, ins, ins.origen.col_nombre).items()
        if k not in ins.nombres and k not in en_catalogo
    }
    return sorted(nuevos.values(), key=str.upper)


# ---------------------------------------------------------------------------------------------
# Lectura por usuario
# ---------------------------------------------------------------------------------------------

def _filtro_visibles(db: Session, usuario_id: int, rol: str) -> tuple[str, dict]:
    """Condición SQL de los avisos que ve este usuario: los roles de administración (Administrador y Administrador de Usuarios) ven 'Todos' y 'Administrador'; Usuario solo 'Todos'. Quien
    no tiene acceso a Importaciones no ve los avisos de ese módulo (no debe deducir que existe)."""
    destinos = [DESTINO_TODOS, DESTINO_ADMINISTRADOR] if rol in ROLES_ADMINISTRACION else [DESTINO_TODOS]
    cond = "a.Destino IN :destinos"
    acceso = db.query(Usuario.AccesoImportaciones).filter(Usuario.UsuarioId == usuario_id).scalar()
    if not acceso:
        cond += f" AND a.Tipo NOT LIKE '{PREFIJO_IMPORTACIONES}%'"
    return cond, {"destinos": tuple(destinos)}


def listar_avisos(db: Session, usuario_id: int, rol: str, incluir_leidos: bool = False, limite: int = 100) -> dict:
    cond, params = _filtro_visibles(db, usuario_id, rol)
    base = f"""
        FROM dbo.Avisos a
        LEFT JOIN dbo.AvisosLeidos l ON l.AvisoId = a.AvisoId AND l.UsuarioId = :uid
        WHERE {cond}"""
    sql_no_leidos = text(f"SELECT COUNT(*) {base} AND l.AvisoId IS NULL").bindparams(_expanding("destinos"))
    no_leidos = db.execute(sql_no_leidos, {**params, "uid": usuario_id}).scalar() or 0
    filtro_leidos = "" if incluir_leidos else " AND l.AvisoId IS NULL"
    filas = db.execute(
        text(f"""
            SELECT TOP (:limite) a.AvisoId, a.Tipo, a.Mensaje, a.Referencia, a.FechaCreacion, a.Destino,
                   CASE WHEN l.AvisoId IS NULL THEN 0 ELSE 1 END AS Leido
            {base}{filtro_leidos}
            ORDER BY a.FechaCreacion DESC, a.AvisoId DESC
        """).bindparams(_expanding("destinos")),
        {**params, "uid": usuario_id, "limite": limite},
    ).all()
    return {
        "no_leidos": int(no_leidos),
        "avisos": [
            {"aviso_id": r[0], "tipo": r[1], "mensaje": r[2], "referencia": r[3], "fecha_creacion": r[4], "destino": r[5], "leido": bool(r[6])}
            for r in filas
        ],
    }


def _expanding(nombre: str):
    return bindparam(nombre, expanding=True)


def marcar_leido(db: Session, usuario_id: int, rol: str, aviso_id: int) -> bool:
    """Marca un aviso como leído por este usuario. False si el aviso no existe o este usuario no lo puede ver."""
    cond, params = _filtro_visibles(db, usuario_id, rol)
    visible = db.execute(
        text(f"SELECT COUNT(*) FROM dbo.Avisos a WHERE a.AvisoId = :id AND {cond}").bindparams(_expanding("destinos")),
        {**params, "id": aviso_id},
    ).scalar()
    if not visible:
        return False
    db.execute(
        text("""
            INSERT INTO dbo.AvisosLeidos (AvisoId, UsuarioId, FechaLectura)
            SELECT :id, :uid, GETDATE()
            WHERE NOT EXISTS (SELECT 1 FROM dbo.AvisosLeidos WHERE AvisoId = :id AND UsuarioId = :uid)
        """),
        {"id": aviso_id, "uid": usuario_id},
    )
    return True


def marcar_todos_leidos(db: Session, usuario_id: int, rol: str) -> int:
    """Marca como leídos todos los avisos visibles que este usuario aún no leyó; devuelve cuántos."""
    cond, params = _filtro_visibles(db, usuario_id, rol)
    r = db.execute(
        text(f"""
            INSERT INTO dbo.AvisosLeidos (AvisoId, UsuarioId, FechaLectura)
            SELECT a.AvisoId, :uid, GETDATE()
            FROM dbo.Avisos a
            WHERE {cond}
              AND NOT EXISTS (SELECT 1 FROM dbo.AvisosLeidos l WHERE l.AvisoId = a.AvisoId AND l.UsuarioId = :uid)
        """).bindparams(_expanding("destinos")),
        {**params, "uid": usuario_id},
    )
    return r.rowcount

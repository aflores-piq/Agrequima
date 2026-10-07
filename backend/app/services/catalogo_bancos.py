"""Catálogo de bancos (dbo.CatalogoBancos) -- apariencia de cada banco en
Conciliación bancaria y Flujo de caja.

La LISTA de bancos sale de los datos (dbo.SaldosBancos,
dbo.ChequesCirculacion y dbo.SaldoBancario); el catálogo solo dice CÓMO
SE VE cada uno (nombre por pantalla, color, orden) o lo oculta
(activo = 0). Un banco que está en los datos y no en el catálogo se
muestra igual: su código como nombre, gris #9E9E9E y al final.

Los códigos se comparan NORMALIZADOS (mayúsculas, sin tildes, sin
espacios ni caracteres invisibles), así PROMÉRICA, Promerica y
"PROMERICA\\xa0" son el mismo banco -- el mismo texto con un NBSP o un
salto de línea al final ya rompió uniones de Python (`dict.get`) en
este proyecto, por eso la comparación nunca se hace con el texto crudo.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

COLOR_BANCO_POR_DEFECTO = "#9E9E9E"
_FORMATO_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_INVISIBLES_EXTRA = {0x034F, 0x061C, 0x180E, 0xFEFF, 0xFFFC}
_ORDEN_AL_FINAL = 10**9


def _es_espacio(ch: str) -> bool:
    return ch.isspace() or unicodedata.category(ch) in ("Zs", "Zl", "Zp")


def _es_invisible_no_espacio(ch: str) -> bool:
    return (unicodedata.category(ch) in ("Cc", "Cf") and not ch.isspace()) or ord(ch) in _INVISIBLES_EXTRA


def limpiar_texto(valor) -> str:
    """Texto para MOSTRAR: cualquier espacio raro (NBSP, tab, CR/LF...)
    pasa a espacio normal, los caracteres invisibles se eliminan, se
    colapsan los espacios repetidos y se recorta."""
    if valor is None:
        return ""
    partes = []
    for ch in str(valor):
        if ch == " " or _es_espacio(ch):
            partes.append(" ")
        elif not _es_invisible_no_espacio(ch):
            partes.append(ch)
    return " ".join("".join(partes).split())


def normalizar_codigo_banco(valor) -> str:
    """Clave de COMPARACIÓN: mayúsculas, sin tildes, sin espacios ni
    caracteres invisibles. '' si no queda nada."""
    sin_tildes = "".join(
        ch for ch in unicodedata.normalize("NFD", limpiar_texto(valor)) if unicodedata.category(ch) != "Mn"
    )
    return sin_tildes.upper().replace(" ", "")


@dataclass(frozen=True)
class BancoCatalogo:
    clave: str
    ban_codigo: str
    nombre_conciliacion: str | None
    nombre_flujo: str | None
    color_hex: str | None
    orden: int | None
    orden_flujo: int | None
    activo: bool
    clave_alias: str


@dataclass(frozen=True)
class BancoResuelto:
    """Un banco ya listo para pintarse en las dos pantallas."""

    clave: str
    codigo: str
    nombre_conciliacion: str
    nombre_flujo: str
    color: str
    orden_conciliacion: tuple
    orden_flujo: tuple
    en_catalogo: bool


def cargar_catalogo_bancos(db: Session) -> list[BancoCatalogo]:
    """Filas de dbo.CatalogoBancos. Si la tabla todavía no existe (se
    publicó la app antes de correr 19_catalogo_bancos_financiero.sql) NO
    se rompe la pantalla: se avisa en el log y todos los bancos salen como
    "no están en el catálogo" (con sus datos, en gris)."""
    try:
        filas = db.execute(
            text(
                """
                SELECT ban_codigo, nombre_conciliacion, nombre_flujo, color_hex,
                       orden, orden_flujo, activo, alias_saldo_bancario
                FROM dbo.CatalogoBancos
                ORDER BY catalogobancoid
                """
            )
        ).all()
    except SQLAlchemyError:
        db.rollback()
        logger.warning(
            "No se pudo leer dbo.CatalogoBancos (¿falta correr 19_catalogo_bancos_financiero.sql?): "
            "los bancos se muestran sin catálogo (código como nombre y color gris)."
        )
        return []

    catalogo = []
    for codigo, nom_conc, nom_flujo, color, orden, orden_flujo, activo, alias in filas:
        clave = normalizar_codigo_banco(codigo)
        if not clave:
            continue
        catalogo.append(
            BancoCatalogo(
                clave=clave,
                ban_codigo=limpiar_texto(codigo),
                nombre_conciliacion=limpiar_texto(nom_conc) or None,
                nombre_flujo=limpiar_texto(nom_flujo) or None,
                color_hex=limpiar_texto(color) or None,
                orden=orden,
                orden_flujo=orden_flujo,
                activo=bool(activo),
                clave_alias=normalizar_codigo_banco(alias),
            )
        )
    return catalogo


class ResolutorBancos:
    """Une los códigos de banco de los datos con el catálogo."""

    def __init__(self, catalogo: list[BancoCatalogo]):
        self._por_clave: dict[str, BancoCatalogo] = {}
        for banco in catalogo:  # si dos filas normalizan igual, gana la primera
            self._por_clave.setdefault(banco.clave, banco)
        # Alias del Excel de SaldoBancario -> clave del banco. Un código
        # propio de otro banco siempre gana sobre un alias.
        self._alias: dict[str, str] = {}
        for banco in catalogo:
            if banco.clave_alias and banco.clave_alias not in self._por_clave:
                self._alias.setdefault(banco.clave_alias, banco.clave)

    def clave(self, codigo) -> str | None:
        """Clave del banco al que pertenece ese texto de los datos (None
        si el texto está vacío)."""
        clave = normalizar_codigo_banco(codigo)
        if not clave:
            return None
        return self._alias.get(clave, clave)

    def activo(self, clave: str) -> bool:
        banco = self._por_clave.get(clave)
        return banco.activo if banco is not None else True

    def resolver(self, codigos_visibles: dict[str, str]) -> list[BancoResuelto]:
        """`codigos_visibles`: clave -> texto con el que se ve el banco en
        los datos. Devuelve los bancos ACTIVOS (nombre, color, órdenes)."""
        resueltos = []
        for clave, codigo in codigos_visibles.items():
            banco = self._por_clave.get(clave)
            if banco is not None and not banco.activo:
                continue
            if banco is None:
                resueltos.append(
                    BancoResuelto(
                        clave=clave,
                        codigo=codigo,
                        nombre_conciliacion=codigo,
                        nombre_flujo=codigo,
                        color=COLOR_BANCO_POR_DEFECTO,
                        orden_conciliacion=(1, 0, clave),
                        orden_flujo=(1, 0, clave),
                        en_catalogo=False,
                    )
                )
                continue
            color = banco.color_hex if banco.color_hex and _FORMATO_COLOR.match(banco.color_hex) else COLOR_BANCO_POR_DEFECTO
            codigo = banco.ban_codigo or codigo  # el código del catálogo, no el alias con el que llegó el dato
            nombre_conciliacion = banco.nombre_conciliacion or codigo
            orden_flujo = banco.orden_flujo if banco.orden_flujo is not None else banco.orden
            resueltos.append(
                BancoResuelto(
                    clave=clave,
                    codigo=codigo,
                    nombre_conciliacion=nombre_conciliacion,
                    nombre_flujo=banco.nombre_flujo or codigo,
                    color=color,
                    orden_conciliacion=(0, banco.orden if banco.orden is not None else _ORDEN_AL_FINAL, clave),
                    orden_flujo=(0, orden_flujo if orden_flujo is not None else _ORDEN_AL_FINAL, clave),
                    en_catalogo=True,
                )
            )
        return resueltos


def ordenar_conciliacion(bancos: list[BancoResuelto]) -> list[BancoResuelto]:
    return sorted(bancos, key=lambda b: b.orden_conciliacion)


def ordenar_flujo(bancos: list[BancoResuelto]) -> list[BancoResuelto]:
    return sorted(bancos, key=lambda b: b.orden_flujo)

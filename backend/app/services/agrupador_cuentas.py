"""Agrupador de cuentas contables (dbo.CatalogoAgrupadorCuentas) --
fuente de la columna "Grupo" en el dashboard Financiero (ver
services/dashboard_financiero.py).

Emparejamiento jerárquico por código de cuenta, hecho en Python (mismo
criterio que app/services/clasificacion.py para Plaguicidas: la
clasificación vive en código, no en SQL) porque la tabla es chica
(decenas de filas) y así se puede probar con datos comunes sin
depender de sintaxis T-SQL:

    1. Nivel 3 -- coincidencia EXACTA contra el código completo de la
       cuenta.
    2. Si no hay, Nivel 2 -- contra los primeros 6 dígitos del código.
    3. Si tampoco, Nivel 1 -- contra los primeros 4 dígitos.

El primero que coincide gana. Si ninguno coincide, no hay grupo (queda
None -- el frontend ya lo muestra como "SIN CLASIFICAR")."""

from sqlalchemy import text
from sqlalchemy.orm import Session

# {nivel: {codigo: nombre}}
MapasAgrupador = dict[int, dict[str, str]]


def cargar_mapas_agrupador(db: Session, tipo_agrupador: str) -> tuple[MapasAgrupador, dict[str, int]]:
    """Devuelve (mapas, ordenes): `mapas` para el emparejamiento
    jerárquico, `ordenes` (nombre de grupo -> menor Orden con el que
    aparece) para poder ordenar la cascada de la página 1 según el
    orden real del catálogo, no por magnitud."""
    filas = db.execute(
        text(
            "SELECT Nivel, Codigo, Nombre, Orden FROM dbo.CatalogoAgrupadorCuentas "
            "WHERE TipoAgrupador = :tipo"
        ),
        {"tipo": tipo_agrupador},
    ).mappings().all()

    mapas: MapasAgrupador = {1: {}, 2: {}, 3: {}}
    ordenes: dict[str, int] = {}
    for fila in filas:
        mapas[fila["Nivel"]][fila["Codigo"]] = fila["Nombre"]
        nombre = fila["Nombre"]
        ordenes[nombre] = min(ordenes.get(nombre, fila["Orden"]), fila["Orden"])
    return mapas, ordenes


def grupo_de_cuenta(mapas: MapasAgrupador, codigo: str | None) -> str | None:
    if not codigo:
        return None
    codigo = codigo.strip()
    if codigo in mapas[3]:
        return mapas[3][codigo]
    if codigo[:6] in mapas[2]:
        return mapas[2][codigo[:6]]
    if codigo[:4] in mapas[1]:
        return mapas[1][codigo[:4]]
    return None

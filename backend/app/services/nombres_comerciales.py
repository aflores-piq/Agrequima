"""Homologación de nombres comerciales de Plaguicidas (dbo.Importacion.producto): clave, sincronización y registro de nombres nuevos.

La clave la calcula UNA sola función de SQL Server, dbo.fn_ClaveNombreComercial (script 27): mayúsculas, sin tildes, puntos y comas
como espacio y espacios colapsados. No une por orden de palabras ni por errores de tipeo: esas uniones las hace el administrador.

dbo.CatalogoNombresComerciales (NombreKey -> NombreHomologado) es el catálogo; dbo.Importacion.NombreComercialHomologado se sincroniza
desde él (mismo patrón que EmpresaHomologada). El dato original (producto) no se modifica nunca; los tableros usan
COALESCE(NombreComercialHomologado, producto).

Para Nutrientes el estándar es dbo.CatalogoAgrupadorNutrientes (ProductoAgrupado), que ya se sincroniza con
sincronizacion_agrupador.sincronizar_agrupador_nutrientes: no se crea otro catálogo.
"""

from sqlalchemy import text


def clave_nombre_comercial(db, texto: str | None) -> str | None:
    """Clave normalizada de un nombre comercial; None si el texto está vacío."""
    if texto is None:
        return None
    return db.execute(text("SELECT dbo.fn_ClaveNombreComercial(:t)"), {"t": texto}).scalar()


def sincronizar_nombres_plaguicidas(db) -> int:
    """Pone en NombreComercialHomologado de dbo.Importacion el nombre del catálogo para la clave de cada fila (y NULL si su clave
    ya no está en el catálogo). Solo toca filas cuyo valor cambia; devuelve cuántas cambió. El commit lo hace quien llama."""
    total = db.execute(text("""
        UPDATE i
        SET i.NombreComercialHomologado = c.NombreHomologado
        FROM dbo.Importacion i
        JOIN dbo.CatalogoNombresComerciales c
          ON c.NombreKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveNombreComercial(i.producto) COLLATE DATABASE_DEFAULT
        WHERE ISNULL(i.NombreComercialHomologado, N'') COLLATE Latin1_General_BIN2 <> c.NombreHomologado COLLATE Latin1_General_BIN2
    """)).rowcount
    total += db.execute(text("""
        UPDATE i
        SET i.NombreComercialHomologado = NULL
        FROM dbo.Importacion i
        WHERE i.NombreComercialHomologado IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM dbo.CatalogoNombresComerciales c
              WHERE c.NombreKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveNombreComercial(i.producto) COLLATE DATABASE_DEFAULT)
    """)).rowcount
    return total


def max_id_importacion(conn) -> int:
    """Último importacionplaguicidaid antes de una carga (para identificar las filas que la carga agregue)."""
    return int(conn.execute(text("SELECT ISNULL(MAX(importacionplaguicidaid), 0) FROM dbo.Importacion")).scalar() or 0)


def registrar_nombres_sin_homologar(conn, id_antes: int) -> int:
    """Registra en dbo.log_ExcepcionesNombresComerciales (una fila por nombre) los nombres comerciales de las filas que agregó la
    carga (id > id_antes) cuya clave no está en el catálogo. Devuelve cuántos nombres nuevos hay."""
    nuevos = conn.execute(text("""
        SELECT n.Nombre, n.Clave, COUNT(*) AS Filas, SUM(CAST(n.Cif AS DECIMAL(19,2))) AS Cif
        FROM (
            SELECT i.producto AS Nombre, dbo.fn_ClaveNombreComercial(i.producto) AS Clave, i.cif_USD AS Cif
            FROM dbo.Importacion i
            WHERE i.importacionplaguicidaid > :id_antes AND i.producto IS NOT NULL
        ) n
        WHERE n.Clave IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM dbo.CatalogoNombresComerciales c
                          WHERE c.NombreKey COLLATE DATABASE_DEFAULT = n.Clave COLLATE DATABASE_DEFAULT)
        GROUP BY n.Nombre, n.Clave
    """), {"id_antes": id_antes}).all()
    por_clave: dict[str, dict] = {}
    for nombre, clave, filas, cif in nuevos:
        d = por_clave.setdefault(clave, {"nombre": nombre, "filas": 0, "cif": 0.0, "mejor": -1.0})
        d["filas"] += int(filas)
        d["cif"] += float(cif or 0)
        if float(cif or 0) > d["mejor"]:
            d["mejor"], d["nombre"] = float(cif or 0), nombre
    for clave, d in por_clave.items():
        conn.execute(
            text("""
                INSERT INTO dbo.log_ExcepcionesNombresComerciales (Origen, Nombre, NombreKey, Filas, CifUsd)
                VALUES ('Plaguicidas', :nombre, :clave, :filas, :cif)
            """),
            {"nombre": d["nombre"], "clave": clave, "filas": d["filas"], "cif": round(d["cif"], 2)},
        )
    return len(por_clave)

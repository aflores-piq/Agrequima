"""Pantalla de Nomenclatura > Nutrientes ("sin agrupador"): debe leer de
dbo.vw_NutrientesActivos (vía NutrienteActivo), no de dbo.Nutrientes
directo -- una fila Excluido=1 no debe aparecer acá tampoco, aunque en
la práctica casi nunca tenga ProductoAgrupado NULL a la vez (ver
comentario en admin_nomenclatura.py)."""

from sqlalchemy import text

from app.core.db import engine
from app.services.text_utils import normalizar


def test_sin_agrupador_nutrientes_no_muestra_productos_excluidos(client, admin_headers):
    nombre_excluido = "PRODUCTO EXCLUIDO SIN AGRUPADOR PRUEBA"
    nombre_normal = "PRODUCTO NORMAL SIN AGRUPADOR PRUEBA"
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM dbo.Nutrientes WHERE NombreComercial IN (:a, :b)"),
            {"a": nombre_excluido, "b": nombre_normal},
        )
        # Excluido=1 y ProductoAgrupado NULL a propósito: el caso límite
        # donde, sin la vista, esta pantalla lo mostraría como "sin
        # agrupador" pese a estar excluido.
        conn.execute(
            text(
                "INSERT INTO dbo.Nutrientes (anio, Tipo, No_Licencia, No_Registro, NombreComercial, "
                "CIF_dolares, Excluido, fechamod) "
                "VALUES (2026, 'Licencias', 'T-1', 'T-F-1', :nombre, 100.0, 1, GETDATE())"
            ),
            {"nombre": nombre_excluido},
        )
        conn.execute(
            text(
                "INSERT INTO dbo.Nutrientes (anio, Tipo, No_Licencia, No_Registro, NombreComercial, "
                "CIF_dolares, Excluido, fechamod) "
                "VALUES (2026, 'Licencias', 'T-2', 'T-F-2', :nombre, 200.0, 0, GETDATE())"
            ),
            {"nombre": nombre_normal},
        )

    try:
        r = client.get(
            "/api/admin/nomenclatura/nutrientes/sin-agrupador",
            headers=admin_headers,
            params={"tamano_pagina": 200},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        claves_resumen = {fila["nombre_key"] for fila in body["resumen"]}
        nombres_detalle = {fila["nombre_comercial"] for fila in body["detalle"]["filas"]}

        assert normalizar(nombre_excluido) not in claves_resumen
        assert nombre_excluido not in nombres_detalle

        assert normalizar(nombre_normal) in claves_resumen
        assert nombre_normal in nombres_detalle
    finally:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM dbo.Nutrientes WHERE NombreComercial IN (:a, :b)"),
                {"a": nombre_excluido, "b": nombre_normal},
            )

"""Demostración de la campanita (SOLO para pruebas locales; no forma parte del sistema).

  python backend/scripts/demo_avisos.py --crear    inserta un aviso de prueba para 'Todos' y otro para 'Administrador'
  python backend/scripts/demo_avisos.py --borrar   borra los avisos de prueba (y sus marcas de leído)

Usa la misma base que el backend (la del .env). Los avisos de prueba tienen Tipo = 'Demo', así que --borrar nunca toca los
avisos reales. Después de --crear, entra al sistema y mira la campanita arriba a la derecha: el Administrador ve los dos avisos y
un Usuario solo el de 'Todos'."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.db import engine  # noqa: E402

TIPO_DEMO = "Demo"


def crear() -> None:
    with engine.begin() as conn:
        creados = 0
        for destino, mensaje in (
            ("Todos", "Aviso de prueba para todos los usuarios: hay un elemento nuevo: DEMO-ELEMENTO."),
            ("Administrador", "Aviso de prueba para el Administrador: hay 3 nombres comerciales nuevos sin homologar."),
        ):
            referencia = f"demo:{destino.lower()}"
            ya = conn.execute(
                text("SELECT COUNT(*) FROM dbo.Avisos WHERE Tipo = :t AND Referencia = :r"), {"t": TIPO_DEMO, "r": referencia}
            ).scalar()
            if ya:
                # Si ya existía (aunque esté leído), se vuelve a mostrar como no leído para repetir la demostración
                conn.execute(
                    text("DELETE FROM dbo.AvisosLeidos WHERE AvisoId IN (SELECT AvisoId FROM dbo.Avisos WHERE Tipo = :t AND Referencia = :r)"),
                    {"t": TIPO_DEMO, "r": referencia},
                )
                continue
            conn.execute(
                text("INSERT INTO dbo.Avisos (Tipo, Mensaje, Referencia, Destino) VALUES (:t, :m, :r, :d)"),
                {"t": TIPO_DEMO, "m": mensaje, "r": referencia, "d": destino},
            )
            creados += 1
    print(f"Avisos de prueba listos ({creados} nuevos). Abre el sistema y mira la campanita.")


def borrar() -> None:
    with engine.begin() as conn:
        n = conn.execute(text("DELETE FROM dbo.Avisos WHERE Tipo = :t"), {"t": TIPO_DEMO}).rowcount
    print(f"Avisos de prueba borrados: {n}.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--crear", action="store_true")
    g.add_argument("--borrar", action="store_true")
    args = ap.parse_args()
    crear() if args.crear else borrar()

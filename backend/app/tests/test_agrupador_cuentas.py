from app.core.db import SessionLocal
from app.services.agrupador_cuentas import cargar_mapas_agrupador, grupo_de_cuenta


def test_emparejamiento_jerarquico_egresos():
    db = SessionLocal()
    try:
        mapas, ordenes = cargar_mapas_agrupador(db, "Egresos")
    finally:
        db.close()

    # Nivel 3 (código completo exacto) gana aunque también matchee Nivel 1.
    assert grupo_de_cuenta(mapas, "510201011") == "Cuentas Incobrables"
    # Nivel 2 (primeros 6 dígitos) cuando no hay Nivel 3.
    assert grupo_de_cuenta(mapas, "510206005") == "Suscripciones y Membresías"
    assert grupo_de_cuenta(mapas, "510206") == "Suscripciones y Membresías"
    # Nivel 1 (primeros 4 dígitos) cuando no hay Nivel 2 ni 3.
    assert grupo_de_cuenta(mapas, "510199999") == "Sueldos Bonificaciones y Prestaciones de Ley"
    assert grupo_de_cuenta(mapas, "5101") == "Sueldos Bonificaciones y Prestaciones de Ley"
    # Dos códigos Nivel 1 distintos (5105 y 5104) mapean al mismo nombre
    # de grupo (mismo Orden=7) -- se agregan bajo el mismo grupo.
    assert grupo_de_cuenta(mapas, "5105") == "Viáticos e Insumos Programa Cuidagro"
    assert grupo_de_cuenta(mapas, "5104") == "Viáticos e Insumos Programa Cuidagro"
    assert ordenes["Viáticos e Insumos Programa Cuidagro"] == 7
    # Sin coincidencia en ningún nivel.
    assert grupo_de_cuenta(mapas, "9999") is None
    assert grupo_de_cuenta(mapas, None) is None
    assert grupo_de_cuenta(mapas, "") is None


def test_emparejamiento_activo_pasivo_patrimonio():
    db = SessionLocal()
    try:
        mapas_activo, _ = cargar_mapas_agrupador(db, "Activo")
        mapas_pasivo, _ = cargar_mapas_agrupador(db, "Pasivo")
        mapas_patrimonio, _ = cargar_mapas_agrupador(db, "Patrimonio")
    finally:
        db.close()

    assert grupo_de_cuenta(mapas_activo, "110204001") == "Cuentas por Cobrar BANRURAL"
    assert grupo_de_cuenta(mapas_activo, "1101") == "Caja y Bancos"
    assert grupo_de_cuenta(mapas_pasivo, "210105001") == "Fondos por aplicar acumulado"
    assert grupo_de_cuenta(mapas_pasivo, "210105002") == "Fondos por aplicar caso judicial BANRURAL"
    assert grupo_de_cuenta(mapas_patrimonio, "310101001") == "Patrimonio activos fijos"
    # Un código de Activo no debe matchear contra el mapa de Pasivo.
    assert grupo_de_cuenta(mapas_pasivo, "1101") is None

"""Revisión de transacciones sin agrupador encontrado.

A diferencia del log de auditoría por corrida (dbo.log_ExcepcionesAgrupador*),
esta pantalla consulta el estado ACTUAL de dbo.Importacion / dbo.Nutrientes
(CodigoAgrupador / ProductoAgrupado nulos), para que quede al día
automáticamente cuando el administrador corrige el catálogo desde la
pantalla de nomenclatura, sin depender de cuál fue la última carga.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.importacion import Importacion
from app.models.nutriente import Nutriente
from app.schemas.excepciones import (
    ActualizarAgrupadorNutrientesRequest,
    ActualizarAgrupadorPlaguicidasRequest,
    ActualizarAgrupadorResponse,
    DetalleExcepcionNutriente,
    DetalleExcepcionPlaguicida,
    ExcepcionesNutrientesResponse,
    ExcepcionesPlaguicidasResponse,
    PaginaDetalleExcepcionesNutrientes,
    PaginaDetalleExcepcionesPlaguicidas,
    ResumenExcepcionNutriente,
    ResumenExcepcionPlaguicida,
)
from app.services.sincronizacion_agrupador import (
    sincronizar_agrupador_nutrientes,
    sincronizar_agrupador_plaguicidas,
)
from app.services.text_utils import normalizar, parece_error_captura

router = APIRouter(
    prefix="/admin/excepciones",
    tags=["admin-excepciones"],
    dependencies=[Depends(require_role("Administrador"))],
)


@router.get("/plaguicidas", response_model=ExcepcionesPlaguicidasResponse)
def excepciones_plaguicidas(
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ExcepcionesPlaguicidasResponse:
    sin_agrupador = db.query(Importacion).filter(
        Importacion.CodigoAgrupador.is_(None), Importacion.ingrediente_act.isnot(None)
    )

    filas_sql = (
        sin_agrupador.with_entities(
            Importacion.ingrediente_act,
            func.count(Importacion.importacionplaguicidaid),
            func.sum(Importacion.cantidad),
            func.sum(Importacion.cif_USD),
        )
        .group_by(Importacion.ingrediente_act)
        .all()
    )

    agregados: dict[str, dict] = {}
    for ingrediente_act, transacciones, cantidad, cif_usd in filas_sql:
        clave = normalizar(ingrediente_act)
        if clave is None:
            continue
        acc = agregados.setdefault(
            clave, {"ejemplo": ingrediente_act, "transacciones": 0, "cantidad": 0.0, "cif_usd": 0.0}
        )
        acc["transacciones"] += transacciones
        acc["cantidad"] += float(cantidad or 0)
        acc["cif_usd"] += float(cif_usd or 0)

    resumen = [
        ResumenExcepcionPlaguicida(
            ingrediente_key=clave,
            ingrediente_ejemplo=datos["ejemplo"],
            transacciones=datos["transacciones"],
            cantidad_total=datos["cantidad"],
            cif_usd_total=datos["cif_usd"],
            posible_error_captura=parece_error_captura(datos["ejemplo"]),
        )
        for clave, datos in sorted(agregados.items(), key=lambda kv: -kv[1]["transacciones"])
    ]

    total_detalle = sin_agrupador.with_entities(
        func.count(Importacion.importacionplaguicidaid)
    ).scalar() or 0
    filas_detalle = (
        sin_agrupador.order_by(Importacion.ingrediente_act, Importacion.importacionplaguicidaid)
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )

    return ExcepcionesPlaguicidasResponse(
        resumen=resumen,
        detalle=PaginaDetalleExcepcionesPlaguicidas(
            total=total_detalle,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
            filas=[
                DetalleExcepcionPlaguicida(
                    recibointerno=fila.recibointerno,
                    ingrediente_act=fila.ingrediente_act,
                    ingrediente_key=normalizar(fila.ingrediente_act),
                    producto=fila.producto,
                )
                for fila in filas_detalle
            ],
        ),
    )


@router.get("/nutrientes", response_model=ExcepcionesNutrientesResponse)
def excepciones_nutrientes(
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ExcepcionesNutrientesResponse:
    sin_agrupador = db.query(Nutriente).filter(
        Nutriente.ProductoAgrupado.is_(None), Nutriente.NombreComercial.isnot(None)
    )

    filas_sql = (
        sin_agrupador.with_entities(
            Nutriente.NombreComercial,
            func.count(Nutriente.nutrienteid),
            func.sum(Nutriente.CIF_dolares),
        )
        .group_by(Nutriente.NombreComercial)
        .all()
    )

    agregados: dict[str, dict] = {}
    for nombre_comercial, transacciones, cif_dolares in filas_sql:
        clave = normalizar(nombre_comercial)
        if clave is None:
            continue
        acc = agregados.setdefault(
            clave, {"ejemplo": nombre_comercial, "transacciones": 0, "cif_dolares": 0.0}
        )
        acc["transacciones"] += transacciones
        acc["cif_dolares"] += float(cif_dolares or 0)

    resumen = [
        ResumenExcepcionNutriente(
            nombre_key=clave,
            nombre_ejemplo=datos["ejemplo"],
            transacciones=datos["transacciones"],
            cif_dolares_total=datos["cif_dolares"],
            posible_error_captura=parece_error_captura(datos["ejemplo"]),
        )
        for clave, datos in sorted(agregados.items(), key=lambda kv: -kv[1]["transacciones"])
    ]

    total_detalle = sin_agrupador.with_entities(func.count(Nutriente.nutrienteid)).scalar() or 0
    filas_detalle = (
        sin_agrupador.order_by(Nutriente.NombreComercial, Nutriente.nutrienteid)
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )

    return ExcepcionesNutrientesResponse(
        resumen=resumen,
        detalle=PaginaDetalleExcepcionesNutrientes(
            total=total_detalle,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
            filas=[
                DetalleExcepcionNutriente(
                    no_licencia=fila.No_Licencia,
                    nombre_comercial=fila.NombreComercial,
                    nombre_key=normalizar(fila.NombreComercial),
                )
                for fila in filas_detalle
            ],
        ),
    )


@router.patch("/plaguicidas/agrupador", response_model=ActualizarAgrupadorResponse)
def actualizar_agrupador_plaguicidas(
    payload: ActualizarAgrupadorPlaguicidasRequest, db: Session = Depends(get_db)
) -> ActualizarAgrupadorResponse:
    """Asigna un Agrupador a una clave de ingrediente activo — inserta o
    actualiza el catálogo, y de inmediato sincroniza Grupo/CodigoAgrupador
    en TODAS las filas de dbo.Importacion que comparten esa clave (no
    solo la fila que se estaba editando en pantalla)."""
    clave = payload.ingrediente_key.strip().upper()
    agrupador = payload.agrupador.strip()
    if not clave or not agrupador:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La clave y el agrupador no pueden estar vacíos.",
        )

    existe = db.execute(
        text("SELECT 1 FROM dbo.CatalogoNomenclaturaPlaguicidas WHERE IngredienteActivo_Key = :k"),
        {"k": clave},
    ).scalar()
    if existe:
        db.execute(
            text(
                "UPDATE dbo.CatalogoNomenclaturaPlaguicidas SET Agrupador = :a, FechaMod = GETDATE() "
                "WHERE IngredienteActivo_Key = :k"
            ),
            {"a": agrupador, "k": clave},
        )
    else:
        db.execute(
            text(
                "INSERT INTO dbo.CatalogoNomenclaturaPlaguicidas (IngredienteActivo_Key, Agrupador, Codigo, FechaMod) "
                "VALUES (:k, :a, NULL, GETDATE())"
            ),
            {"k": clave, "a": agrupador},
        )

    filas_actualizadas = sincronizar_agrupador_plaguicidas(db)
    db.commit()
    return ActualizarAgrupadorResponse(filas_actualizadas=filas_actualizadas)


@router.patch("/nutrientes/agrupador", response_model=ActualizarAgrupadorResponse)
def actualizar_agrupador_nutrientes(
    payload: ActualizarAgrupadorNutrientesRequest, db: Session = Depends(get_db)
) -> ActualizarAgrupadorResponse:
    """Igual que actualizar_agrupador_plaguicidas, pero contra el
    catálogo de nombres comerciales de nutrientes."""
    clave = payload.nombre_key.strip().upper()
    agrupador = payload.agrupador.strip()
    if not clave or not agrupador:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La clave y el agrupador no pueden estar vacíos.",
        )

    existe = db.execute(
        text("SELECT 1 FROM dbo.CatalogoAgrupadorNutrientes WHERE NombreComercial_Key = :k"),
        {"k": clave},
    ).scalar()
    if existe:
        db.execute(
            text(
                "UPDATE dbo.CatalogoAgrupadorNutrientes SET ProductoAgrupado = :a, FechaMod = GETDATE() "
                "WHERE NombreComercial_Key = :k"
            ),
            {"a": agrupador, "k": clave},
        )
    else:
        db.execute(
            text(
                "INSERT INTO dbo.CatalogoAgrupadorNutrientes (NombreComercial_Key, ProductoAgrupado, Codigo, FechaMod) "
                "VALUES (:k, :a, NULL, GETDATE())"
            ),
            {"k": clave, "a": agrupador},
        )

    filas_actualizadas = sincronizar_agrupador_nutrientes(db)
    db.commit()
    return ActualizarAgrupadorResponse(filas_actualizadas=filas_actualizadas)

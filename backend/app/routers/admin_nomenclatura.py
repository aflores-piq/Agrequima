"""Catálogos de nomenclatura/agrupación (plaguicidas y nutrientes).

Cada pantalla tiene dos secciones: (a) buscar y editar lo que ya está
en el catálogo, y (b) revisar los ítems SIN agrupador todavía
(Grupo/ProductoAgrupado IS NULL en dbo.Importacion / dbo.Nutrientes) —
esta segunda sección reemplaza a la antigua pantalla de "Excepciones"
(eliminada: su PATCH no disparaba sincronizar_agrupador_* de forma
consistente, ver services/sincronizacion_agrupador.py). Ambas
secciones editan a través del MISMO endpoint PUT de abajo, que además
de guardar el catálogo sincroniza de inmediato Grupo/CodigoAgrupador
(o ProductoAgrupado/CodigoAgrupador) en todas las filas ya cargadas que
comparten esa clave — así el ítem deja de aparecer en "sin agrupador"
al instante, sin depender de una recarga de datos aparte."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.importacion import Importacion
from app.models.nomenclatura import CatalogoAgrupadorNutrientes, CatalogoNomenclaturaPlaguicidas
from app.models.nutriente import Nutriente
from app.schemas.nomenclatura import (
    AgrupadorNutrienteItem,
    AgrupadorNutrienteUpdate,
    DetalleSinAgrupadorNutriente,
    DetalleSinAgrupadorPlaguicida,
    NomenclaturaPlaguicidaItem,
    NomenclaturaPlaguicidaUpdate,
    PaginaAgrupadorNutrientes,
    PaginaDetalleSinAgrupadorNutrientes,
    PaginaDetalleSinAgrupadorPlaguicidas,
    PaginaNomenclaturaPlaguicidas,
    ResumenSinAgrupadorNutriente,
    ResumenSinAgrupadorPlaguicida,
    SinAgrupadorNutrientesResponse,
    SinAgrupadorPlaguicidasResponse,
)
from app.services.sincronizacion_agrupador import (
    sincronizar_agrupador_nutrientes,
    sincronizar_agrupador_plaguicidas,
)
from app.services.text_utils import normalizar, parece_error_captura

router = APIRouter(
    prefix="/admin/nomenclatura",
    tags=["admin-nomenclatura"],
    dependencies=[Depends(require_role("Administrador"))],
)


@router.get("/plaguicidas", response_model=PaginaNomenclaturaPlaguicidas)
def listar_nomenclatura_plaguicidas(
    busqueda: str | None = None,
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> PaginaNomenclaturaPlaguicidas:
    query = db.query(CatalogoNomenclaturaPlaguicidas)
    if busqueda:
        patron = f"%{busqueda}%"
        query = query.filter(
            or_(
                CatalogoNomenclaturaPlaguicidas.IngredienteActivo_Key.ilike(patron),
                CatalogoNomenclaturaPlaguicidas.Agrupador.ilike(patron),
            )
        )

    total = query.with_entities(func.count(CatalogoNomenclaturaPlaguicidas.IngredienteActivo_Key)).scalar() or 0
    filas = (
        query.order_by(CatalogoNomenclaturaPlaguicidas.IngredienteActivo_Key)
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )

    return PaginaNomenclaturaPlaguicidas(
        total=total,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
        filas=[
            NomenclaturaPlaguicidaItem(
                ingrediente_key=fila.IngredienteActivo_Key,
                agrupador=fila.Agrupador,
                codigo=fila.Codigo,
                fecha_mod=fila.FechaMod,
            )
            for fila in filas
        ],
    )


@router.get("/plaguicidas/sin-agrupador", response_model=SinAgrupadorPlaguicidasResponse)
def sin_agrupador_plaguicidas(
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> SinAgrupadorPlaguicidasResponse:
    """Transacciones cuyo ingrediente activo todavía no tiene agrupador
    en el catálogo (Importacion.Grupo IS NULL) — consulta el estado
    ACTUAL de dbo.Importacion, así que queda al día automáticamente en
    cuanto se asigna un agrupador desde la sección de arriba, sin
    depender de cuál fue la última carga."""
    sin_agrupador = db.query(Importacion).filter(
        Importacion.Grupo.is_(None), Importacion.ingrediente_act.isnot(None)
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
        ResumenSinAgrupadorPlaguicida(
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

    return SinAgrupadorPlaguicidasResponse(
        resumen=resumen,
        detalle=PaginaDetalleSinAgrupadorPlaguicidas(
            total=total_detalle,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
            filas=[
                DetalleSinAgrupadorPlaguicida(
                    recibointerno=fila.recibointerno,
                    ingrediente_act=fila.ingrediente_act,
                    ingrediente_key=normalizar(fila.ingrediente_act),
                    producto=fila.producto,
                )
                for fila in filas_detalle
            ],
        ),
    )


@router.put("/plaguicidas/{ingrediente_key}", response_model=NomenclaturaPlaguicidaItem)
def actualizar_nomenclatura_plaguicida(
    ingrediente_key: str,
    payload: NomenclaturaPlaguicidaUpdate,
    db: Session = Depends(get_db),
) -> NomenclaturaPlaguicidaItem:
    fila = db.get(CatalogoNomenclaturaPlaguicidas, ingrediente_key)
    if fila is None:
        fila = CatalogoNomenclaturaPlaguicidas(IngredienteActivo_Key=ingrediente_key)
        db.add(fila)

    fila.Agrupador = payload.agrupador
    fila.Codigo = payload.codigo
    fila.FechaMod = datetime.now(timezone.utc)
    db.flush()
    # Propaga de inmediato a TODAS las filas de Importacion que
    # comparten esta clave (no solo la que se estaba editando) — sin
    # esto, la sección "sin agrupador" no reflejaría el cambio.
    sincronizar_agrupador_plaguicidas(db)
    db.commit()
    db.refresh(fila)

    return NomenclaturaPlaguicidaItem(
        ingrediente_key=fila.IngredienteActivo_Key,
        agrupador=fila.Agrupador,
        codigo=fila.Codigo,
        fecha_mod=fila.FechaMod,
    )


@router.get("/nutrientes", response_model=PaginaAgrupadorNutrientes)
def listar_agrupador_nutrientes(
    busqueda: str | None = None,
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> PaginaAgrupadorNutrientes:
    query = db.query(CatalogoAgrupadorNutrientes)
    if busqueda:
        patron = f"%{busqueda}%"
        query = query.filter(
            or_(
                CatalogoAgrupadorNutrientes.NombreComercial_Key.ilike(patron),
                CatalogoAgrupadorNutrientes.ProductoAgrupado.ilike(patron),
            )
        )

    total = query.with_entities(func.count(CatalogoAgrupadorNutrientes.NombreComercial_Key)).scalar() or 0
    filas = (
        query.order_by(CatalogoAgrupadorNutrientes.NombreComercial_Key)
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )

    return PaginaAgrupadorNutrientes(
        total=total,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
        filas=[
            AgrupadorNutrienteItem(
                nombre_key=fila.NombreComercial_Key,
                producto_agrupado=fila.ProductoAgrupado,
                codigo=fila.Codigo,
                fecha_mod=fila.FechaMod,
            )
            for fila in filas
        ],
    )


@router.get("/nutrientes/sin-agrupador", response_model=SinAgrupadorNutrientesResponse)
def sin_agrupador_nutrientes(
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> SinAgrupadorNutrientesResponse:
    """Igual que sin_agrupador_plaguicidas, pero contra licencias de
    nutrientes sin producto agrupado (Nutrientes.ProductoAgrupado IS
    NULL)."""
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
        ResumenSinAgrupadorNutriente(
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

    return SinAgrupadorNutrientesResponse(
        resumen=resumen,
        detalle=PaginaDetalleSinAgrupadorNutrientes(
            total=total_detalle,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
            filas=[
                DetalleSinAgrupadorNutriente(
                    no_licencia=fila.No_Licencia,
                    nombre_comercial=fila.NombreComercial,
                    nombre_key=normalizar(fila.NombreComercial),
                )
                for fila in filas_detalle
            ],
        ),
    )


@router.put("/nutrientes/{nombre_key}", response_model=AgrupadorNutrienteItem)
def actualizar_agrupador_nutriente(
    nombre_key: str,
    payload: AgrupadorNutrienteUpdate,
    db: Session = Depends(get_db),
) -> AgrupadorNutrienteItem:
    fila = db.get(CatalogoAgrupadorNutrientes, nombre_key)
    if fila is None:
        fila = CatalogoAgrupadorNutrientes(NombreComercial_Key=nombre_key)
        db.add(fila)

    fila.ProductoAgrupado = payload.producto_agrupado
    fila.Codigo = payload.codigo
    fila.FechaMod = datetime.now(timezone.utc)
    db.flush()
    sincronizar_agrupador_nutrientes(db)
    db.commit()
    db.refresh(fila)

    return AgrupadorNutrienteItem(
        nombre_key=fila.NombreComercial_Key,
        producto_agrupado=fila.ProductoAgrupado,
        codigo=fila.Codigo,
        fecha_mod=fila.FechaMod,
    )

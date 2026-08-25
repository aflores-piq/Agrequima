from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.nomenclatura import CatalogoAgrupadorNutrientes, CatalogoNomenclaturaPlaguicidas
from app.schemas.nomenclatura import (
    AgrupadorNutrienteItem,
    AgrupadorNutrienteUpdate,
    NomenclaturaPlaguicidaItem,
    NomenclaturaPlaguicidaUpdate,
    PaginaAgrupadorNutrientes,
    PaginaNomenclaturaPlaguicidas,
)

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
    db.commit()
    db.refresh(fila)

    return AgrupadorNutrienteItem(
        nombre_key=fila.NombreComercial_Key,
        producto_agrupado=fila.ProductoAgrupado,
        codigo=fila.Codigo,
        fecha_mod=fila.FechaMod,
    )

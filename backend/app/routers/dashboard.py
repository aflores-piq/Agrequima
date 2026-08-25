from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import UsuarioToken, get_current_user, require_export_permission
from app.schemas.dashboard import (
    DashboardNutrientesResponse,
    DashboardPlaguicidasResponse,
    OpcionesFiltroNutrientes,
    OpcionesFiltroPlaguicidas,
)
from app.services import export as export_service
from app.services.dashboard_nutrientes import (
    construir_contexto_nutrientes,
    obtener_dashboard_nutrientes,
    obtener_opciones_filtro_nutrientes,
)
from app.services.dashboard_plaguicidas import (
    construir_contexto_plaguicidas,
    obtener_dashboard_plaguicidas,
    obtener_opciones_filtro_plaguicidas,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/plaguicidas", response_model=DashboardPlaguicidasResponse)
def dashboard_plaguicidas(
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12, description="'Hasta el mes'; por defecto el último con datos"),
    origen: list[str] | None = Query(None),
    ingrediente_act: list[str] | None = Query(None),
    aplicacion: list[str] | None = Query(None),
    producto: list[str] | None = Query(None),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(get_current_user),
) -> DashboardPlaguicidasResponse:
    return obtener_dashboard_plaguicidas(
        db, anio, mes, origen, ingrediente_act, aplicacion, producto, pagina, tamano_pagina
    )


@router.get("/plaguicidas/opciones", response_model=OpcionesFiltroPlaguicidas)
def opciones_dashboard_plaguicidas(
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(get_current_user),
) -> OpcionesFiltroPlaguicidas:
    return obtener_opciones_filtro_plaguicidas(db)


@router.get("/nutrientes", response_model=DashboardNutrientesResponse)
def dashboard_nutrientes(
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12, description="'Hasta el mes'; por defecto el último con datos"),
    nombre_comercial: list[str] | None = Query(None),
    origen: list[str] | None = Query(None),
    componente: list[str] | None = Query(None),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(get_current_user),
) -> DashboardNutrientesResponse:
    return obtener_dashboard_nutrientes(
        db, anio, mes, nombre_comercial, origen, componente, pagina, tamano_pagina
    )


@router.get("/nutrientes/opciones", response_model=OpcionesFiltroNutrientes)
def opciones_dashboard_nutrientes(
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(get_current_user),
) -> OpcionesFiltroNutrientes:
    return obtener_opciones_filtro_nutrientes(db)


def _respuesta_xlsx(contenido: bytes, nombre_archivo: str) -> Response:
    return Response(
        content=contenido,
        media_type=export_service.MEDIA_TYPE_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("/plaguicidas/export/{elemento}")
def exportar_plaguicidas_elemento(
    elemento: str,
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
    origen: list[str] | None = Query(None),
    ingrediente_act: list[str] | None = Query(None),
    aplicacion: list[str] | None = Query(None),
    producto: list[str] | None = Query(None),
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(require_export_permission),
) -> Response:
    registro = export_service.PLAGUICIDAS_ELEMENTOS.get(elemento)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Elemento de exportación desconocido: {elemento}")
    ctx = construir_contexto_plaguicidas(db, anio, mes, origen, ingrediente_act, aplicacion, producto)
    contenido = export_service.generar_excel_elemento(ctx, registro)
    nombre_archivo = f"plaguicidas_{elemento.replace('-', '_')}_{ctx.anio_actual}.xlsx"
    return _respuesta_xlsx(contenido, nombre_archivo)


@router.get("/plaguicidas/export-todo")
def exportar_plaguicidas_todo(
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
    origen: list[str] | None = Query(None),
    ingrediente_act: list[str] | None = Query(None),
    aplicacion: list[str] | None = Query(None),
    producto: list[str] | None = Query(None),
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(require_export_permission),
) -> Response:
    ctx = construir_contexto_plaguicidas(db, anio, mes, origen, ingrediente_act, aplicacion, producto)
    contenido = export_service.generar_excel_todo(ctx, export_service.PLAGUICIDAS_ELEMENTOS)
    nombre_archivo = f"plaguicidas_completo_{ctx.anio_actual}.xlsx"
    return _respuesta_xlsx(contenido, nombre_archivo)


@router.get("/nutrientes/export/{elemento}")
def exportar_nutrientes_elemento(
    elemento: str,
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
    nombre_comercial: list[str] | None = Query(None),
    origen: list[str] | None = Query(None),
    componente: list[str] | None = Query(None),
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(require_export_permission),
) -> Response:
    registro = export_service.NUTRIENTES_ELEMENTOS.get(elemento)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Elemento de exportación desconocido: {elemento}")
    ctx = construir_contexto_nutrientes(db, anio, mes, nombre_comercial, origen, componente)
    contenido = export_service.generar_excel_elemento(ctx, registro)
    nombre_archivo = f"nutrientes_{elemento.replace('-', '_')}_{ctx.anio_actual}.xlsx"
    return _respuesta_xlsx(contenido, nombre_archivo)


@router.get("/nutrientes/export-todo")
def exportar_nutrientes_todo(
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
    nombre_comercial: list[str] | None = Query(None),
    origen: list[str] | None = Query(None),
    componente: list[str] | None = Query(None),
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(require_export_permission),
) -> Response:
    ctx = construir_contexto_nutrientes(db, anio, mes, nombre_comercial, origen, componente)
    contenido = export_service.generar_excel_todo(ctx, export_service.NUTRIENTES_ELEMENTOS)
    nombre_archivo = f"nutrientes_completo_{ctx.anio_actual}.xlsx"
    return _respuesta_xlsx(contenido, nombre_archivo)

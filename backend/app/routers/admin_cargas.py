from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import UsuarioToken, require_role
from app.models.auditoria import AuditoriaCarga
from app.models.usuario import Usuario
from app.schemas.cargas import (
    AuditoriaCargaItem,
    PaginaAuditoriaCargas,
    ResumenCargaNutrientes,
    ResumenCargaPlaguicidas,
)
from app.services.etl_nutrientes import procesar_carga_nutrientes
from app.services.etl_plaguicidas import procesar_carga_plaguicidas

router = APIRouter(prefix="/admin/cargas", tags=["admin-cargas"])

_EXTENSIONES_EXCEL = (".xlsx", ".xls")


def _validar_extension_excel(archivo: UploadFile, etiqueta: str) -> None:
    nombre = archivo.filename or ""
    if not nombre.lower().endswith(_EXTENSIONES_EXCEL):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo de {etiqueta} debe ser un Excel (.xlsx/.xls).",
        )


def _validar_extension_excel_o_csv(archivo: UploadFile, etiqueta: str) -> None:
    nombre = archivo.filename or ""
    if not nombre.lower().endswith(_EXTENSIONES_EXCEL + (".csv",)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo de {etiqueta} debe ser un Excel (.xlsx/.xls) o un CSV (.csv).",
        )


@router.post("/plaguicidas", response_model=ResumenCargaPlaguicidas)
async def cargar_plaguicidas(
    archivo_importaciones: UploadFile = File(...),
    archivo_nomenclatura: UploadFile | None = File(None),
    usuario: UsuarioToken = Depends(require_role("Administrador")),
) -> ResumenCargaPlaguicidas:
    _validar_extension_excel_o_csv(archivo_importaciones, "importaciones")
    if archivo_nomenclatura is not None:
        _validar_extension_excel(archivo_nomenclatura, "nomenclatura")

    contenido_importaciones = await archivo_importaciones.read()
    contenido_nomenclatura = (
        await archivo_nomenclatura.read() if archivo_nomenclatura is not None else None
    )

    try:
        return procesar_carga_plaguicidas(
            contenido_importaciones=contenido_importaciones,
            nombre_archivo_importaciones=archivo_importaciones.filename,
            contenido_nomenclatura=contenido_nomenclatura,
            usuario_id=usuario.usuario_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/historial", response_model=PaginaAuditoriaCargas)
def historial_cargas(
    tipo: str | None = Query(None, description="'Plaguicidas' o 'Nutrientes'"),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _usuario: UsuarioToken = Depends(require_role("Administrador")),
) -> PaginaAuditoriaCargas:
    query = db.query(AuditoriaCarga, Usuario.NombreUsuario).outerjoin(
        Usuario, AuditoriaCarga.UsuarioId == Usuario.UsuarioId
    )
    if tipo:
        query = query.filter(AuditoriaCarga.TipoCarga == tipo)

    total = query.with_entities(AuditoriaCarga.CargaId).count()
    filas = (
        query.order_by(AuditoriaCarga.FechaCarga.desc())
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )

    return PaginaAuditoriaCargas(
        total=total,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
        filas=[
            AuditoriaCargaItem(
                carga_id=carga.CargaId,
                tipo_carga=carga.TipoCarga,
                nombre_archivo=carga.NombreArchivo,
                usuario=nombre_usuario,
                fecha_carga=carga.FechaCarga,
                filas_procesadas=carga.FilasProcesadas,
                filas_con_excepcion=carga.FilasConExcepcion,
                estado=carga.Estado,
                mensaje_error=carga.MensajeError,
            )
            for carga, nombre_usuario in filas
        ],
    )


@router.post("/nutrientes", response_model=ResumenCargaNutrientes)
async def cargar_nutrientes(
    archivo_nutrientes: UploadFile = File(...),
    archivo_agrupador: UploadFile | None = File(None),
    usuario: UsuarioToken = Depends(require_role("Administrador")),
) -> ResumenCargaNutrientes:
    _validar_extension_excel_o_csv(archivo_nutrientes, "licencias de nutrientes")
    if archivo_agrupador is not None:
        _validar_extension_excel(archivo_agrupador, "agrupador de fertilizantes")

    contenido_nutrientes = await archivo_nutrientes.read()
    contenido_agrupador = (
        await archivo_agrupador.read() if archivo_agrupador is not None else None
    )

    try:
        return procesar_carga_nutrientes(
            contenido_nutrientes=contenido_nutrientes,
            nombre_archivo_nutrientes=archivo_nutrientes.filename,
            contenido_agrupador=contenido_agrupador,
            usuario_id=usuario.usuario_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

"""Indicadores > Viáticos > «Resumen General».

Todas las rutas exigen AccesoIndicadores (require_acceso_indicadores): un usuario sin ese acceso recibe 403 sin
que el mensaje nombre el módulo. Ver services/dashboard_indicadores.py para las consultas."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import UsuarioToken, require_acceso_indicadores
from app.services import dashboard_indicadores as svc

router = APIRouter(prefix="/dashboard/indicadores", tags=["indicadores"])


class MesDisponible(BaseModel):
    anio: int
    mes: int
    etiqueta: str
    filas: int


class MesPorDefecto(BaseModel):
    anio: int
    mes: int


class MesesOut(BaseModel):
    meses: list[MesDisponible]
    por_defecto: MesPorDefecto | None


class PuntoMes(BaseModel):
    anio: int
    mes: int
    valor: float


class TarjetaOut(BaseModel):
    clave: str
    etiqueta: str
    formato: str
    valor: float
    valor_anio_anterior: float | None
    variacion_pct: float | None
    ultimos_12_meses: list[PuntoMes]


class TarjetasOut(BaseModel):
    anio: int
    mes: int
    etiqueta_mes: str
    titulo: str
    periodo_parcial: bool
    dia_corte: int | None
    texto_comparacion: str
    tarjetas: list[TarjetaOut]


class PuntoAcumulado(BaseModel):
    mes: int
    etiqueta: str
    acumulado: float | None


class AcumuladoOut(BaseModel):
    anio: int
    anio_anterior: int
    mes: int
    serie_actual: list[PuntoAcumulado]
    serie_anterior: list[PuntoAcumulado]


class DatoAgrupado(BaseModel):
    nombre: str
    total_gastos: float


class AgrupadoOut(BaseModel):
    anio: int
    mes: int
    total: float
    datos: list[DatoAgrupado]


class FilaDetalle(BaseModel):
    fecha_documento: str | None
    fecha_inicial: str | None
    fecha_final: str | None
    tecnico: str | None
    tipo_gasto: str | None
    motivo: str | None
    total_factura: float
    proveedor: str | None


class DetalleOut(BaseModel):
    anio: int
    mes: int
    total_factura: float
    filas: list[FilaDetalle]


def _periodo(
    anio: int = Query(..., ge=2000, le=2100, description="Año del filtro «Año y Mes»"),
    mes: int = Query(..., ge=1, le=12, description="Mes (1-12) del filtro «Año y Mes»"),
) -> tuple[int, int]:
    return anio, mes


@router.get("/resumen-general/meses", response_model=MesesOut)
def meses(db: Session = Depends(get_db), _: UsuarioToken = Depends(require_acceso_indicadores)) -> dict:
    """Meses con datos para el filtro «Año y Mes»; por defecto, el último mes con datos."""
    return svc.meses_disponibles(db)


@router.get("/resumen-general/tarjetas", response_model=TarjetasOut)
def tarjetas(
    periodo: tuple[int, int] = Depends(_periodo),
    db: Session = Depends(get_db),
    _: UsuarioToken = Depends(require_acceso_indicadores),
) -> dict:
    return svc.tarjetas(db, *periodo)


@router.get("/resumen-general/acumulado", response_model=AcumuladoOut)
def acumulado(
    periodo: tuple[int, int] = Depends(_periodo),
    db: Session = Depends(get_db),
    _: UsuarioToken = Depends(require_acceso_indicadores),
) -> dict:
    return svc.acumulado(db, *periodo)


@router.get("/resumen-general/tipos-gasto", response_model=AgrupadoOut)
def tipos_gasto(
    periodo: tuple[int, int] = Depends(_periodo),
    db: Session = Depends(get_db),
    _: UsuarioToken = Depends(require_acceso_indicadores),
) -> dict:
    return svc.tipos_gasto(db, *periodo)


@router.get("/resumen-general/colaboradores", response_model=AgrupadoOut)
def colaboradores(
    periodo: tuple[int, int] = Depends(_periodo),
    db: Session = Depends(get_db),
    _: UsuarioToken = Depends(require_acceso_indicadores),
) -> dict:
    return svc.colaboradores(db, *periodo)


@router.get("/resumen-general/detalle", response_model=DetalleOut)
def detalle(
    periodo: tuple[int, int] = Depends(_periodo),
    db: Session = Depends(get_db),
    _: UsuarioToken = Depends(require_acceso_indicadores),
) -> dict:
    return svc.detalle(db, *periodo)

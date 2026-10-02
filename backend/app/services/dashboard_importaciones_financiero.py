"""Cálculos de "Importaciones" DENTRO del módulo Financiero (sub-sección
hermana de "Presupuestos" en el Sidebar) -- distinta del dashboard
"Importaciones" (Plaguicidas/Nutrientes, dashboard_plaguicidas.py): esta
lee la MISMA tabla dbo.Importacion pero agrupada por institucion
(Agrequima/Gremiagro), fuente real de ingresos de la gremial por
importaciones, confirmada con pbixray contra el .pbix real
(PIQ_AGREQUIMA.pbix). SQL crudo vía text(), sin ORM, mismo patrón que
dashboard_otros_informes.py.

--- Fuente y estructura --------------------------------------------------

dbo.Importacion (misma tabla, MISMO esquema que usa Plaguicidas):
    anio, fecha (varchar 'YYYY/MM/DD'), institucion ('Agrequima' |
    'Gremiagro'), cantidad, cif_USD. Mes = MONTH(fecha) (confirmado en
    el Power Query real: `month(Importacion[fecha])`).

En la base de desarrollo (AGREQUIMA, DESARROLLO-2) hay datos reales
2025 (12 meses completos) y 2026 (solo Enero-Julio) -- SIN 2024. La
comparación "año vs año-1" para año=2025 (año-1=2024) no se puede
probar en vivo contra esta base: se validó por separado leyendo la
tabla cacheada del .pbix con pbixray (que sí trae 2023-2026), donde SÍ
existe 2024 -- ver bitácora para el detalle de esa verificación.
Pendiente de confirmar: si el servidor real (PIQ_IA) tiene 2024 cargado
para dbo.Importacion (no se pudo verificar desde esta sesión, sin
conexión al servidor de producción).

--- Fórmulas CONFIRMADAS contra los números de control reales ------------

Ingresos por importación / Comparativo (tabla CIF por mes):
    CIF(mes, año) = SUM(cif_USD) WHERE anio=año AND MONTH(fecha)=mes
        [AND institucion=X en los bloques de Comparativo].
    % año-1 (de cada fila) = CIF(mes, año-1) / TOTAL completo de año-1
        (los 12 meses reales que tenga ESE año, sea cual sea -- NO
        limitado a los meses del año actual). ROUND 1 decimal.
    % año actual = CIF(mes, año) / TOTAL completo de año actual (todos
        los meses reales que tenga, sea cual sea). ROUND 1 decimal.
    Diferencia (VAR) = CIF(mes,año) - CIF(mes,año-1).
    VAR % = VAR / CIF(mes,año-1) -- equivalente confirmado numéricamente
        a la medida real VariacionAnualPorcentaje.
    Fila "Total año": el CIF de año-1 mostrado en Q suma SOLO los meses
        que también existen en el año actual (no los 12 completos de
        año-1) -- confirmado exacto contra el control (Ene-Jul 2025 =
        Q182,736,770 cuando el año actual solo llega a julio). Las 2
        columnas de % de esta fila son SIEMPRE 100.00% fijo (no una
        razón calculada) -- así lo pidió/confirmó el usuario.

Kilolitros (precio por kilolitro y cambio de cantidad):
    Tarjetas de cambio de cantidad = SUM(cantidad) ACUMULADO de enero al
        mes seleccionado, año vs año-1 (mismo patrón que "Total año"
        de arriba, pero con cantidad en vez de cif_USD, y siempre
        acumulado -- confirmado exacto con pbixray: 2025 vs 2024 a
        julio da 14.35% / 16.58% / 11.81%, igual que el control).
    Precio por kilolitro (tabla) = CIF/cantidad del MES SELECCIONADO
        SOLAMENTE, SIN acumular -- a pesar de que el título de la
        página dice "Acumulado", así es como el DAX real lo calcula
        (confirmado exacto con pbixray: julio 2024/2025 y agosto 2025
        dan exactos los 6 números de control). Si el año actual no
        tiene ninguna fila en ese mes específico, el valor de esa
        columna es None (el frontend muestra "—").

Contribución 4.5 por millar (cuenta 410104001):
    Realizado(mes) = SUM(Creditos)-SUM(Debitos) de dbo.BalanceSaldos,
        Cta_Codigo=410104001, Sal_Ano/Sal_Mes exactos (sin acumular).
    Realizado acumulado / Presupuesto acumulado = mismo patrón "N" ya
        usado en Presupuestos (par_mes <= mes seleccionado, mismo año).
    dbo.Presupuestos NO tiene ninguna fila para esta cuenta en 2026 (sí
        las 12 de 2025) -- el % de ejecución y el "Presupuesto {Año}"
        de la gráfica quedan vacíos/"Sin presupuesto" en 2026, tal como
        ya preveía el usuario en su propia instrucción.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.dashboard_importaciones_financiero import (
    BloqueComparativoInstitucion,
    ContribucionMillarResponse,
    FilaCIFMes,
    FilaPrecioKilolitro,
    ImportacionComparativoResponse,
    IngresosImportacionResponse,
    KilolitrosResponse,
    PuntoCIFMes,
    PuntoContribucionMes,
    PuntoPrecioMes,
    TarjetaCambioCantidad,
    TarjetaResumenContribucion,
)
from app.services.dashboard_otros_informes import _periodos_disponibles_gastos

MESES_LARGOS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

_CTA_MILLAR = "410104001"

# dbo.Importacion trae, en el servidor real, filas con `anio` corrupto:
# +100 años por un error de captura viejo (ej. 20126 en vez de 2026) y
# copias duplicadas con el signo invertido (ej. -2024, mismo contenido,
# ID distinto) -- confirmado por el cliente, pendiente de limpieza en
# origen. Ninguna pantalla de Importaciones del Financiero (selectores
# de año, sumas, acumulados) debe contarlas.
#
# SIN años fijos (instrucción explícita del cliente: "no deberían de
# existir años fijos") -- la regla es RELATIVA a hoy, no una lista ni
# un rango de calendario hardcodeado: `anio` tiene que ser positivo (
# descarta las copias con signo invertido) y no puede ser mayor al año
# en curso (descarta el +100 años -- 20126 nunca es <= YEAR(GETDATE()),
# sin importar qué año sea "hoy"). No hace falta tocar este código cada
# año nuevo: la cota se recalcula sola en cada consulta.
_FILTRO_ANIO_VALIDO = "anio > 0 AND anio <= YEAR(GETDATE())"


def _num(valor) -> float:
    return float(valor) if valor is not None else 0.0


# --- Utilidades comunes sobre dbo.Importacion -----------------------------


def _anios_disponibles_importacion(db: Session) -> list[int]:
    filas = db.execute(
        text(f"SELECT DISTINCT anio FROM dbo.Importacion WHERE {_FILTRO_ANIO_VALIDO} ORDER BY anio")
    ).all()
    return [int(a) for (a,) in filas if a is not None]


def _cif_por_mes(db: Session, anio: int, institucion: str | None) -> dict[int, float]:
    filtro = "AND institucion = :institucion" if institucion else ""
    params: dict = {"anio": anio}
    if institucion:
        params["institucion"] = institucion
    filas = db.execute(
        text(
            f"""
            SELECT CAST(SUBSTRING(fecha, 6, 2) AS INT) AS mes, SUM(cif_USD) AS cif
            FROM dbo.Importacion
            WHERE anio = :anio AND {_FILTRO_ANIO_VALIDO} {filtro}
            GROUP BY CAST(SUBSTRING(fecha, 6, 2) AS INT)
            """
        ),
        params,
    ).all()
    return {int(m): _num(c) for m, c in filas}


def _cif_total_anio(db: Session, anio: int, institucion: str | None) -> float:
    filtro = "AND institucion = :institucion" if institucion else ""
    params: dict = {"anio": anio}
    if institucion:
        params["institucion"] = institucion
    valor = db.execute(
        text(f"SELECT SUM(cif_USD) FROM dbo.Importacion WHERE anio = :anio AND {_FILTRO_ANIO_VALIDO} {filtro}"), params
    ).scalar()
    return _num(valor)


def _construir_bloque_cif(
    db: Session, anio: int, institucion: str | None
) -> tuple[list[FilaCIFMes], FilaCIFMes, list[PuntoCIFMes], bool]:
    anio_anterior = anio - 1
    # Si el año anterior no tiene NINGUNA fila (p.ej. 2024 en desarrollo),
    # no hay serie real que mostrar -- se devuelve el flag para que el
    # frontend no dibuje esa línea/leyenda/cajitas "$0" y las columnas de
    # la tabla muestren "—" en vez de un 0 engañoso (parecido al fix ya
    # hecho en Kilolitros para el mismo hueco de datos).
    hay_anterior = _tiene_datos_anio(db, anio_anterior, institucion)
    cif_actual = _cif_por_mes(db, anio, institucion)
    cif_anterior_por_mes = _cif_por_mes(db, anio_anterior, institucion) if hay_anterior else {}
    total_actual = _cif_total_anio(db, anio, institucion)
    total_anterior = _cif_total_anio(db, anio_anterior, institucion) if hay_anterior else 0.0

    meses_con_datos = sorted(cif_actual.keys())
    filas: list[FilaCIFMes] = []
    grafico: list[PuntoCIFMes] = []
    for m in meses_con_datos:
        c_act = cif_actual.get(m, 0.0)
        c_ant = cif_anterior_por_mes.get(m, 0.0) if hay_anterior else None
        var = (c_act - c_ant) if c_ant is not None else None
        filas.append(
            FilaCIFMes(
                mes=MESES_LARGOS[m - 1],
                cif_anio_anterior=c_ant,
                pct_anio_anterior=(round(c_ant / total_anterior * 100, 1) if total_anterior else 0.0) if hay_anterior else None,
                cif_anio_actual=c_act,
                pct_anio_actual=round(c_act / total_actual * 100, 1) if total_actual else 0.0,
                variacion=var,
                variacion_pct=(round(var / c_ant * 100, 2) if c_ant else 0.0) if var is not None else None,
            )
        )
        grafico.append(PuntoCIFMes(mes=MESES_LARGOS[m - 1], cif_anio_anterior=c_ant, cif_anio_actual=c_act))

    # "Total año": el valor en Q de año-1 suma SOLO los meses que
    # también existen en el año actual (no los 12 completos de año-1) --
    # confirmado exacto contra el control. Las 2 columnas de % de esta
    # fila son 100.00% fijo, no una razón calculada.
    total_cif_actual = sum(f.cif_anio_actual for f in filas)
    total_cif_anterior = sum(f.cif_anio_anterior for f in filas) if hay_anterior else None
    var_total = (total_cif_actual - total_cif_anterior) if total_cif_anterior is not None else None
    fila_total = FilaCIFMes(
        mes="Total año",
        cif_anio_anterior=total_cif_anterior,
        pct_anio_anterior=100.0 if hay_anterior else None,
        cif_anio_actual=total_cif_actual,
        pct_anio_actual=100.0,
        variacion=var_total,
        variacion_pct=(round(var_total / total_cif_anterior * 100, 2) if total_cif_anterior else 0.0) if var_total is not None else None,
        negrita=True,
    )
    return filas, fila_total, grafico, hay_anterior


def _precio_acumulado_por_mes(db: Session, anio: int, institucion: str | None) -> dict[int, float]:
    """Precio = CIF acumulado / cantidad acumulada de enero a cada mes,
    del año dado -- usado SOLO en la gráfica de líneas de precio de
    "Ingresos por importación" (screen 1b), que sí es una serie
    acumulada real (a diferencia de la tabla de Kilolitros, que usa el
    mes suelto -- ver docstring del módulo)."""
    filtro = "AND institucion = :institucion" if institucion else ""
    params: dict = {"anio": anio}
    if institucion:
        params["institucion"] = institucion
    filas = db.execute(
        text(
            f"""
            SELECT CAST(SUBSTRING(fecha, 6, 2) AS INT) AS mes, SUM(cif_USD) AS cif, SUM(cantidad) AS cantidad
            FROM dbo.Importacion
            WHERE anio = :anio AND {_FILTRO_ANIO_VALIDO} {filtro}
            GROUP BY CAST(SUBSTRING(fecha, 6, 2) AS INT)
            """
        ),
        params,
    ).all()
    por_mes = {int(m): (_num(c), _num(q)) for m, c, q in filas}
    meses = sorted(por_mes.keys())
    resultado: dict[int, float] = {}
    cif_acum = 0.0
    cant_acum = 0.0
    for m in meses:
        cif_acum += por_mes[m][0]
        cant_acum += por_mes[m][1]
        resultado[m] = cif_acum / cant_acum if cant_acum else 0.0
    return resultado


def obtener_ingresos_importacion(db: Session, anio: int | None) -> IngresosImportacionResponse:
    anios_disponibles = _anios_disponibles_importacion(db)
    anio_resuelto = anio if anio is not None else (anios_disponibles[-1] if anios_disponibles else 0)

    filas, fila_total, grafico_cif, hay_anterior = _construir_bloque_cif(db, anio_resuelto, None)

    precio_total = _precio_acumulado_por_mes(db, anio_resuelto, None)
    precio_agre = _precio_acumulado_por_mes(db, anio_resuelto, "Agrequima")
    precio_gre = _precio_acumulado_por_mes(db, anio_resuelto, "Gremiagro")
    meses_precio = sorted(set(precio_total) | set(precio_agre) | set(precio_gre))
    grafico_precio = [
        PuntoPrecioMes(
            mes=MESES_LARGOS[m - 1],
            agrequima=precio_agre.get(m, 0.0),
            gremiagro=precio_gre.get(m, 0.0),
            total=precio_total.get(m, 0.0),
        )
        for m in meses_precio
    ]
    ultimo_mes = meses_precio[-1] if meses_precio else 0

    return IngresosImportacionResponse(
        anio=anio_resuelto,
        anio_anterior=anio_resuelto - 1,
        anio_anterior_sin_datos=not hay_anterior,
        anios_disponibles=anios_disponibles,
        ultimo_mes_con_datos=ultimo_mes,
        filas=filas,
        fila_total=fila_total,
        grafico_cif=grafico_cif,
        grafico_precio=grafico_precio,
    )


def obtener_ingresos_importacion_comparativo(db: Session, anio: int | None) -> ImportacionComparativoResponse:
    anios_disponibles = _anios_disponibles_importacion(db)
    anio_resuelto = anio if anio is not None else (anios_disponibles[-1] if anios_disponibles else 0)

    bloques = []
    for institucion, titulo in [
        ("Gremiagro", f"Comparativo CIF US$ {anio_resuelto - 1} vs. {anio_resuelto} Gremiagro"),
        ("Agrequima", f"Comparativo CIF US$ {anio_resuelto - 1} vs. {anio_resuelto} Agrequima"),
    ]:
        filas, fila_total, grafico, hay_anterior = _construir_bloque_cif(db, anio_resuelto, institucion)
        bloques.append(
            BloqueComparativoInstitucion(
                institucion=institucion,
                titulo=titulo,
                anio_anterior_sin_datos=not hay_anterior,
                filas=filas,
                fila_total=fila_total,
                grafico=grafico,
            )
        )

    return ImportacionComparativoResponse(
        anio=anio_resuelto, anio_anterior=anio_resuelto - 1, anios_disponibles=anios_disponibles, bloques=bloques
    )


# --- 3. Comparación importaciones Kilolitros ------------------------------


def _cantidad_acumulada(db: Session, anio: int, mes_max: int, institucion: str | None) -> float:
    filtro = "AND institucion = :institucion" if institucion else ""
    params: dict = {"anio": anio, "mes_max": mes_max}
    if institucion:
        params["institucion"] = institucion
    valor = db.execute(
        text(
            f"""
            SELECT SUM(cantidad) FROM dbo.Importacion
            WHERE anio = :anio AND {_FILTRO_ANIO_VALIDO} AND CAST(SUBSTRING(fecha, 6, 2) AS INT) <= :mes_max {filtro}
            """
        ),
        params,
    ).scalar()
    return _num(valor)


def _tiene_datos_mes(db: Session, anio: int, mes: int, institucion: str | None) -> bool:
    filtro = "AND institucion = :institucion" if institucion else ""
    params: dict = {"anio": anio, "mes": mes}
    if institucion:
        params["institucion"] = institucion
    valor = db.execute(
        text(
            f"""
            SELECT COUNT(*) FROM dbo.Importacion
            WHERE anio = :anio AND {_FILTRO_ANIO_VALIDO} AND CAST(SUBSTRING(fecha, 6, 2) AS INT) = :mes {filtro}
            """
        ),
        params,
    ).scalar()
    return bool(valor)


def _tiene_datos_anio(db: Session, anio: int, institucion: str | None) -> bool:
    """Si el año NO tiene NINGUNA fila (p.ej. 2024 en la base de
    desarrollo), no hay base de comparación real -- distinto del caso
    "anterior==0 por coincidencia", que sí debe seguir mostrando
    0.00%/aumentó/disminuyó normalmente."""
    filtro = "AND institucion = :institucion" if institucion else ""
    params: dict = {"anio": anio}
    if institucion:
        params["institucion"] = institucion
    valor = db.execute(
        text(f"SELECT COUNT(*) FROM dbo.Importacion WHERE anio = :anio AND {_FILTRO_ANIO_VALIDO} {filtro}"), params
    ).scalar()
    return bool(valor)


def _mensaje_cambio_cantidad(etiqueta_sujeto: str, anio: int, mes: int, db: Session, institucion: str | None) -> str:
    if not _tiene_datos_mes(db, anio, mes, institucion):
        return "El mes seleccionado no tiene datos, por favor, cárguelos."
    if not _tiene_datos_anio(db, anio - 1, institucion):
        return f"Sin datos del año {anio - 1} para comparar."
    actual = _cantidad_acumulada(db, anio, mes, institucion)
    anterior = _cantidad_acumulada(db, anio - 1, mes, institucion)
    if actual == anterior:
        return "No hubo cambio en cantidad"
    if actual > anterior:
        pct = ((actual - anterior) / anterior * 100) if anterior else 0.0
        return f"{etiqueta_sujeto} aumentó {pct:.2f}% en cantidad"
    pct = ((anterior - actual) / anterior * 100) if anterior else 0.0
    return f"{etiqueta_sujeto} disminuyó {pct:.2f}% en cantidad"


def _precio_mes_especifico(db: Session, anio: int, mes: int, institucion: str | None) -> float | None:
    """Precio del MES SELECCIONADO solo (sin acumular) -- ver docstring
    del módulo. None si esa institución no tiene ninguna fila ese mes
    (el frontend muestra "—")."""
    filtro = "AND institucion = :institucion" if institucion else ""
    params: dict = {"anio": anio, "mes": mes}
    if institucion:
        params["institucion"] = institucion
    fila = db.execute(
        text(
            f"""
            SELECT SUM(cif_USD), SUM(cantidad) FROM dbo.Importacion
            WHERE anio = :anio AND {_FILTRO_ANIO_VALIDO} AND CAST(SUBSTRING(fecha, 6, 2) AS INT) = :mes {filtro}
            """
        ),
        params,
    ).first()
    if fila is None or fila[0] is None:
        return None
    cif, cantidad = _num(fila[0]), _num(fila[1])
    return cif / cantidad if cantidad else None


def obtener_kilolitros(db: Session, anio: int | None, mes: int | None) -> KilolitrosResponse:
    periodos = _periodos_disponibles_gastos(db)
    if anio is None or mes is None:
        ultimo = periodos[-1] if periodos else None
        anio_resuelto = anio if anio is not None else (ultimo.anio if ultimo else 0)
        mes_resuelto = mes if mes is not None else (ultimo.mes if ultimo else 0)
    else:
        anio_resuelto, mes_resuelto = anio, mes

    tarjetas = [
        TarjetaCambioCantidad(
            etiqueta="Agrequima-Gremiagro",
            mensaje=_mensaje_cambio_cantidad("Agrequima-Gremiagro", anio_resuelto, mes_resuelto, db, None),
        ),
        TarjetaCambioCantidad(
            etiqueta="Agrequima",
            mensaje=_mensaje_cambio_cantidad("Agrequima", anio_resuelto, mes_resuelto, db, "Agrequima"),
        ),
        TarjetaCambioCantidad(
            etiqueta="Gremiagro",
            mensaje=_mensaje_cambio_cantidad("Gremiagro", anio_resuelto, mes_resuelto, db, "Gremiagro"),
        ),
    ]

    filas_precio = []
    for etiqueta, institucion in [("Total", None), ("Agrequima", "Agrequima"), ("Gremiagro", "Gremiagro")]:
        p_ant = _precio_mes_especifico(db, anio_resuelto - 1, mes_resuelto, institucion)
        p_act = _precio_mes_especifico(db, anio_resuelto, mes_resuelto, institucion)
        variacion = None
        if p_ant is not None and p_act is not None and p_ant != 0:
            variacion = (p_act - p_ant) / p_ant * 100
        elif p_ant is not None and p_act is None:
            # "Sin dato del año actual" -- el propio spec pide -100% acá
            # (confirmado contra el control real: Agosto 2026 sin datos,
            # variación -100%, no "—").
            variacion = -100.0
        filas_precio.append(
            FilaPrecioKilolitro(
                etiqueta=etiqueta, precio_anio_anterior=p_ant, precio_anio_actual=p_act, variacion_pct=variacion
            )
        )

    return KilolitrosResponse(
        anio=anio_resuelto,
        mes=mes_resuelto,
        anio_anterior=anio_resuelto - 1,
        periodos_disponibles=periodos,
        tarjetas=tarjetas,
        filas_precio=filas_precio,
    )


# --- 4. Ingresos por contribución 4.5 por millar --------------------------


def _realizado_millar_mes(db: Session, anio: int, mes: int) -> float:
    valor = db.execute(
        text(
            "SELECT SUM(Creditos) - SUM(Debitos) FROM dbo.BalanceSaldos "
            "WHERE Sal_Ano = :anio AND Sal_Mes = :mes AND Cta_Codigo = :cta"
        ),
        {"anio": anio, "mes": mes, "cta": _CTA_MILLAR},
    ).scalar()
    return _num(valor)


def _realizado_millar_acumulado(db: Session, anio: int, mes: int) -> float:
    valor = db.execute(
        text(
            "SELECT SUM(Creditos) - SUM(Debitos) FROM dbo.BalanceSaldos "
            "WHERE Sal_Ano = :anio AND Sal_Mes <= :mes AND Cta_Codigo = :cta"
        ),
        {"anio": anio, "mes": mes, "cta": _CTA_MILLAR},
    ).scalar()
    return _num(valor)


def _presupuesto_millar_mes(db: Session, anio: int, mes: int) -> float:
    valor = db.execute(
        text(
            "SELECT SUM(pre_presupuesto) FROM dbo.Presupuestos "
            "WHERE par_ano = :anio AND par_mes = :mes AND cta_codigo = :cta"
        ),
        {"anio": anio, "mes": mes, "cta": _CTA_MILLAR},
    ).scalar()
    return _num(valor)


def _presupuesto_millar_acumulado(db: Session, anio: int, mes: int) -> float:
    valor = db.execute(
        text(
            "SELECT SUM(pre_presupuesto) FROM dbo.Presupuestos "
            "WHERE par_ano = :anio AND par_mes <= :mes AND cta_codigo = :cta"
        ),
        {"anio": anio, "mes": mes, "cta": _CTA_MILLAR},
    ).scalar()
    return _num(valor)


def _porcentaje_ejecucion(realizado: float, presupuesto: float) -> float | None:
    if not presupuesto:
        return None
    return realizado / presupuesto * 100


def obtener_contribucion_millar(db: Session, anio: int | None, mes: int | None) -> ContribucionMillarResponse:
    periodos = _periodos_disponibles_gastos(db)
    if anio is None or mes is None:
        ultimo = periodos[-1] if periodos else None
        anio_resuelto = anio if anio is not None else (ultimo.anio if ultimo else 0)
        mes_resuelto = mes if mes is not None else (ultimo.mes if ultimo else 0)
    else:
        anio_resuelto, mes_resuelto = anio, mes

    grafico = []
    for m in range(1, mes_resuelto + 1):
        grafico.append(
            PuntoContribucionMes(
                mes=MESES_LARGOS[m - 1],
                anio_anterior=_realizado_millar_mes(db, anio_resuelto - 1, m),
                presupuesto=_presupuesto_millar_mes(db, anio_resuelto, m),
                anio_actual=_realizado_millar_mes(db, anio_resuelto, m),
            )
        )

    realizado_mes = _realizado_millar_mes(db, anio_resuelto, mes_resuelto)
    presupuesto_mes = _presupuesto_millar_mes(db, anio_resuelto, mes_resuelto)
    realizado_acum = _realizado_millar_acumulado(db, anio_resuelto, mes_resuelto)
    presupuesto_acum = _presupuesto_millar_acumulado(db, anio_resuelto, mes_resuelto)

    return ContribucionMillarResponse(
        anio=anio_resuelto,
        mes=mes_resuelto,
        periodos_disponibles=periodos,
        grafico=grafico,
        tarjeta_mes=TarjetaResumenContribucion(
            presupuesto=presupuesto_mes,
            realizado=realizado_mes,
            porcentaje_ejecucion=_porcentaje_ejecucion(realizado_mes, presupuesto_mes),
        ),
        tarjeta_acumulada=TarjetaResumenContribucion(
            presupuesto=presupuesto_acum,
            realizado=realizado_acum,
            porcentaje_ejecucion=_porcentaje_ejecucion(realizado_acum, presupuesto_acum),
        ),
    )

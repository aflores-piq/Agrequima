"""Generación de archivos .xlsx para los botones de exportación del
dashboard. Cada elemento exportable reutiliza la misma función df_* que
ya usa el endpoint JSON del dashboard (ver dashboard_plaguicidas.py /
dashboard_nutrientes.py) — mismos datos en pantalla y en el Excel."""

import io

import pandas as pd

from app.services import dashboard_nutrientes as dn
from app.services import dashboard_plaguicidas as dp

MEDIA_TYPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Cada entrada: título mostrado (y usado como nombre de hoja en
# /export-todo), la función df_* que trae los datos, y los encabezados
# en español que reemplazan los nombres de columna internos al exportar.
PLAGUICIDAS_ELEMENTOS: dict[str, dict] = {
    "acumulado-mensual": {
        "titulo": "Comparativo acumulado",
        "df": dp.df_acumulado_mensual,
        "encabezados": lambda ctx: {
            "mes": "Mes",
            "cif_usd_actual_acumulado": f"CIF USD {ctx.anio_actual} (acumulado)",
            "cif_usd_anterior_acumulado": f"CIF USD {ctx.anio_anterior} (acumulado)",
        },
    },
    "comparativo-mensual": {
        "titulo": "Comparación mensual",
        "df": dp.df_comparativo_mensual,
        "encabezados": lambda ctx: {
            "mes": "Mes",
            "cif_usd_actual": f"CIF USD {ctx.anio_actual}",
            "cif_usd_anterior": f"CIF USD {ctx.anio_anterior}",
        },
    },
    "acumulado-multianual": {
        "titulo": "Comparativo acumulado por año",
        "df": dp.df_acumulado_multianual_ancho,
        "encabezados": lambda ctx: {"mes": "Mes"},
    },
    "por-aplicacion": {
        "titulo": "Distribución por aplicación",
        "df": dp.df_por_aplicacion,
        "encabezados": lambda ctx: {"etiqueta": "Tipo de aplicación", "cif_usd": "CIF USD"},
    },
    "top-moleculas": {
        "titulo": "Top ingredientes activos",
        "df": dp.df_top_moleculas,
        "encabezados": lambda ctx: {"etiqueta": "Ingrediente activo", "cif_usd": "CIF USD"},
    },
    "top-importadores": {
        "titulo": "Top importadores",
        "df": dp.df_top_importadores,
        "encabezados": lambda ctx: {"etiqueta": "Importador", "cif_usd": "CIF USD"},
    },
    "top-paises": {
        "titulo": "Top países de origen",
        "df": dp.df_top_paises,
        "encabezados": lambda ctx: {
            "etiqueta": "País",
            "transacciones": "Transacciones",
            "cif_usd": "CIF USD",
            "porcentaje_del_total": "% del total",
        },
    },
    "nombres-comerciales": {
        "titulo": "Nombres comerciales",
        "df": dp.df_nombres_comerciales,
        "encabezados": lambda ctx: {
            "producto": "Producto",
            "grupo": "Grupo",
            "aplicacion": "Aplicación",
            "importador": "Importador",
            "origen": "Origen",
            "cantidad": "Cantidad",
            "unidad_medida": "Unidad",
            "cif_usd": "CIF USD",
            "cif_q": "CIF Q",
            "categoria_aplicacion": "Categoría de aplicación",
        },
    },
    "grupo": {
        "titulo": "Grupo",
        "df": dp.df_grupo,
        "encabezados": lambda ctx: {
            "grupo": "Grupo",
            "porcentaje_del_total": "% del total",
            "aplicacion_principal": "Aplicación principal",
            "cantidad": "Cantidad",
            "unidad_medida": "Unidad",
            "cif_usd": "CIF USD",
            "cif_q": "CIF Q",
            "categoria_aplicacion": "Categoría de aplicación",
        },
    },
    "detalle": {
        "titulo": "Detalle de transacciones",
        "df": dp.df_detalle,
        "encabezados": lambda ctx: {
            "anio": "Año",
            "fecha": "Fecha",
            "recibointerno": "Recibo interno",
            "serie_sat": "Serie SAT",
            "numero_recibo_sat": "Número recibo SAT",
            "aplicacion": "Aplicación",
            "importador": "Empresa importadora",
            "producto": "Nombre comercial",
            "ingrediente_act": "Ingrediente activo",
            "cantidad": "Cantidad",
            "unidad_medida": "Unidad",
            "cif_usd": "CIF USD",
            "cif_q": "CIF Q",
            "porcentaje": "Porcentaje",
            "exportador": "Exportador",
            "origen": "Origen",
            "tipo_cambio": "Tipo de cambio",
            "institucion": "Institución",
            "umsp": "UMSP",
            "grupo": "Grupo",
            "codigo_agrupador": "Código agrupador",
        },
    },
}

NUTRIENTES_ELEMENTOS: dict[str, dict] = {
    "acumulado-mensual": {
        "titulo": "Comparativo acumulado",
        "df": dn.df_acumulado_mensual,
        "encabezados": lambda ctx: {
            "mes": "Mes",
            "cif_usd_actual_acumulado": f"CIF USD {ctx.anio_actual} (acumulado)",
            "cif_usd_anterior_acumulado": f"CIF USD {ctx.anio_anterior} (acumulado)",
        },
    },
    "comparativo-mensual": {
        "titulo": "Comparación mensual",
        "df": dn.df_comparativo_mensual,
        "encabezados": lambda ctx: {
            "mes": "Mes",
            "cif_usd_actual": f"CIF USD {ctx.anio_actual}",
            "cif_usd_anterior": f"CIF USD {ctx.anio_anterior}",
        },
    },
    "acumulado-multianual": {
        "titulo": "Comparativo acumulado por año",
        "df": dn.df_acumulado_multianual_ancho,
        "encabezados": lambda ctx: {"mes": "Mes"},
    },
    "top-formulas": {
        "titulo": "Top fórmulas químicas",
        "df": dn.df_top_formulas,
        "encabezados": lambda ctx: {"etiqueta": "Fórmula", "cif_usd": "CIF USD"},
    },
    "top-aduanas": {
        "titulo": "Top aduanas de ingreso",
        "df": dn.df_top_aduanas,
        "encabezados": lambda ctx: {"etiqueta": "Aduana", "cif_usd": "CIF USD"},
    },
    "formulas-componentes": {
        "titulo": "Fórmulas y componentes",
        "df": dn.df_formulas_componentes,
        "encabezados": lambda ctx: {
            "componente": "Fórmula/Componente",
            "porcentaje_del_total": "% del total",
            "concentracion_principal": "Concentración principal",
            "cantidad": "Cantidad",
            "unidad": "Unidad",
            "cif_usd": "CIF USD",
            "cif_q": "CIF Q",
        },
    },
    "detalle": {
        "titulo": "Detalle de licencias",
        "df": dn.df_detalle,
        "encabezados": lambda ctx: {
            "aduana": "Aduana",
            "no_licencia": "No. licencia",
            "no_registro": "No. registro",
            "nombre_comercial": "Nombre comercial",
            "empresa_importadora": "Empresa importadora",
            "fecha_emision": "Fecha de emisión",
            "unidad": "Unidad",
        },
    },
}


def _nombre_hoja_unico(titulo: str, usados: set[str]) -> str:
    # Excel limita el nombre de hoja a 31 caracteres y no permite duplicados.
    base = titulo[:31]
    nombre = base
    sufijo = 2
    while nombre in usados:
        nombre = f"{base[: 31 - len(f' {sufijo}')]} {sufijo}"
        sufijo += 1
    usados.add(nombre)
    return nombre


def _df_para_excel(ctx, registro: dict) -> pd.DataFrame:
    df: pd.DataFrame = registro["df"](ctx)
    return df.rename(columns=registro["encabezados"](ctx))


def generar_excel_elemento(ctx, registro: dict) -> bytes:
    df = _df_para_excel(ctx, registro)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=registro["titulo"][:31])
    return buffer.getvalue()


def generar_excel_todo(ctx, elementos: dict[str, dict]) -> bytes:
    buffer = io.BytesIO()
    usados: set[str] = set()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for registro in elementos.values():
            df = _df_para_excel(ctx, registro)
            nombre_hoja = _nombre_hoja_unico(registro["titulo"], usados)
            df.to_excel(writer, index=False, sheet_name=nombre_hoja)
    return buffer.getvalue()

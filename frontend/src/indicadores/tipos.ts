/** Tipos de las respuestas de /api/dashboard/indicadores/resumen-general/* (ver backend/app/routers/dashboard_indicadores.py). */

export interface MesDisponible {
  anio: number;
  mes: number;
  etiqueta: string;
  filas: number;
}

export interface MesesRespuesta {
  meses: MesDisponible[];
  por_defecto: { anio: number; mes: number } | null;
}

export interface PuntoMes {
  anio: number;
  mes: number;
  valor: number;
}

export interface Tarjeta {
  clave: "total_viaticos" | "tecnicos_conductores" | "total_documentos" | "total_proveedores";
  etiqueta: string;
  formato: "moneda" | "entero";
  valor: number;
  valor_anio_anterior: number | null;
  variacion_pct: number | null;
  ultimos_12_meses: PuntoMes[];
}

export interface TarjetasRespuesta {
  anio: number;
  mes: number;
  etiqueta_mes: string;
  titulo: string;
  /** true si el mes elegido está incompleto: el % se compara contra el mismo período del año anterior. */
  periodo_parcial: boolean;
  dia_corte: number | null;
  texto_comparacion: string;
  tarjetas: Tarjeta[];
}

export interface PuntoAcumulado {
  mes: number;
  etiqueta: string;
  acumulado: number | null;
}

export interface AcumuladoRespuesta {
  anio: number;
  anio_anterior: number;
  mes: number;
  serie_actual: PuntoAcumulado[];
  serie_anterior: PuntoAcumulado[];
}

export interface DatoAgrupado {
  nombre: string;
  total_gastos: number;
}

export interface AgrupadoRespuesta {
  anio: number;
  mes: number;
  total: number;
  datos: DatoAgrupado[];
}

export interface FilaDetalle {
  fecha_documento: string | null;
  fecha_inicial: string | null;
  fecha_final: string | null;
  tecnico: string | null;
  tipo_gasto: string | null;
  motivo: string | null;
  total_factura: number;
  proveedor: string | null;
}

export interface DetalleRespuesta {
  anio: number;
  mes: number;
  total_factura: number;
  filas: FilaDetalle[];
}

export interface Periodo {
  anio: number;
  mes: number;
}

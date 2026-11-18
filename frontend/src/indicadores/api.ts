import { apiClient } from "../api/client";
import type {
  AcumuladoRespuesta,
  AgrupadoRespuesta,
  DetalleRespuesta,
  MesesRespuesta,
  Periodo,
  TarjetasRespuesta,
} from "./tipos";

const BASE = "/dashboard/indicadores/resumen-general";

export async function obtenerMeses(): Promise<MesesRespuesta> {
  return (await apiClient.get<MesesRespuesta>(`${BASE}/meses`)).data;
}

async function pedir<T>(ruta: string, p: Periodo): Promise<T> {
  return (await apiClient.get<T>(`${BASE}/${ruta}`, { params: { anio: p.anio, mes: p.mes } })).data;
}

export const obtenerTarjetas = (p: Periodo) => pedir<TarjetasRespuesta>("tarjetas", p);
export const obtenerAcumulado = (p: Periodo) => pedir<AcumuladoRespuesta>("acumulado", p);
export const obtenerTiposGasto = (p: Periodo) => pedir<AgrupadoRespuesta>("tipos-gasto", p);
export const obtenerColaboradores = (p: Periodo) => pedir<AgrupadoRespuesta>("colaboradores", p);
export const obtenerDetalle = (p: Periodo) => pedir<DetalleRespuesta>("detalle", p);

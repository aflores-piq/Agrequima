export interface Aviso {
  aviso_id: number;
  tipo: string;
  mensaje: string;
  referencia: string | null;
  fecha_creacion: string;
  destino: string;
  leido: boolean;
}

export interface ListaAvisos {
  no_leidos: number;
  avisos: Aviso[];
}

export interface ResultadoLeer {
  marcados: number;
  no_leidos: number;
}

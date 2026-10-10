export interface FilaBitacoraIngreso {
  usuario: string;
  nombre: string | null;
  empresa: string | null;
  fecha_hora: string;
}

export interface BitacoraIngresosResponse {
  total: number;
  filas: FilaBitacoraIngreso[];
  empresas: string[];
  usuarios: string[];
}

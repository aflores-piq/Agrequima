import { useEffect, useState } from "react";
import { Card, Select, SelectItem, Text, Title } from "@tremor/react";
import { obtenerBitacoraIngresos } from "../../api/bitacora";
import { mensajeError } from "../../api/client";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import type { BitacoraIngresosResponse, FilaBitacoraIngreso } from "../../types/bitacora";
import { formatFechaHoraGuatemala, formatNumber } from "../../utils/format";

// Valor de la opción "Todos" de las listas (Tremor no admite un valor vacío en SelectItem).
const TODOS = "__todos__";

export function BitacoraIngresosPage() {
  const [empresa, setEmpresa] = useState(TODOS);
  const [usuario, setUsuario] = useState(TODOS);
  const [data, setData] = useState<BitacoraIngresosResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Las opciones de las listas salen de la bitácora completa (no cambian al filtrar).
  const [empresas, setEmpresas] = useState<string[]>([]);
  const [usuarios, setUsuarios] = useState<string[]>([]);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    obtenerBitacoraIngresos(empresa === TODOS ? undefined : empresa, usuario === TODOS ? undefined : usuario)
      .then((res) => {
        if (cancelado) return;
        setData(res);
        setEmpresas(res.empresas);
        setUsuarios(res.usuarios);
        setError(null);
      })
      .catch((err) => {
        if (!cancelado) setError(mensajeError(err));
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [empresa, usuario]);

  return (
    <div className="space-y-6">
      <div>
        <Title className="text-ink">Bitácora de ingresos</Title>
        {data && <Text className="text-ink-muted">Total de ingresos: {formatNumber(data.total)}</Text>}
      </div>

      <Card className="bg-surface ring-1 ring-line">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div>
            <Text className="mb-1 text-xs text-ink-muted">Empresa</Text>
            <Select value={empresa} onValueChange={setEmpresa} className="w-56">
              <SelectItem value={TODOS}>Todos</SelectItem>
              {empresas.map((e) => (
                <SelectItem key={e} value={e}>
                  {e}
                </SelectItem>
              ))}
            </Select>
          </div>
          <div>
            <Text className="mb-1 text-xs text-ink-muted">Usuario</Text>
            <Select value={usuario} onValueChange={setUsuario} className="w-56">
              <SelectItem value={TODOS}>Todos</SelectItem>
              {usuarios.map((u) => (
                <SelectItem key={u} value={u}>
                  {u}
                </SelectItem>
              ))}
            </Select>
          </div>
        </div>

        {error && <p className="text-sm text-danger">{error}</p>}
        {cargando && !data ? (
          <p className="text-sm text-ink-muted">Cargando…</p>
        ) : (
          <div className="max-h-[65vh] overflow-y-auto">
            <SimpleDataTable
              sinLimiteAltura
              columnas={[
                { header: "Usuario", accessor: (r: FilaBitacoraIngreso) => r.usuario },
                { header: "Nombre", accessor: (r: FilaBitacoraIngreso) => r.nombre ?? "—" },
                { header: "Empresa", accessor: (r: FilaBitacoraIngreso) => r.empresa ?? "—" },
                { header: "Fecha y hora", accessor: (r: FilaBitacoraIngreso) => formatFechaHoraGuatemala(r.fecha_hora) },
              ]}
              filas={data?.filas ?? []}
              getKey={(_r, i) => i}
            />
          </div>
        )}
      </Card>
    </div>
  );
}

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Badge, Button, Card, Title, Text } from "@tremor/react";
import { cargarSaldosBancarios, obtenerHistorialCargas } from "../../api/cargas";
import { mensajeError } from "../../api/client";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import { formatNumber } from "../../utils/format";
import type { AuditoriaCargaItem, ResumenCargaFinanciero } from "../../types/cargas";

const ESTADO_COLOR: Record<string, "emerald" | "amber" | "red"> = {
  OK: "emerald",
  ConExcepciones: "amber",
  Error: "red",
};

export function CargaSaldoBancarioPage() {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [resumen, setResumen] = useState<ResumenCargaFinanciero | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historial, setHistorial] = useState<AuditoriaCargaItem[]>([]);

  function cargarHistorial() {
    obtenerHistorialCargas("SaldosBancarios", 1, 10).then((res) => setHistorial(res.filas));
  }

  useEffect(cargarHistorial, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!archivo) return;
    setEnviando(true);
    setError(null);
    setResumen(null);
    try {
      const res = await cargarSaldosBancarios(archivo);
      setResumen(res);
      cargarHistorial();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Title className="text-ink">Carga de Saldos Bancarios</Title>
        <Text className="text-ink-muted">
          Sube el archivo de Saldos Bancarios del mes (.xlsx). Columnas esperadas: Concepto, Año,
          Mes, Banco, Valor. Volver a subir el mismo período (año/mes) reemplaza lo ya cargado, no
          lo duplica.
        </Text>
      </div>

      <Card className="bg-surface ring-1 ring-line">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-ink-muted">
              Archivo de Saldos Bancarios (.xlsx) <span className="text-danger">*</span>
            </label>
            <input
              type="file"
              accept=".xlsx,.xls"
              required
              onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-ink-muted file:mr-3 file:rounded-tremor-small file:border-0 file:bg-teal-600 file:px-3 file:py-1.5 file:text-white hover:file:bg-teal-500"
            />
          </div>

          {error && (
            <p role="alert" className="rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}

          <Button type="submit" loading={enviando} disabled={enviando || !archivo}>
            Procesar carga
          </Button>
        </form>
      </Card>

      {resumen && (
        <Card className="bg-surface ring-1 ring-line">
          <div className="mb-3 flex items-center gap-2">
            <Title className="text-ink">Resultado</Title>
            <Badge color={ESTADO_COLOR[resumen.estado] ?? "slate"}>{resumen.estado}</Badge>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-ink-faint">Filas cargadas</dt>
              <dd className="text-ink">{formatNumber(resumen.filas_cargadas)}</dd>
            </div>
            <div>
              <dt className="text-ink-faint">Períodos cubiertos</dt>
              <dd className="text-ink">
                {resumen.periodos.map((p) => `${p.mes}/${p.anio}`).join(", ") || "—"}
              </dd>
            </div>
          </dl>
        </Card>
      )}

      <Card className="bg-surface ring-1 ring-line">
        <Title className="mb-3 text-ink">Historial de cargas</Title>
        <SimpleDataTable
          columnas={[
            { header: "Fecha", accessor: (r: AuditoriaCargaItem) => new Date(r.fecha_carga).toLocaleString("es-GT") },
            { header: "Archivo", accessor: (r: AuditoriaCargaItem) => r.nombre_archivo ?? "—" },
            { header: "Usuario", accessor: (r: AuditoriaCargaItem) => r.usuario ?? "—" },
            { header: "Filas", accessor: (r: AuditoriaCargaItem) => r.filas_procesadas ?? "—", align: "right" },
            {
              header: "Estado",
              accessor: (r: AuditoriaCargaItem) => (
                <Badge color={ESTADO_COLOR[r.estado] ?? "slate"}>{r.estado}</Badge>
              ),
            },
          ]}
          filas={historial}
          getKey={(r) => r.carga_id}
        />
      </Card>
    </div>
  );
}

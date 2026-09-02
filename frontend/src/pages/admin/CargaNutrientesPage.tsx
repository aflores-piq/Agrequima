import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Badge, Button, Card, Title, Text } from "@tremor/react";
import { cargarNutrientes, obtenerHistorialCargas } from "../../api/cargas";
import { mensajeError } from "../../api/client";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import { formatNumber } from "../../utils/format";
import type { AuditoriaCargaItem, ResumenCargaNutrientes } from "../../types/cargas";

const ESTADO_COLOR: Record<string, "emerald" | "amber" | "red"> = {
  OK: "emerald",
  ConExcepciones: "amber",
  Error: "red",
};

export function CargaNutrientesPage() {
  const [archivoNutrientes, setArchivoNutrientes] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [resumen, setResumen] = useState<ResumenCargaNutrientes | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historial, setHistorial] = useState<AuditoriaCargaItem[]>([]);

  function cargarHistorial() {
    obtenerHistorialCargas("Nutrientes", 1, 10).then((res) => setHistorial(res.filas));
  }

  useEffect(cargarHistorial, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!archivoNutrientes) return;
    setEnviando(true);
    setError(null);
    setResumen(null);
    try {
      const res = await cargarNutrientes(archivoNutrientes);
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
        <Title className="text-ink">Carga de nutrientes</Title>
        <Text className="text-ink-muted">
          Sube el archivo consolidado de licencias de importación (.csv o .xlsx). Los ajustes de
          agrupador se hacen desde la pantalla de Nomenclatura.
        </Text>
      </div>

      <Card className="bg-surface ring-1 ring-line">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-ink-muted">
              Licencias de nutrientes (.csv o .xlsx) <span className="text-danger">*</span>
            </label>
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              required
              onChange={(e) => setArchivoNutrientes(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-ink-muted file:mr-3 file:rounded-tremor-small file:border-0 file:bg-orange-600 file:px-3 file:py-1.5 file:text-white hover:file:bg-orange-500"
            />
          </div>

          {error && (
            <p role="alert" className="rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}

          <Button type="submit" loading={enviando} disabled={enviando || !archivoNutrientes}>
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
              <dt className="text-ink-faint">Años</dt>
              <dd className="text-ink">{resumen.anios.join(", ") || "—"}</dd>
            </div>
            <div>
              <dt className="text-ink-faint">Filas truncadas</dt>
              <dd className="text-ink">{formatNumber(resumen.filas_truncadas)}</dd>
            </div>
            <div>
              <dt className="text-ink-faint">Sin agrupador encontrado</dt>
              <dd className="text-ink">{formatNumber(resumen.filas_sin_agrupador)}</dd>
            </div>
          </dl>
          {resumen.filas_sin_agrupador > 0 && (
            <Text className="mt-3 text-amber-400">
              Hay licencias sin agrupador — revísalas en la pantalla de Nomenclatura.
            </Text>
          )}
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
            { header: "Excepciones", accessor: (r: AuditoriaCargaItem) => r.filas_con_excepcion ?? "—", align: "right" },
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

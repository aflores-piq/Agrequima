import { useEffect, useState } from "react";
import { Button, Card, TextInput, Title, Text } from "@tremor/react";
import {
  actualizarNomenclaturaPlaguicida,
  listarNomenclaturaPlaguicidas,
} from "../../api/nomenclatura";
import { mensajeError } from "../../api/client";
import { PaginatedTable } from "../../components/PaginatedTable";
import type { NomenclaturaPlaguicidaItem } from "../../types/nomenclatura";

const TAMANO_PAGINA = 20;

export function NomenclaturaPlaguicidasPage() {
  const [busquedaInput, setBusquedaInput] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [filas, setFilas] = useState<NomenclaturaPlaguicidaItem[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [edicion, setEdicion] = useState<{ key: string; agrupador: string; codigo: string } | null>(null);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    setCargando(true);
    listarNomenclaturaPlaguicidas(busqueda, pagina, TAMANO_PAGINA)
      .then((res) => {
        setFilas(res.filas);
        setTotal(res.total);
        setError(null);
      })
      .catch((err) => setError(mensajeError(err)))
      .finally(() => setCargando(false));
  }

  useEffect(cargar, [busqueda, pagina]);

  function abrirEdicion(fila: NomenclaturaPlaguicidaItem) {
    setEdicion({ key: fila.ingrediente_key, agrupador: fila.agrupador ?? "", codigo: fila.codigo ?? "" });
  }

  async function guardarEdicion() {
    if (!edicion) return;
    setGuardando(true);
    try {
      await actualizarNomenclaturaPlaguicida(edicion.key, edicion.agrupador, edicion.codigo || null);
      setEdicion(null);
      cargar();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Title className="text-ink">Nomenclatura de plaguicidas</Title>
        <Text className="text-ink-muted">
          Catálogo permanente de ingredientes activos y su agrupador estandarizado.
        </Text>
      </div>

      <div className="flex items-end gap-3">
        <div>
          <Text className="mb-1 text-xs text-ink-muted">Buscar</Text>
          <TextInput
            value={busquedaInput}
            onValueChange={setBusquedaInput}
            placeholder="Ingrediente o agrupador"
            className="w-72"
          />
        </div>
        <Button
          onClick={() => {
            setPagina(1);
            setBusqueda(busquedaInput);
          }}
        >
          Buscar
        </Button>
      </div>

      {error && <p className="rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">{error}</p>}

      {edicion && (
        <Card className="bg-surface ring-1 ring-teal-500/40">
          <Text className="mb-2 text-ink-muted">
            Editando: <span className="text-ink">{edicion.key}</span>
          </Text>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Text className="mb-1 text-xs text-ink-muted">Agrupador</Text>
              <TextInput
                value={edicion.agrupador}
                onValueChange={(v) => setEdicion({ ...edicion, agrupador: v })}
                className="w-64"
              />
            </div>
            <div>
              <Text className="mb-1 text-xs text-ink-muted">Código</Text>
              <TextInput
                value={edicion.codigo}
                onValueChange={(v) => setEdicion({ ...edicion, codigo: v })}
                className="w-32"
              />
            </div>
            <Button onClick={guardarEdicion} loading={guardando} disabled={!edicion.agrupador || guardando}>
              Guardar
            </Button>
            <Button variant="secondary" onClick={() => setEdicion(null)}>
              Cancelar
            </Button>
          </div>
        </Card>
      )}

      <Card className="bg-surface ring-1 ring-line">
        {cargando ? (
          <p className="text-sm text-ink-muted">Cargando…</p>
        ) : (
          <PaginatedTable
            columnas={[
              { header: "Ingrediente activo", accessor: (r: NomenclaturaPlaguicidaItem) => r.ingrediente_key },
              { header: "Agrupador", accessor: (r: NomenclaturaPlaguicidaItem) => r.agrupador ?? "—" },
              { header: "Código", accessor: (r: NomenclaturaPlaguicidaItem) => r.codigo ?? "—" },
              {
                header: "",
                accessor: (r: NomenclaturaPlaguicidaItem) => (
                  <button
                    type="button"
                    onClick={() => abrirEdicion(r)}
                    className="text-xs font-medium text-teal-400 hover:text-teal-300"
                  >
                    Editar
                  </button>
                ),
              },
            ]}
            filas={filas}
            total={total}
            pagina={pagina}
            tamanoPagina={TAMANO_PAGINA}
            onCambiarPagina={setPagina}
            getKey={(r) => r.ingrediente_key}
          />
        )}
      </Card>
    </div>
  );
}

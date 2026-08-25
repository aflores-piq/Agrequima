import { useEffect, useState } from "react";
import { Button, Card, TextInput, Title, Text } from "@tremor/react";
import { actualizarAgrupadorNutriente, listarAgrupadorNutrientes } from "../../api/nomenclatura";
import { mensajeError } from "../../api/client";
import { PaginatedTable } from "../../components/PaginatedTable";
import type { AgrupadorNutrienteItem } from "../../types/nomenclatura";

const TAMANO_PAGINA = 20;

export function AgrupadorNutrientesPage() {
  const [busquedaInput, setBusquedaInput] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [filas, setFilas] = useState<AgrupadorNutrienteItem[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [edicion, setEdicion] = useState<{ key: string; producto: string; codigo: string } | null>(null);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    setCargando(true);
    listarAgrupadorNutrientes(busqueda, pagina, TAMANO_PAGINA)
      .then((res) => {
        setFilas(res.filas);
        setTotal(res.total);
        setError(null);
      })
      .catch((err) => setError(mensajeError(err)))
      .finally(() => setCargando(false));
  }

  useEffect(cargar, [busqueda, pagina]);

  function abrirEdicion(fila: AgrupadorNutrienteItem) {
    setEdicion({ key: fila.nombre_key, producto: fila.producto_agrupado ?? "", codigo: fila.codigo ?? "" });
  }

  async function guardarEdicion() {
    if (!edicion) return;
    setGuardando(true);
    try {
      await actualizarAgrupadorNutriente(edicion.key, edicion.producto, edicion.codigo || null);
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
        <Title className="text-ink">Agrupador de nutrientes</Title>
        <Text className="text-ink-muted">
          Catálogo permanente de nombres comerciales y su producto agrupado (fórmula).
        </Text>
      </div>

      <div className="flex items-end gap-3">
        <div>
          <Text className="mb-1 text-xs text-ink-muted">Buscar</Text>
          <TextInput
            value={busquedaInput}
            onValueChange={setBusquedaInput}
            placeholder="Nombre comercial o producto agrupado"
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
        <Card className="bg-surface ring-1 ring-orange-500/40">
          <Text className="mb-2 text-ink-muted">
            Editando: <span className="text-ink">{edicion.key}</span>
          </Text>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Text className="mb-1 text-xs text-ink-muted">Producto agrupado</Text>
              <TextInput
                value={edicion.producto}
                onValueChange={(v) => setEdicion({ ...edicion, producto: v })}
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
            <Button onClick={guardarEdicion} loading={guardando} disabled={!edicion.producto || guardando}>
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
              { header: "Nombre comercial", accessor: (r: AgrupadorNutrienteItem) => r.nombre_key },
              { header: "Producto agrupado", accessor: (r: AgrupadorNutrienteItem) => r.producto_agrupado ?? "—" },
              { header: "Código", accessor: (r: AgrupadorNutrienteItem) => r.codigo ?? "—" },
              {
                header: "",
                accessor: (r: AgrupadorNutrienteItem) => (
                  <button
                    type="button"
                    onClick={() => abrirEdicion(r)}
                    className="text-xs font-medium text-orange-400 hover:text-orange-300"
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
            getKey={(r) => r.nombre_key}
          />
        )}
      </Card>
    </div>
  );
}

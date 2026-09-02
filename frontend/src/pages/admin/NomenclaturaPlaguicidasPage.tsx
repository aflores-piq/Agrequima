import { useEffect, useState } from "react";
import { Badge, Button, Card, TextInput, Title, Text } from "@tremor/react";
import {
  actualizarNomenclaturaPlaguicida,
  listarNomenclaturaPlaguicidas,
  obtenerSinAgrupadorPlaguicidas,
} from "../../api/nomenclatura";
import { mensajeError } from "../../api/client";
import { PaginatedTable } from "../../components/PaginatedTable";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import { formatNumber, formatUSD } from "../../utils/format";
import type {
  NomenclaturaPlaguicidaItem,
  SinAgrupadorPlaguicidasResponse,
} from "../../types/nomenclatura";

const TAMANO_PAGINA = 20;

interface Edicion {
  key: string;
  agrupador: string;
  codigo: string;
}

export function NomenclaturaPlaguicidasPage() {
  const [busquedaInput, setBusquedaInput] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [filas, setFilas] = useState<NomenclaturaPlaguicidaItem[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [paginaSinAgrupador, setPaginaSinAgrupador] = useState(1);
  const [datosSinAgrupador, setDatosSinAgrupador] = useState<SinAgrupadorPlaguicidasResponse | null>(null);
  const [errorSinAgrupador, setErrorSinAgrupador] = useState<string | null>(null);

  const [edicion, setEdicion] = useState<Edicion | null>(null);
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

  function cargarSinAgrupador() {
    obtenerSinAgrupadorPlaguicidas(paginaSinAgrupador, TAMANO_PAGINA)
      .then((res) => {
        setDatosSinAgrupador(res);
        setErrorSinAgrupador(null);
      })
      .catch((err) => setErrorSinAgrupador(mensajeError(err)));
  }

  useEffect(cargar, [busqueda, pagina]);
  useEffect(cargarSinAgrupador, [paginaSinAgrupador]);

  function abrirEdicion(fila: NomenclaturaPlaguicidaItem) {
    setEdicion({ key: fila.ingrediente_key, agrupador: fila.agrupador ?? "", codigo: fila.codigo ?? "" });
  }

  function abrirEdicionSinAgrupador(ingredienteKey: string) {
    setEdicion({ key: ingredienteKey, agrupador: "", codigo: "" });
  }

  async function guardarEdicion() {
    if (!edicion) return;
    setGuardando(true);
    try {
      await actualizarNomenclaturaPlaguicida(edicion.key, edicion.agrupador, edicion.codigo || null);
      setEdicion(null);
      // Un mismo guardado puede afectar tanto la lista del catálogo
      // (sección de búsqueda) como la de "sin agrupador" — se recargan
      // ambas siempre, sin importar desde cuál se abrió la edición.
      cargar();
      cargarSinAgrupador();
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

      {edicion && (
        <Card className="bg-surface ring-1 ring-teal-500/40">
          <Text className="mb-2 text-ink-muted">
            Editando: <span className="text-ink">{edicion.key}</span>
          </Text>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Text className="mb-1 text-xs text-ink-muted">Grupo</Text>
              <TextInput
                value={edicion.agrupador}
                onValueChange={(v) => setEdicion({ ...edicion, agrupador: v })}
                className="w-64"
              />
            </div>
            <div>
              <Text className="mb-1 text-xs text-ink-muted">Código (opcional)</Text>
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

      <div>
        <Title className="mb-3 text-ink">Buscar y editar catálogo</Title>

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

        {error && <p className="mt-3 rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">{error}</p>}

        <Card className="mt-3 bg-surface ring-1 ring-line">
          {cargando ? (
            <p className="text-sm text-ink-muted">Cargando…</p>
          ) : (
            <PaginatedTable
              columnas={[
                { header: "Ingrediente activo", accessor: (r: NomenclaturaPlaguicidaItem) => r.ingrediente_key },
                { header: "Grupo", accessor: (r: NomenclaturaPlaguicidaItem) => r.agrupador ?? "—" },
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

      <div>
        <Title className="mb-1 text-ink">Sin agrupador</Title>
        <Text className="mb-3 text-ink-muted">
          Ingredientes activos que aparecen en transacciones cargadas pero todavía no tienen un
          grupo asignado en el catálogo — se actualiza al instante al editar desde aquí.
        </Text>

        {errorSinAgrupador && (
          <p className="mb-3 rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">
            {errorSinAgrupador}
          </p>
        )}

        {!datosSinAgrupador ? (
          <p className="text-sm text-ink-muted">Cargando…</p>
        ) : (
          <div className="space-y-4">
            <Card className="bg-surface ring-1 ring-line">
              <Title className="mb-3 text-ink">Resumen por ingrediente</Title>
              <SimpleDataTable
                columnas={[
                  { header: "Ingrediente activo", accessor: (r) => r.ingrediente_ejemplo ?? r.ingrediente_key },
                  { header: "Transacciones", accessor: (r) => formatNumber(r.transacciones), align: "right" },
                  { header: "CIF USD", accessor: (r) => formatUSD(r.cif_usd_total), align: "right" },
                  {
                    header: "¿Posible error de captura?",
                    accessor: (r) => (r.posible_error_captura ? <Badge color="amber">Revisar</Badge> : "—"),
                  },
                ]}
                filas={datosSinAgrupador.resumen}
                getKey={(r) => r.ingrediente_key}
              />
            </Card>
            <Card className="bg-surface ring-1 ring-line">
              <Title className="mb-3 text-ink">Detalle de transacciones sin agrupador</Title>
              <PaginatedTable
                columnas={[
                  { header: "Recibo", accessor: (r) => r.recibointerno ?? "—" },
                  { header: "Ingrediente activo", accessor: (r) => r.ingrediente_act ?? "—" },
                  { header: "Producto", accessor: (r) => r.producto ?? "—" },
                  {
                    header: "",
                    accessor: (r) =>
                      r.ingrediente_key ? (
                        <button
                          type="button"
                          onClick={() => abrirEdicionSinAgrupador(r.ingrediente_key as string)}
                          className="text-xs font-medium text-teal-400 hover:text-teal-300"
                        >
                          Editar
                        </button>
                      ) : (
                        <span className="text-xs text-ink-faint">—</span>
                      ),
                  },
                ]}
                filas={datosSinAgrupador.detalle.filas}
                total={datosSinAgrupador.detalle.total}
                pagina={datosSinAgrupador.detalle.pagina}
                tamanoPagina={datosSinAgrupador.detalle.tamano_pagina}
                onCambiarPagina={setPaginaSinAgrupador}
                getKey={(r, i) => `${r.recibointerno}-${i}`}
              />
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

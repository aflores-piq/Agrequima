import { useEffect, useState } from "react";
import { Badge, Button, Card, TextInput, Title, Text } from "@tremor/react";
import {
  actualizarAgrupadorNutriente,
  listarAgrupadorNutrientes,
  obtenerSinAgrupadorNutrientes,
} from "../../api/nomenclatura";
import { mensajeError } from "../../api/client";
import { PaginatedTable } from "../../components/PaginatedTable";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import { formatNumber, formatUSD } from "../../utils/format";
import type {
  AgrupadorNutrienteItem,
  SinAgrupadorNutrientesResponse,
} from "../../types/nomenclatura";

const TAMANO_PAGINA = 20;

interface Edicion {
  key: string;
  producto: string;
  codigo: string;
}

export function AgrupadorNutrientesPage() {
  const [busquedaInput, setBusquedaInput] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [filas, setFilas] = useState<AgrupadorNutrienteItem[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [paginaSinAgrupador, setPaginaSinAgrupador] = useState(1);
  const [datosSinAgrupador, setDatosSinAgrupador] = useState<SinAgrupadorNutrientesResponse | null>(null);
  const [errorSinAgrupador, setErrorSinAgrupador] = useState<string | null>(null);

  const [edicion, setEdicion] = useState<Edicion | null>(null);
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

  function cargarSinAgrupador() {
    obtenerSinAgrupadorNutrientes(paginaSinAgrupador, TAMANO_PAGINA)
      .then((res) => {
        setDatosSinAgrupador(res);
        setErrorSinAgrupador(null);
      })
      .catch((err) => setErrorSinAgrupador(mensajeError(err)));
  }

  useEffect(cargar, [busqueda, pagina]);
  useEffect(cargarSinAgrupador, [paginaSinAgrupador]);

  function abrirEdicion(fila: AgrupadorNutrienteItem) {
    setEdicion({ key: fila.nombre_key, producto: fila.producto_agrupado ?? "", codigo: fila.codigo ?? "" });
  }

  function abrirEdicionSinAgrupador(nombreKey: string) {
    setEdicion({ key: nombreKey, producto: "", codigo: "" });
  }

  async function guardarEdicion() {
    if (!edicion) return;
    setGuardando(true);
    try {
      await actualizarAgrupadorNutriente(edicion.key, edicion.producto, edicion.codigo || null);
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
        <Title className="text-ink">Agrupador de nutrientes</Title>
        <Text className="text-ink-muted">
          Catálogo permanente de nombres comerciales y su producto agrupado (fórmula).
        </Text>
      </div>

      {edicion && (
        <Card className="bg-surface ring-1 ring-orange-500/40">
          <Text className="mb-2 text-ink-muted">
            Editando: <span className="text-ink">{edicion.key}</span>
          </Text>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Text className="mb-1 text-xs text-ink-muted">Grupo (producto agrupado)</Text>
              <TextInput
                value={edicion.producto}
                onValueChange={(v) => setEdicion({ ...edicion, producto: v })}
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
            <Button onClick={guardarEdicion} loading={guardando} disabled={!edicion.producto || guardando}>
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

        {error && <p className="mt-3 rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">{error}</p>}

        <Card className="mt-3 bg-surface ring-1 ring-line">
          {cargando ? (
            <p className="text-sm text-ink-muted">Cargando…</p>
          ) : (
            <PaginatedTable
              columnas={[
                { header: "Nombre comercial", accessor: (r: AgrupadorNutrienteItem) => r.nombre_key },
                { header: "Grupo", accessor: (r: AgrupadorNutrienteItem) => r.producto_agrupado ?? "—" },
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

      <div>
        <Title className="mb-1 text-ink">Sin agrupador</Title>
        <Text className="mb-3 text-ink-muted">
          Nombres comerciales que aparecen en licencias cargadas pero todavía no tienen un grupo
          asignado en el catálogo — se actualiza al instante al editar desde aquí.
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
              <Title className="mb-3 text-ink">Resumen por nombre comercial</Title>
              <SimpleDataTable
                columnas={[
                  { header: "Nombre comercial", accessor: (r) => r.nombre_ejemplo ?? r.nombre_key },
                  { header: "Transacciones", accessor: (r) => formatNumber(r.transacciones), align: "right" },
                  { header: "CIF USD", accessor: (r) => formatUSD(r.cif_dolares_total), align: "right" },
                  {
                    header: "¿Posible error de captura?",
                    accessor: (r) => (r.posible_error_captura ? <Badge color="amber">Revisar</Badge> : "—"),
                  },
                ]}
                filas={datosSinAgrupador.resumen}
                getKey={(r) => r.nombre_key}
              />
            </Card>
            <Card className="bg-surface ring-1 ring-line">
              <Title className="mb-3 text-ink">Detalle de licencias sin agrupador</Title>
              <PaginatedTable
                columnas={[
                  { header: "No. licencia", accessor: (r) => r.no_licencia ?? "—" },
                  { header: "Nombre comercial", accessor: (r) => r.nombre_comercial ?? "—" },
                  {
                    header: "",
                    accessor: (r) =>
                      r.nombre_key ? (
                        <button
                          type="button"
                          onClick={() => abrirEdicionSinAgrupador(r.nombre_key as string)}
                          className="text-xs font-medium text-orange-400 hover:text-orange-300"
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
                getKey={(r, i) => `${r.no_licencia}-${i}`}
              />
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

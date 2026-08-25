import { useEffect, useState } from "react";
import { Badge, Card, Tab, TabGroup, TabList, TabPanel, TabPanels, Title, Text } from "@tremor/react";
import {
  actualizarAgrupadorNutrientes,
  actualizarAgrupadorPlaguicidas,
  obtenerExcepcionesNutrientes,
  obtenerExcepcionesPlaguicidas,
} from "../../api/excepciones";
import { mensajeError } from "../../api/client";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import { PaginatedTable } from "../../components/PaginatedTable";
import { formatNumber, formatUSD } from "../../utils/format";
import type { ExcepcionesPlaguicidasResponse } from "../../types/excepciones";
import type { ExcepcionesNutrientesResponse } from "../../types/excepciones";

/** Campo "Agrupador" editable por fila: al guardar, asigna esa clave al
 * catálogo y sincroniza de inmediato todas las filas que la comparten
 * (backend), por eso `onGuardado` recarga la lista completa — la fila
 * (y cualquier otra con la misma clave) desaparece de "sin agrupador". */
function AgrupadorCell({
  clave,
  onGuardar,
}: {
  clave: string | null;
  onGuardar: (agrupador: string) => Promise<void>;
}) {
  const [valor, setValor] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!clave) return <span className="text-xs text-ink-faint">—</span>;

  async function guardar() {
    if (!valor.trim() || guardando) return;
    setGuardando(true);
    setError(null);
    try {
      await onGuardar(valor.trim());
    } catch (err) {
      setError(mensajeError(err));
      setGuardando(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={valor}
        onChange={(e) => setValor(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") guardar();
        }}
        placeholder="Asignar agrupador…"
        disabled={guardando}
        className="w-44 rounded-[2px] border border-line-strong bg-app px-2 py-1 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:ring-1 focus:ring-teal-500 disabled:opacity-50"
      />
      <button
        type="button"
        onClick={guardar}
        disabled={guardando || !valor.trim()}
        className="text-xs font-medium text-teal-400 hover:text-teal-300 disabled:opacity-40"
      >
        {guardando ? "Guardando…" : "Guardar"}
      </button>
      {error && <span className="text-xs text-danger">{error}</span>}
    </div>
  );
}

function PlaguicidasTab() {
  const [pagina, setPagina] = useState(1);
  const [data, setData] = useState<ExcepcionesPlaguicidasResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function cargar() {
    obtenerExcepcionesPlaguicidas(pagina, 20)
      .then(setData)
      .catch((err) => setError(mensajeError(err)));
  }

  useEffect(cargar, [pagina]);

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!data) return <p className="text-sm text-ink-muted">Cargando…</p>;

  return (
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
          filas={data.resumen}
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
              header: "Agrupador",
              accessor: (r) => (
                <AgrupadorCell
                  clave={r.ingrediente_key}
                  onGuardar={async (agrupador) => {
                    await actualizarAgrupadorPlaguicidas(r.ingrediente_key as string, agrupador);
                    cargar();
                  }}
                />
              ),
            },
          ]}
          filas={data.detalle.filas}
          total={data.detalle.total}
          pagina={data.detalle.pagina}
          tamanoPagina={data.detalle.tamano_pagina}
          onCambiarPagina={setPagina}
          getKey={(r, i) => `${r.recibointerno}-${i}`}
        />
      </Card>
    </div>
  );
}

function NutrientesTab() {
  const [pagina, setPagina] = useState(1);
  const [data, setData] = useState<ExcepcionesNutrientesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function cargar() {
    obtenerExcepcionesNutrientes(pagina, 20)
      .then(setData)
      .catch((err) => setError(mensajeError(err)));
  }

  useEffect(cargar, [pagina]);

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!data) return <p className="text-sm text-ink-muted">Cargando…</p>;

  return (
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
          filas={data.resumen}
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
              header: "Agrupador",
              accessor: (r) => (
                <AgrupadorCell
                  clave={r.nombre_key}
                  onGuardar={async (agrupador) => {
                    await actualizarAgrupadorNutrientes(r.nombre_key as string, agrupador);
                    cargar();
                  }}
                />
              ),
            },
          ]}
          filas={data.detalle.filas}
          total={data.detalle.total}
          pagina={data.detalle.pagina}
          tamanoPagina={data.detalle.tamano_pagina}
          onCambiarPagina={setPagina}
          getKey={(r, i) => `${r.no_licencia}-${i}`}
        />
      </Card>
    </div>
  );
}

export function ExcepcionesPage() {
  return (
    <div className="space-y-6">
      <div>
        <Title className="text-ink">Excepciones</Title>
        <Text className="text-ink-muted">
          Transacciones y licencias que no encontraron agrupador en el catálogo — se actualiza al
          instante al asignar un agrupador desde aquí.
        </Text>
      </div>

      <TabGroup>
        <TabList>
          <Tab>Plaguicidas</Tab>
          <Tab>Nutrientes</Tab>
        </TabList>
        <TabPanels>
          <TabPanel className="mt-4">
            <PlaguicidasTab />
          </TabPanel>
          <TabPanel className="mt-4">
            <NutrientesTab />
          </TabPanel>
        </TabPanels>
      </TabGroup>
    </div>
  );
}

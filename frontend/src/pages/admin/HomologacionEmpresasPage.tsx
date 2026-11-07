import { Fragment, useEffect, useMemo, useState } from "react";
import { Badge, Button, Card, Select, SelectItem, Text, TextInput, Title } from "@tremor/react";
import {
  asignarNuevas,
  confirmarGrupos,
  confirmarPendientes,
  listarGruposEmpresas,
  obtenerNuevasSinHomologar,
  renombrarGrupoEmpresa,
  separarVariante,
  unirEmpresas,
} from "../../api/empresas";
import { mensajeError } from "../../api/client";
import { ErrorBox, Modal } from "../../components/admin/Modal";
import { formatFechaHoraGuatemala, formatNumber, formatUSD } from "../../utils/format";
import type {
  EmpresaNueva,
  FiltroEstado,
  FiltroOrigen,
  GrupoEmpresa,
  OrigenGrupo,
  PaginaGruposEmpresas,
  ResultadoHomologacion,
  VarianteEmpresa,
} from "../../types/empresas";

const TAMANO_PAGINA = 25;

const ETIQUETA_ORIGEN: Record<OrigenGrupo, { texto: string; titulo: string; color: "blue" | "emerald" | "violet" | "gray" }> = {
  P: { texto: "P", titulo: "Solo Plaguicidas", color: "blue" },
  N: { texto: "N", titulo: "Solo Nutrientes", color: "emerald" },
  ambas: { texto: "P + N", titulo: "Plaguicidas y Nutrientes", color: "violet" },
  "": { texto: "—", titulo: "Sin movimientos actuales", color: "gray" },
};

function OrigenBadge({ origen }: { origen: OrigenGrupo }) {
  const e = ETIQUETA_ORIGEN[origen];
  return (
    <span title={e.titulo}>
      <Badge color={e.color}>{e.texto}</Badge>
    </span>
  );
}

function EstadoBadge({ confirmada }: { confirmada: boolean }) {
  return confirmada ? <Badge color="emerald">Confirmada</Badge> : <Badge color="amber">Pendiente</Badge>;
}

type Dialogo =
  | { tipo: "unir" }
  | { tipo: "renombrar"; grupo: GrupoEmpresa }
  | { tipo: "separar"; grupo: GrupoEmpresa; variante: VarianteEmpresa }
  | { tipo: "confirmarPendientes" }
  | { tipo: "asignar"; empresas: EmpresaNueva[] };

type Aviso = { tipo: "ok" | "error"; texto: string };

export function HomologacionEmpresasPage() {
  const [pestana, setPestana] = useState<"grupos" | "nuevas">("grupos");
  const [aviso, setAviso] = useState<Aviso | null>(null);

  // ---- Grupos
  const [busquedaInput, setBusquedaInput] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [estado, setEstado] = useState<FiltroEstado>("todas");
  const [origen, setOrigen] = useState<FiltroOrigen>("todas");
  const [pagina, setPagina] = useState(1);
  const [datos, setDatos] = useState<PaginaGruposEmpresas | null>(null);
  const [cargando, setCargando] = useState(true);
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set());
  // La selección se conserva entre páginas: se guarda el grupo completo para conocer sus claves al unir
  const [seleccion, setSeleccion] = useState<Map<string, GrupoEmpresa>>(new Map());

  // ---- Nuevas sin homologar
  const [nuevas, setNuevas] = useState<EmpresaNueva[] | null>(null);
  const [seleccionNuevas, setSeleccionNuevas] = useState<Set<string>>(new Set());

  const [dialogo, setDialogo] = useState<Dialogo | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const [errorDialogo, setErrorDialogo] = useState<string | null>(null);

  function cargarGrupos() {
    setCargando(true);
    listarGruposEmpresas(busqueda, estado, origen, pagina, TAMANO_PAGINA)
      .then((res) => {
        setDatos(res);
        setAviso((a) => (a?.tipo === "error" && a.texto.startsWith("No se pudo cargar") ? null : a));
      })
      .catch((err) => setAviso({ tipo: "error", texto: `No se pudo cargar la lista: ${mensajeError(err)}` }))
      .finally(() => setCargando(false));
  }

  function cargarNuevas() {
    obtenerNuevasSinHomologar()
      .then((res) => setNuevas(res.empresas))
      .catch((err) => setAviso({ tipo: "error", texto: `No se pudo cargar las nuevas: ${mensajeError(err)}` }));
  }

  useEffect(cargarGrupos, [busqueda, estado, origen, pagina]);
  useEffect(cargarNuevas, []);

  const totalPaginas = Math.max(1, Math.ceil((datos?.total ?? 0) / TAMANO_PAGINA));
  const seleccionados = useMemo(() => Array.from(seleccion.values()), [seleccion]);

  function alternarSeleccion(g: GrupoEmpresa) {
    setSeleccion((prev) => {
      const sig = new Map(prev);
      if (sig.has(g.nombre_homologado)) sig.delete(g.nombre_homologado);
      else sig.set(g.nombre_homologado, g);
      return sig;
    });
  }

  function alternarExpandido(nombre: string) {
    setExpandidos((prev) => {
      const sig = new Set(prev);
      if (sig.has(nombre)) sig.delete(nombre);
      else sig.add(nombre);
      return sig;
    });
  }

  function aplicarFiltros() {
    setPagina(1);
    setBusqueda(busquedaInput.trim());
  }

  /** Ejecuta una operación del backend, muestra el resultado y recarga las listas. */
  async function ejecutar(operacion: () => Promise<ResultadoHomologacion>, alExito?: () => void) {
    setTrabajando(true);
    setErrorDialogo(null);
    try {
      const r = await operacion();
      setAviso({
        tipo: "ok",
        texto: `${r.mensaje}${r.filas_sincronizadas ? ` (${formatNumber(r.filas_sincronizadas)} filas ya cargadas actualizadas)` : ""}`,
      });
      setDialogo(null);
      alExito?.();
      cargarGrupos();
      cargarNuevas();
    } catch (err) {
      // El error se muestra dentro del diálogo abierto (o como aviso si no hay uno)
      const texto = mensajeError(err);
      if (dialogo) setErrorDialogo(texto);
      else setAviso({ tipo: "error", texto });
    } finally {
      setTrabajando(false);
    }
  }

  function cerrarDialogo() {
    setDialogo(null);
    setErrorDialogo(null);
  }

  function abrirDialogo(d: Dialogo) {
    setErrorDialogo(null);
    setDialogo(d);
  }

  const hayFiltro = busqueda !== "" || estado !== "todas" || origen !== "todas";

  return (
    <div className="space-y-6">
      <div>
        <Title className="text-ink">Homologación de empresas</Title>
        <Text className="text-ink-muted">
          Unifica las distintas formas en que viene escrita una misma empresa (Plaguicidas y Nutrientes). Los datos
          originales no se modifican: los tableros y las exportaciones muestran el nombre oficial.
        </Text>
      </div>

      {aviso && (
        <div
          role={aviso.tipo === "error" ? "alert" : "status"}
          className={`flex items-start justify-between gap-3 rounded-tremor-small px-3 py-2 text-sm ${
            aviso.tipo === "error"
              ? "bg-danger-surface text-danger"
              : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
          }`}
        >
          <span>{aviso.texto}</span>
          <button type="button" onClick={() => setAviso(null)} className="shrink-0 text-xs underline" aria-label="Cerrar aviso">
            Cerrar
          </button>
        </div>
      )}

      <div className="flex gap-1 border-b border-line">
        {(
          [
            ["grupos", "Grupos de empresas"],
            ["nuevas", `Nuevas sin homologar (${nuevas?.length ?? "…"})`],
          ] as const
        ).map(([id, texto]) => (
          <button
            key={id}
            type="button"
            onClick={() => setPestana(id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm transition-colors ${
              pestana === id
                ? "border-orange-500 font-medium text-accent-emphasis"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {texto}
          </button>
        ))}
      </div>

      {pestana === "grupos" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[14rem] flex-1 sm:max-w-sm">
              <Text className="mb-1 text-xs text-ink-muted">Buscar</Text>
              <TextInput
                value={busquedaInput}
                onValueChange={setBusquedaInput}
                onKeyDown={(e) => {
                  if (e.key === "Enter") aplicarFiltros();
                }}
                placeholder="Nombre oficial o cualquier variante"
              />
            </div>
            <div className="w-40">
              <Text className="mb-1 text-xs text-ink-muted">Estado</Text>
              <Select
                value={estado}
                onValueChange={(v) => {
                  setPagina(1);
                  setEstado(v as FiltroEstado);
                }}
              >
                <SelectItem value="todas">Todas</SelectItem>
                <SelectItem value="pendientes">Pendientes</SelectItem>
                <SelectItem value="confirmadas">Confirmadas</SelectItem>
              </Select>
            </div>
            <div className="w-44">
              <Text className="mb-1 text-xs text-ink-muted">Origen</Text>
              <Select
                value={origen}
                onValueChange={(v) => {
                  setPagina(1);
                  setOrigen(v as FiltroOrigen);
                }}
              >
                <SelectItem value="todas">Todos</SelectItem>
                <SelectItem value="P">Plaguicidas</SelectItem>
                <SelectItem value="N">Nutrientes</SelectItem>
                <SelectItem value="ambas">Ambas</SelectItem>
              </Select>
            </div>
            <Button onClick={aplicarFiltros}>Buscar</Button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <Text className="text-ink-muted">
              {datos
                ? `${formatNumber(datos.total_pendientes)} pendientes · ${formatNumber(datos.total_confirmadas)} confirmadas${
                    hayFiltro ? " (con la búsqueda y el origen actuales)" : ""
                  }`
                : "Cargando…"}
            </Text>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                disabled={seleccionados.length < 2}
                onClick={() => abrirDialogo({ tipo: "unir" })}
                title={seleccionados.length < 2 ? "Selecciona al menos dos grupos" : undefined}
              >
                Unir… {seleccionados.length > 0 && `(${seleccionados.length})`}
              </Button>
              {seleccionados.length > 0 && (
                <Button variant="light" onClick={() => setSeleccion(new Map())}>
                  Quitar selección
                </Button>
              )}
              <Button
                disabled={!datos || datos.pendientes_en_filtro === 0}
                onClick={() => abrirDialogo({ tipo: "confirmarPendientes" })}
              >
                Confirmar todos los pendientes{datos ? ` (${formatNumber(datos.pendientes_en_filtro)})` : ""}
              </Button>
            </div>
          </div>

          <Card className="bg-surface p-0 ring-1 ring-line">
            {cargando && !datos ? (
              <p className="p-4 text-sm text-ink-muted">Cargando…</p>
            ) : !datos || datos.grupos.length === 0 ? (
              <p className="p-6 text-center text-sm text-ink-faint">No hay grupos para los filtros actuales.</p>
            ) : (
              <div className={`overflow-x-auto ${cargando ? "opacity-60" : ""}`}>
                <table className="w-full min-w-[44rem] text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs text-ink-muted">
                      <th className="w-8 px-3 py-2" />
                      <th className="w-8 px-1 py-2" />
                      <th className="px-3 py-2 font-medium">Nombre oficial</th>
                      <th className="px-3 py-2 text-right font-medium">Variantes</th>
                      <th className="px-3 py-2 font-medium">Origen</th>
                      <th className="px-3 py-2 text-right font-medium">CIF USD total</th>
                      <th className="px-3 py-2 font-medium">Estado</th>
                      <th className="px-3 py-2 font-medium">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datos.grupos.map((g) => {
                      const abierto = expandidos.has(g.nombre_homologado);
                      return (
                        <Fragment key={g.nombre_homologado}>
                          <tr className="border-b border-line align-top hover:bg-surface-hover">
                            <td className="px-3 py-2">
                              <input
                                type="checkbox"
                                aria-label={`Seleccionar ${g.nombre_homologado}`}
                                checked={seleccion.has(g.nombre_homologado)}
                                onChange={() => alternarSeleccion(g)}
                              />
                            </td>
                            <td className="px-1 py-2">
                              <button
                                type="button"
                                aria-expanded={abierto}
                                aria-label={abierto ? "Ocultar variantes" : "Ver variantes"}
                                onClick={() => alternarExpandido(g.nombre_homologado)}
                                className="px-1 text-ink-muted hover:text-ink"
                              >
                                {abierto ? "▾" : "▸"}
                              </button>
                            </td>
                            <td className="px-3 py-2 font-medium text-ink">{g.nombre_homologado}</td>
                            <td className="px-3 py-2 text-right text-ink-muted">{formatNumber(g.variantes.length)}</td>
                            <td className="px-3 py-2">
                              <OrigenBadge origen={g.origen} />
                            </td>
                            <td className="px-3 py-2 text-right text-ink">{formatUSD(g.cif_total_usd)}</td>
                            <td className="px-3 py-2">
                              <EstadoBadge confirmada={g.confirmada} />
                            </td>
                            <td className="whitespace-nowrap px-3 py-2">
                              <button
                                type="button"
                                onClick={() => abrirDialogo({ tipo: "renombrar", grupo: g })}
                                className="mr-3 text-xs font-medium text-orange-400 hover:text-orange-300"
                              >
                                Renombrar
                              </button>
                              {!g.confirmada && (
                                <button
                                  type="button"
                                  onClick={() => ejecutar(() => confirmarGrupos([g.nombre_homologado]))}
                                  disabled={trabajando}
                                  className="text-xs font-medium text-orange-400 hover:text-orange-300 disabled:opacity-50"
                                >
                                  Confirmar
                                </button>
                              )}
                            </td>
                          </tr>
                          {abierto && (
                            <tr className="border-b border-line bg-app">
                              <td />
                              <td colSpan={7} className="px-3 py-3">
                                <table className="w-full text-xs">
                                  <thead>
                                    <tr className="text-left text-ink-muted">
                                      <th className="py-1 pr-3 font-medium">Nombre original (como viene)</th>
                                      <th className="py-1 pr-3 text-right font-medium">Plaguicidas</th>
                                      <th className="py-1 pr-3 text-right font-medium">Nutrientes</th>
                                      <th className="py-1 pr-3 text-right font-medium">CIF USD</th>
                                      <th className="py-1 font-medium" />
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {g.variantes.map((v) => (
                                      <tr key={`${v.clave}|${v.nombre_original}`} className="border-t border-line">
                                        <td className="py-1.5 pr-3 text-ink">
                                          {v.nombre_original}
                                          <span className="ml-2 text-ink-faint">clave: {v.clave}</span>
                                        </td>
                                        <td className="py-1.5 pr-3 text-right text-ink-muted">
                                          {v.plaguicidas.filas ? `${formatNumber(v.plaguicidas.filas)} · ${formatUSD(v.plaguicidas.cif_usd)}` : "—"}
                                        </td>
                                        <td className="py-1.5 pr-3 text-right text-ink-muted">
                                          {v.nutrientes.filas ? `${formatNumber(v.nutrientes.filas)} · ${formatUSD(v.nutrientes.cif_usd)}` : "—"}
                                        </td>
                                        <td className="py-1.5 pr-3 text-right text-ink">{formatUSD(v.cif_total_usd)}</td>
                                        <td className="py-1.5 text-right">
                                          {g.puede_separar && (
                                            <button
                                              type="button"
                                              onClick={() => abrirDialogo({ tipo: "separar", grupo: g, variante: v })}
                                              className="text-xs font-medium text-orange-400 hover:text-orange-300"
                                            >
                                              Separar
                                            </button>
                                          )}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                                <p className="mt-2 text-xs text-ink-faint">
                                  Plaguicidas: {formatNumber(g.plaguicidas.filas)} filas · {formatUSD(g.plaguicidas.cif_usd)}.
                                  {" "}Nutrientes (activos): {formatNumber(g.nutrientes.filas)} filas · {formatUSD(g.nutrientes.cif_usd)}.
                                  {g.fecha_mod && ` Última modificación: ${formatFechaHoraGuatemala(g.fecha_mod)}${g.usuario_mod ? ` por ${g.usuario_mod}` : ""}.`}
                                </p>
                                {!g.puede_separar && (
                                  <p className="mt-1 text-xs text-ink-faint">
                                    Estas variantes solo difieren en mayúsculas, puntuación o «S.A.»: se tratan siempre como la misma empresa.
                                  </p>
                                )}
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            {datos && datos.total > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-3 py-2 text-sm text-ink-muted">
                <span>
                  {formatNumber(datos.total)} grupos — página {pagina} de {formatNumber(totalPaginas)}
                </span>
                <div className="flex gap-2">
                  <Button size="xs" variant="secondary" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>
                    Anterior
                  </Button>
                  <Button size="xs" variant="secondary" disabled={pagina >= totalPaginas} onClick={() => setPagina(pagina + 1)}>
                    Siguiente
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {pestana === "nuevas" && (
        <div className="space-y-3">
          <Text className="text-ink-muted">
            Empresas que llegaron en cargas y todavía no están en el catálogo. Mientras no se asignen, los tableros las
            muestran con el nombre original.
          </Text>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Text className="text-ink-muted">{nuevas ? `${formatNumber(nuevas.length)} empresas nuevas` : "Cargando…"}</Text>
            <Button
              variant="secondary"
              disabled={seleccionNuevas.size === 0}
              onClick={() => abrirDialogo({ tipo: "asignar", empresas: (nuevas ?? []).filter((e) => seleccionNuevas.has(e.clave)) })}
            >
              Asignar seleccionadas… {seleccionNuevas.size > 0 && `(${seleccionNuevas.size})`}
            </Button>
          </div>
          <Card className="bg-surface p-0 ring-1 ring-line">
            {!nuevas ? (
              <p className="p-4 text-sm text-ink-muted">Cargando…</p>
            ) : nuevas.length === 0 ? (
              <p className="p-6 text-center text-sm text-ink-muted">
                Todo al día: no hay empresas nuevas pendientes de homologar.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[40rem] text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs text-ink-muted">
                      <th className="w-8 px-3 py-2" />
                      <th className="px-3 py-2 font-medium">Empresa (como llegó)</th>
                      <th className="px-3 py-2 font-medium">Origen</th>
                      <th className="px-3 py-2 text-right font-medium">Filas</th>
                      <th className="px-3 py-2 text-right font-medium">CIF USD</th>
                      <th className="px-3 py-2 font-medium">Última carga</th>
                      <th className="px-3 py-2 font-medium">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nuevas.map((e) => (
                      <tr key={e.clave} className="border-b border-line hover:bg-surface-hover">
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            aria-label={`Seleccionar ${e.nombre_ejemplo}`}
                            checked={seleccionNuevas.has(e.clave)}
                            onChange={() =>
                              setSeleccionNuevas((prev) => {
                                const sig = new Set(prev);
                                if (sig.has(e.clave)) sig.delete(e.clave);
                                else sig.add(e.clave);
                                return sig;
                              })
                            }
                          />
                        </td>
                        <td className="px-3 py-2 font-medium text-ink">{e.nombre_ejemplo}</td>
                        <td className="px-3 py-2">
                          <OrigenBadge origen={e.plaguicidas.filas && e.nutrientes.filas ? "ambas" : e.plaguicidas.filas ? "P" : "N"} />
                        </td>
                        <td className="px-3 py-2 text-right text-ink-muted">
                          {formatNumber(e.plaguicidas.filas + e.nutrientes.filas)}
                        </td>
                        <td className="px-3 py-2 text-right text-ink">{formatUSD(e.cif_total_usd)}</td>
                        <td className="px-3 py-2 text-ink-muted">{e.ultima_carga ? formatFechaHoraGuatemala(e.ultima_carga) : "—"}</td>
                        <td className="whitespace-nowrap px-3 py-2">
                          <button
                            type="button"
                            onClick={() => abrirDialogo({ tipo: "asignar", empresas: [e] })}
                            className="text-xs font-medium text-orange-400 hover:text-orange-300"
                          >
                            Asignar…
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      {dialogo?.tipo === "unir" && (
        <UnirDialogo
          grupos={seleccionados}
          trabajando={trabajando}
          error={errorDialogo}
          onCerrar={cerrarDialogo}
          onUnir={(nombre) =>
            ejecutar(() => unirEmpresas(seleccionados.flatMap((g) => g.claves), nombre), () => setSeleccion(new Map()))
          }
        />
      )}
      {dialogo?.tipo === "renombrar" && (
        <RenombrarDialogo
          grupo={dialogo.grupo}
          trabajando={trabajando}
          error={errorDialogo}
          onCerrar={cerrarDialogo}
          onRenombrar={(nuevo) => {
            const actual = dialogo.grupo.nombre_homologado;
            return ejecutar(() => renombrarGrupoEmpresa(actual, nuevo), () => setSeleccion(new Map()));
          }}
        />
      )}
      {dialogo?.tipo === "separar" && (
        <Modal titulo="Separar variante" onCerrar={cerrarDialogo}>
          <p className="text-sm text-ink-muted">
            La variante <span className="font-medium text-ink">{dialogo.variante.nombre_original}</span> saldrá de «
            {dialogo.grupo.nombre_homologado}» y quedará sola, con su nombre original como nombre oficial, confirmada.
          </p>
          {errorDialogo && <p role="alert" className="mt-3 rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">{errorDialogo}</p>}
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={cerrarDialogo}>Cancelar</Button>
            <Button
              loading={trabajando}
              disabled={trabajando}
              onClick={() => {
                const clave = dialogo.variante.clave;
                return ejecutar(() => separarVariante(clave), () => setSeleccion(new Map()));
              }}
            >
              Separar
            </Button>
          </div>
        </Modal>
      )}
      {dialogo?.tipo === "confirmarPendientes" && datos && (
        <Modal titulo="Confirmar todos los pendientes" onCerrar={cerrarDialogo}>
          <p className="text-sm text-ink-muted">
            Se confirmarán <span className="font-medium text-ink">{formatNumber(datos.pendientes_en_filtro)}</span> grupos
            pendientes
            {busqueda || origen !== "todas" ? " que cumplen la búsqueda y el origen actuales" : " (todos los pendientes)"}.
            El estado de la lista no limita esta acción.
          </p>
          {errorDialogo && <p role="alert" className="mt-3 rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">{errorDialogo}</p>}
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={cerrarDialogo}>Cancelar</Button>
            <Button loading={trabajando} disabled={trabajando} onClick={() => ejecutar(() => confirmarPendientes(busqueda, origen))}>
              Confirmar {formatNumber(datos.pendientes_en_filtro)}
            </Button>
          </div>
        </Modal>
      )}
      {dialogo?.tipo === "asignar" && (
        <AsignarDialogo
          empresas={dialogo.empresas}
          trabajando={trabajando}
          error={errorDialogo}
          onCerrar={cerrarDialogo}
          onAsignar={(nombre, nuevo) =>
            ejecutar(
              () => asignarNuevas(dialogo.empresas.map((e) => e.clave), nombre, nuevo),
              () => setSeleccionNuevas(new Set())
            )
          }
        />
      )}
    </div>
  );
}

function UnirDialogo({
  grupos,
  trabajando,
  error,
  onCerrar,
  onUnir,
}: {
  grupos: GrupoEmpresa[];
  trabajando: boolean;
  error: string | null;
  onCerrar: () => void;
  onUnir: (nombre: string) => void;
}) {
  // Nombres sugeridos: el nombre oficial de cada grupo y cada nombre original (sin repetir), el de más CIF primero
  const opciones = useMemo(() => {
    const vistos = new Set<string>();
    const lista: string[] = [];
    const ordenados = [...grupos].sort((a, b) => b.cif_total_usd - a.cif_total_usd);
    for (const g of ordenados) {
      for (const n of [g.nombre_homologado, ...g.variantes.map((v) => v.nombre_original)]) {
        if (!vistos.has(n.toLowerCase())) {
          vistos.add(n.toLowerCase());
          lista.push(n);
        }
      }
    }
    return lista;
  }, [grupos]);
  const [elegido, setElegido] = useState(opciones[0] ?? "");
  const [escrito, setEscrito] = useState("");
  const [usarEscrito, setUsarEscrito] = useState(false);
  const nombre = (usarEscrito ? escrito : elegido).trim();

  return (
    <Modal titulo={`Unir ${grupos.length} grupos`} onCerrar={onCerrar}>
      <Text className="mb-2 text-ink-muted">Elige el nombre oficial con el que quedarán todos (confirmados):</Text>
      <div className="max-h-56 space-y-1 overflow-y-auto rounded-tremor-small border border-line p-2">
        {opciones.map((o) => (
          <label key={o} className="flex cursor-pointer items-start gap-2 text-sm text-ink">
            <input
              type="radio"
              name="nombre-oficial"
              className="mt-1"
              checked={!usarEscrito && elegido === o}
              onChange={() => {
                setUsarEscrito(false);
                setElegido(o);
              }}
            />
            <span>{o}</span>
          </label>
        ))}
        <label className="flex cursor-pointer items-start gap-2 text-sm text-ink">
          <input type="radio" name="nombre-oficial" className="mt-1" checked={usarEscrito} onChange={() => setUsarEscrito(true)} />
          <span className="flex-1">Otro nombre:</span>
        </label>
        <TextInput
          value={escrito}
          onValueChange={(v) => {
            setEscrito(v);
            setUsarEscrito(true);
          }}
          maxLength={400}
          placeholder="Escribe el nombre oficial"
        />
      </div>
      <ErrorBox texto={error} />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCerrar}>Cancelar</Button>
        <Button loading={trabajando} disabled={trabajando || !nombre} onClick={() => onUnir(nombre)}>
          Unir
        </Button>
      </div>
    </Modal>
  );
}

function RenombrarDialogo({
  grupo,
  trabajando,
  error,
  onCerrar,
  onRenombrar,
}: {
  grupo: GrupoEmpresa;
  trabajando: boolean;
  error: string | null;
  onCerrar: () => void;
  onRenombrar: (nuevo: string) => void;
}) {
  const [nuevo, setNuevo] = useState(grupo.nombre_homologado);
  const limpio = nuevo.trim();
  return (
    <Modal titulo="Renombrar grupo" onCerrar={onCerrar}>
      <Text className="mb-1 text-xs text-ink-muted">Nombre oficial</Text>
      <TextInput
        autoFocus
        value={nuevo}
        onValueChange={setNuevo}
        maxLength={400}
        onKeyDown={(e) => {
          if (e.key === "Enter" && limpio && limpio !== grupo.nombre_homologado && !trabajando) onRenombrar(limpio);
        }}
      />
      <ErrorBox texto={error} />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCerrar}>Cancelar</Button>
        <Button
          loading={trabajando}
          disabled={trabajando || !limpio || limpio === grupo.nombre_homologado}
          onClick={() => onRenombrar(limpio)}
        >
          Guardar
        </Button>
      </div>
    </Modal>
  );
}

function AsignarDialogo({
  empresas,
  trabajando,
  error,
  onCerrar,
  onAsignar,
}: {
  empresas: EmpresaNueva[];
  trabajando: boolean;
  error: string | null;
  onCerrar: () => void;
  onAsignar: (nombre: string, nuevo: boolean) => void;
}) {
  const [modo, setModo] = useState<"nuevo" | "existente">("nuevo");
  const [nombreNuevo, setNombreNuevo] = useState(empresas[0]?.nombre_ejemplo ?? "");
  const [busqueda, setBusqueda] = useState("");
  const [resultados, setResultados] = useState<GrupoEmpresa[]>([]);
  const [elegido, setElegido] = useState<string | null>(null);

  useEffect(() => {
    if (modo !== "existente" || busqueda.trim().length < 2) {
      setResultados([]);
      return;
    }
    // Pequeña espera para no consultar en cada tecla
    const t = setTimeout(() => {
      listarGruposEmpresas(busqueda.trim(), "todas", "todas", 1, 8)
        .then((r) => setResultados(r.grupos))
        .catch(() => setResultados([]));
    }, 300);
    return () => clearTimeout(t);
  }, [modo, busqueda]);

  const nombre = modo === "nuevo" ? nombreNuevo.trim() : elegido ?? "";
  return (
    <Modal titulo={empresas.length === 1 ? "Asignar empresa nueva" : `Asignar ${empresas.length} empresas nuevas`} onCerrar={onCerrar}>
      <ul className="mb-3 max-h-24 list-inside list-disc overflow-y-auto text-sm text-ink-muted">
        {empresas.map((e) => (
          <li key={e.clave}>{e.nombre_ejemplo}</li>
        ))}
      </ul>
      <div className="space-y-3">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
          <input type="radio" name="modo" checked={modo === "nuevo"} onChange={() => setModo("nuevo")} />
          Crear un grupo nuevo
        </label>
        {modo === "nuevo" && (
          <TextInput autoFocus value={nombreNuevo} onValueChange={setNombreNuevo} maxLength={400} placeholder="Nombre oficial del grupo" />
        )}
        <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
          <input type="radio" name="modo" checked={modo === "existente"} onChange={() => setModo("existente")} />
          Agregar a un grupo existente
        </label>
        {modo === "existente" && (
          <div>
            <TextInput value={busqueda} onValueChange={setBusqueda} placeholder="Busca el grupo (mínimo 2 letras)" />
            <div className="mt-2 max-h-40 space-y-1 overflow-y-auto">
              {resultados.map((g) => (
                <label key={g.nombre_homologado} className="flex cursor-pointer items-start gap-2 text-sm text-ink">
                  <input
                    type="radio"
                    name="grupo-existente"
                    className="mt-1"
                    checked={elegido === g.nombre_homologado}
                    onChange={() => setElegido(g.nombre_homologado)}
                  />
                  <span>{g.nombre_homologado}</span>
                </label>
              ))}
              {busqueda.trim().length >= 2 && resultados.length === 0 && (
                <p className="text-xs text-ink-faint">Sin resultados.</p>
              )}
            </div>
          </div>
        )}
      </div>
      <ErrorBox texto={error} />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCerrar}>Cancelar</Button>
        <Button loading={trabajando} disabled={trabajando || !nombre} onClick={() => onAsignar(nombre, modo === "nuevo")}>
          Asignar
        </Button>
      </div>
    </Modal>
  );
}

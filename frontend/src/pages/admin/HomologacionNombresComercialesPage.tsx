import { Fragment, useEffect, useMemo, useState } from "react";
import { Badge, Button, Card, Select, SelectItem, Text, TextInput, Title } from "@tremor/react";
import {
  asignarNombresNuevos,
  cargarExcelNombres,
  confirmarNombres,
  confirmarPendientesNombres,
  listarGruposNombres,
  listarNuevosNombres,
  renombrarNombre,
  separarNombre,
  unirNombres,
} from "../../api/nombresComerciales";
import { mensajeError } from "../../api/client";
import { ErrorBox, Modal } from "../../components/admin/Modal";
import { formatFechaHoraGuatemala, formatNumber, formatUSD } from "../../utils/format";
import type { FiltroEstado } from "../../types/empresas";
import type {
  GrupoNombre,
  NombreNuevo,
  NuevosSinHomologarNombres,
  PaginaGruposNombres,
  ResultadoExcelNombres,
  ResultadoNombres,
  TipoNombres,
  VarianteNombre,
} from "../../types/nombresComerciales";

const TAMANO_PAGINA = 25;

type Pestana = "grupos" | "nuevos" | "excel";
type Dialogo =
  | { tipo: "unir" }
  | { tipo: "renombrar"; grupo: GrupoNombre }
  | { tipo: "separar"; grupo: GrupoNombre; variante: VarianteNombre }
  | { tipo: "confirmarPendientes" }
  | { tipo: "asignar"; nombres: NombreNuevo[] };
type Aviso = { tipo: "ok" | "error"; texto: string };

function EstadoBadge({ confirmada }: { confirmada: boolean }) {
  return confirmada ? <Badge color="emerald">Confirmada</Badge> : <Badge color="amber">Pendiente</Badge>;
}

export function HomologacionNombresComercialesPage() {
  const [tipo, setTipo] = useState<TipoNombres>("plaguicidas");
  const [pestana, setPestana] = useState<Pestana>("grupos");
  const [aviso, setAviso] = useState<Aviso | null>(null);

  // ---- Grupos
  const [busquedaInput, setBusquedaInput] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [estado, setEstado] = useState<FiltroEstado>("todas");
  const [pagina, setPagina] = useState(1);
  const [datos, setDatos] = useState<PaginaGruposNombres | null>(null);
  const [cargando, setCargando] = useState(true);
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set());
  const [seleccion, setSeleccion] = useState<Map<string, GrupoNombre>>(new Map());

  // ---- Nuevos sin homologar
  const [busquedaNuevosInput, setBusquedaNuevosInput] = useState("");
  const [busquedaNuevos, setBusquedaNuevos] = useState("");
  const [paginaNuevos, setPaginaNuevos] = useState(1);
  const [nuevos, setNuevos] = useState<NuevosSinHomologarNombres | null>(null);
  const [totalNuevos, setTotalNuevos] = useState<number | null>(null);
  const [seleccionNuevos, setSeleccionNuevos] = useState<Map<string, NombreNuevo>>(new Map());

  // ---- Excel estándar
  const [archivo, setArchivo] = useState<File | null>(null);
  const [vistaPrevia, setVistaPrevia] = useState<ResultadoExcelNombres | null>(null);
  const [procesandoExcel, setProcesandoExcel] = useState(false);
  const [errorExcel, setErrorExcel] = useState<string | null>(null);

  const [dialogo, setDialogo] = useState<Dialogo | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const [errorDialogo, setErrorDialogo] = useState<string | null>(null);

  function cargarGrupos() {
    setCargando(true);
    listarGruposNombres(tipo, busqueda, estado, pagina, TAMANO_PAGINA)
      .then(setDatos)
      .catch((err) => setAviso({ tipo: "error", texto: `No se pudo cargar la lista: ${mensajeError(err)}` }))
      .finally(() => setCargando(false));
  }

  function cargarNuevos() {
    listarNuevosNombres(tipo, busquedaNuevos, paginaNuevos, TAMANO_PAGINA)
      .then((r) => {
        setNuevos(r);
        if (!busquedaNuevos) setTotalNuevos(r.total);
      })
      .catch((err) => setAviso({ tipo: "error", texto: `No se pudo cargar los nombres nuevos: ${mensajeError(err)}` }));
  }

  useEffect(cargarGrupos, [tipo, busqueda, estado, pagina]);
  useEffect(cargarNuevos, [tipo, busquedaNuevos, paginaNuevos]);

  function cambiarTipo(nuevo: TipoNombres) {
    if (nuevo === tipo) return;
    setTipo(nuevo);
    setPagina(1);
    setPaginaNuevos(1);
    setBusquedaInput("");
    setBusqueda("");
    setBusquedaNuevosInput("");
    setBusquedaNuevos("");
    setEstado("todas");
    setSeleccion(new Map());
    setSeleccionNuevos(new Map());
    setExpandidos(new Set());
    setDatos(null);
    setNuevos(null);
    setTotalNuevos(null);
    setArchivo(null);
    setVistaPrevia(null);
    setErrorExcel(null);
    setAviso(null);
  }

  const totalPaginas = Math.max(1, Math.ceil((datos?.total ?? 0) / TAMANO_PAGINA));
  const totalPaginasNuevos = Math.max(1, Math.ceil((nuevos?.total ?? 0) / TAMANO_PAGINA));
  const seleccionados = useMemo(() => Array.from(seleccion.values()), [seleccion]);
  const nuevosSeleccionados = useMemo(() => Array.from(seleccionNuevos.values()), [seleccionNuevos]);

  function alternar<T>(setter: (f: (prev: Map<string, T>) => Map<string, T>) => void, clave: string, valor: T) {
    setter((prev) => {
      const sig = new Map(prev);
      if (sig.has(clave)) sig.delete(clave);
      else sig.set(clave, valor);
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

  async function ejecutar(operacion: () => Promise<ResultadoNombres>, alExito?: () => void) {
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
      cargarNuevos();
    } catch (err) {
      const texto = mensajeError(err);
      if (dialogo) setErrorDialogo(texto);
      else setAviso({ tipo: "error", texto });
    } finally {
      setTrabajando(false);
    }
  }

  function abrirDialogo(d: Dialogo) {
    setErrorDialogo(null);
    setDialogo(d);
  }

  function cerrarDialogo() {
    setDialogo(null);
    setErrorDialogo(null);
  }

  async function procesarExcel(aplicar: boolean) {
    if (!archivo) return;
    setProcesandoExcel(true);
    setErrorExcel(null);
    try {
      const r = await cargarExcelNombres(tipo, archivo, aplicar);
      setVistaPrevia(r);
      if (aplicar) {
        setAviso({
          tipo: "ok",
          texto: `${r.mensaje}${r.filas_sincronizadas ? ` (${formatNumber(r.filas_sincronizadas)} filas ya cargadas actualizadas)` : ""}`,
        });
        cargarGrupos();
        cargarNuevos();
      }
    } catch (err) {
      setErrorExcel(mensajeError(err));
      if (!aplicar) setVistaPrevia(null);
    } finally {
      setProcesandoExcel(false);
    }
  }

  const etiquetaTipo = tipo === "plaguicidas" ? "Plaguicidas" : "Nutrientes";

  return (
    <div className="space-y-6">
      <div>
        <Title className="text-ink">Homologación de nombres comerciales</Title>
        <Text className="text-ink-muted">
          Indica qué nombres comerciales son el mismo producto. Los datos originales no se modifican: los tableros y las
          exportaciones muestran el nombre estándar.
          {tipo === "nutrientes" && " En Nutrientes el estándar es el producto agrupado (fórmula) del Agrupador de nutrientes."}
        </Text>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="w-48">
          <Text className="mb-1 text-xs text-ink-muted">Tipo</Text>
          <Select value={tipo} onValueChange={(v) => cambiarTipo(v as TipoNombres)}>
            <SelectItem value="plaguicidas">Plaguicidas</SelectItem>
            <SelectItem value="nutrientes">Nutrientes</SelectItem>
          </Select>
        </div>
      </div>

      {aviso && (
        <div
          role={aviso.tipo === "error" ? "alert" : "status"}
          className={`flex items-start justify-between gap-3 rounded-tremor-small px-3 py-2 text-sm ${
            aviso.tipo === "error" ? "bg-danger-surface text-danger" : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
          }`}
        >
          <span>{aviso.texto}</span>
          <button type="button" onClick={() => setAviso(null)} className="shrink-0 text-xs underline" aria-label="Cerrar aviso">
            Cerrar
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-1 border-b border-line">
        {(
          [
            ["grupos", "Grupos de nombres"],
            ["nuevos", `Nuevos sin homologar (${totalNuevos ?? "…"})`],
            ["excel", "Cargar Excel estándar"],
          ] as const
        ).map(([id, texto]) => (
          <button
            key={id}
            type="button"
            onClick={() => setPestana(id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm transition-colors ${
              pestana === id ? "border-orange-500 font-medium text-accent-emphasis" : "border-transparent text-ink-muted hover:text-ink"
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
                  if (e.key === "Enter") {
                    setPagina(1);
                    setBusqueda(busquedaInput.trim());
                  }
                }}
                placeholder="Nombre estándar o cualquier variante"
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
            <Button
              onClick={() => {
                setPagina(1);
                setBusqueda(busquedaInput.trim());
              }}
            >
              Buscar
            </Button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <Text className="text-ink-muted">
              {datos
                ? `${formatNumber(datos.total_pendientes)} pendientes · ${formatNumber(datos.total_confirmadas)} confirmadas${
                    busqueda ? " (con la búsqueda actual)" : ""
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
              <Button disabled={!datos || datos.pendientes_en_filtro === 0} onClick={() => abrirDialogo({ tipo: "confirmarPendientes" })}>
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
                <table className="w-full min-w-[40rem] text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs text-ink-muted">
                      <th className="w-8 px-3 py-2" />
                      <th className="w-8 px-1 py-2" />
                      <th className="px-3 py-2 font-medium">Nombre estándar</th>
                      <th className="px-3 py-2 text-right font-medium">Variantes</th>
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
                                onChange={() => alternar(setSeleccion, g.nombre_homologado, g)}
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
                            <td className="px-3 py-2 text-right text-ink">{formatUSD(g.cif_usd)}</td>
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
                                  onClick={() => ejecutar(() => confirmarNombres(tipo, [g.nombre_homologado]))}
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
                              <td colSpan={6} className="px-3 py-3">
                                {g.variantes.length === 0 ? (
                                  <p className="text-xs text-ink-faint">Este nombre no tiene movimientos actuales en los datos.</p>
                                ) : (
                                  <table className="w-full text-xs">
                                    <thead>
                                      <tr className="text-left text-ink-muted">
                                        <th className="py-1 pr-3 font-medium">Nombre original (como viene)</th>
                                        <th className="py-1 pr-3 text-right font-medium">Filas</th>
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
                                          <td className="py-1.5 pr-3 text-right text-ink-muted">{formatNumber(v.filas)}</td>
                                          <td className="py-1.5 pr-3 text-right text-ink">{formatUSD(v.cif_usd)}</td>
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
                                )}
                                <p className="mt-2 text-xs text-ink-faint">
                                  {g.fecha_mod && `Última modificación: ${formatFechaHoraGuatemala(g.fecha_mod)}${g.usuario_mod ? ` por ${g.usuario_mod}` : ""}. `}
                                  {!g.puede_separar && "Las variantes que solo difieren en mayúsculas, tildes o puntuación se tratan siempre como el mismo nombre."}
                                </p>
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

      {pestana === "nuevos" && (
        <div className="space-y-3">
          <Text className="text-ink-muted">
            Nombres comerciales de {etiquetaTipo} que están en los datos y todavía no tienen entrada en el catálogo. Mientras no se
            asignen, los tableros los muestran con el nombre original.
          </Text>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="flex items-end gap-3">
              <div className="min-w-[14rem]">
                <Text className="mb-1 text-xs text-ink-muted">Buscar</Text>
                <TextInput
                  value={busquedaNuevosInput}
                  onValueChange={setBusquedaNuevosInput}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      setPaginaNuevos(1);
                      setBusquedaNuevos(busquedaNuevosInput.trim());
                    }
                  }}
                  placeholder="Nombre comercial"
                />
              </div>
              <Button
                onClick={() => {
                  setPaginaNuevos(1);
                  setBusquedaNuevos(busquedaNuevosInput.trim());
                }}
              >
                Buscar
              </Button>
            </div>
            <Button
              variant="secondary"
              disabled={nuevosSeleccionados.length === 0}
              onClick={() => abrirDialogo({ tipo: "asignar", nombres: nuevosSeleccionados })}
            >
              Asignar seleccionados… {nuevosSeleccionados.length > 0 && `(${nuevosSeleccionados.length})`}
            </Button>
          </div>
          <Card className="bg-surface p-0 ring-1 ring-line">
            {!nuevos ? (
              <p className="p-4 text-sm text-ink-muted">Cargando…</p>
            ) : nuevos.total === 0 ? (
              <p className="p-6 text-center text-sm text-ink-muted">
                {busquedaNuevos ? "Sin resultados para la búsqueda." : "Todo al día: no hay nombres nuevos pendientes de homologar."}
              </p>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[36rem] text-sm">
                    <thead>
                      <tr className="border-b border-line text-left text-xs text-ink-muted">
                        <th className="w-8 px-3 py-2" />
                        <th className="px-3 py-2 font-medium">Nombre comercial (como llegó)</th>
                        <th className="px-3 py-2 text-right font-medium">Filas</th>
                        <th className="px-3 py-2 text-right font-medium">CIF USD</th>
                        <th className="px-3 py-2 font-medium">Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {nuevos.nombres.map((n) => (
                        <tr key={n.clave} className="border-b border-line hover:bg-surface-hover">
                          <td className="px-3 py-2">
                            <input
                              type="checkbox"
                              aria-label={`Seleccionar ${n.nombre_ejemplo}`}
                              checked={seleccionNuevos.has(n.clave)}
                              onChange={() => alternar(setSeleccionNuevos, n.clave, n)}
                            />
                          </td>
                          <td className="px-3 py-2 font-medium text-ink">
                            {n.nombre_ejemplo}
                            {n.variantes.length > 1 && <span className="ml-2 text-xs text-ink-faint">({n.variantes.length} formas de escribirlo)</span>}
                          </td>
                          <td className="px-3 py-2 text-right text-ink-muted">{formatNumber(n.filas)}</td>
                          <td className="px-3 py-2 text-right text-ink">{formatUSD(n.cif_usd)}</td>
                          <td className="whitespace-nowrap px-3 py-2">
                            <button
                              type="button"
                              onClick={() => abrirDialogo({ tipo: "asignar", nombres: [n] })}
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
                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-3 py-2 text-sm text-ink-muted">
                  <span>
                    {formatNumber(nuevos.total)} nombres — página {paginaNuevos} de {formatNumber(totalPaginasNuevos)}
                  </span>
                  <div className="flex gap-2">
                    <Button size="xs" variant="secondary" disabled={paginaNuevos <= 1} onClick={() => setPaginaNuevos(paginaNuevos - 1)}>
                      Anterior
                    </Button>
                    <Button size="xs" variant="secondary" disabled={paginaNuevos >= totalPaginasNuevos} onClick={() => setPaginaNuevos(paginaNuevos + 1)}>
                      Siguiente
                    </Button>
                  </div>
                </div>
              </>
            )}
          </Card>
        </div>
      )}

      {pestana === "excel" && (
        <Card className="space-y-4 bg-surface ring-1 ring-line">
          <div>
            <Title className="text-ink">Excel estándar de {etiquetaTipo}</Title>
            <Text className="mt-1 text-ink-muted">
              Sube un Excel (.xlsx) con dos columnas: <span className="text-ink">nombre comercial</span> y <span className="text-ink">nombre estándar</span>.
              Cada fila dice que ese nombre comercial es el mismo que el estándar. Primero se muestra una vista previa; no se cambia nada
              hasta que pulses «Aplicar».
            </Text>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Text className="mb-1 text-xs text-ink-muted">Archivo</Text>
              <input
                type="file"
                accept=".xlsx,.xlsm"
                aria-label="Archivo Excel estándar"
                onChange={(e) => {
                  setArchivo(e.target.files?.[0] ?? null);
                  setVistaPrevia(null);
                  setErrorExcel(null);
                }}
                className="block text-sm text-ink-muted file:mr-3 file:rounded-tremor-small file:border-0 file:bg-accent-subtle file:px-3 file:py-1.5 file:text-sm file:text-accent-emphasis"
              />
            </div>
            <Button variant="secondary" disabled={!archivo || procesandoExcel} loading={procesandoExcel && !vistaPrevia} onClick={() => procesarExcel(false)}>
              Ver vista previa
            </Button>
            <Button
              disabled={!archivo || !vistaPrevia || vistaPrevia.aplicado || procesandoExcel || vistaPrevia.se_uniran + vistaPrevia.nuevos === 0}
              loading={procesandoExcel && !!vistaPrevia}
              onClick={() => procesarExcel(true)}
            >
              Aplicar
            </Button>
          </div>
          {errorExcel && <ErrorBox texto={errorExcel} />}
          {vistaPrevia && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                {(
                  [
                    ["Filas leídas", vistaPrevia.filas_leidas, "text-ink"],
                    ["Se unirán", vistaPrevia.se_uniran, "text-ink"],
                    ["Nuevos", vistaPrevia.nuevos, "text-ink"],
                    ["Sin cambio", vistaPrevia.sin_cambio, "text-ink-muted"],
                    ["Con conflicto", vistaPrevia.conflictos, vistaPrevia.conflictos > 0 ? "text-danger" : "text-ink-muted"],
                  ] as const
                ).map(([etiqueta, valor, color]) => (
                  <div key={etiqueta} className="rounded-tremor-small border border-line p-3">
                    <p className="text-xs text-ink-muted">{etiqueta}</p>
                    <p className={`text-xl font-semibold ${color}`}>{formatNumber(valor)}</p>
                  </div>
                ))}
              </div>
              <Text className={vistaPrevia.aplicado ? "text-emerald-700 dark:text-emerald-300" : "text-ink-muted"}>
                {vistaPrevia.aplicado ? vistaPrevia.mensaje : `${vistaPrevia.mensaje} Las filas con conflicto no se aplican.`}
              </Text>
              {vistaPrevia.detalle.length > 0 && (
                <div className="max-h-80 overflow-auto rounded-tremor-small border border-line">
                  <table className="w-full min-w-[36rem] text-xs">
                    <thead>
                      <tr className="border-b border-line text-left text-ink-muted">
                        <th className="px-3 py-2 font-medium">Fila</th>
                        <th className="px-3 py-2 font-medium">Nombre comercial</th>
                        <th className="px-3 py-2 font-medium">Nombre estándar</th>
                        <th className="px-3 py-2 font-medium">Resultado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vistaPrevia.detalle.map((d) => (
                        <tr key={`${d.fila}-${d.nombre}`} className="border-b border-line">
                          <td className="px-3 py-1.5 text-ink-muted">{d.fila}</td>
                          <td className="px-3 py-1.5 text-ink">{d.nombre || "—"}</td>
                          <td className="px-3 py-1.5 text-ink">{d.nombre_estandar || "—"}</td>
                          <td className="px-3 py-1.5">
                            {d.estado === "nuevo" && <Badge color="blue">Nuevo</Badge>}
                            {d.estado === "se_unira" && (
                              <span>
                                <Badge color="emerald">Se unirá</Badge>
                                {d.nombre_actual && <span className="ml-2 text-ink-faint">antes: {d.nombre_actual}</span>}
                              </span>
                            )}
                            {d.estado === "conflicto" && (
                              <span>
                                <Badge color="red">Conflicto</Badge>
                                {d.motivo && <span className="ml-2 text-ink-faint">{d.motivo}</span>}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {dialogo?.tipo === "unir" && (
        <UnirDialogo
          grupos={seleccionados}
          trabajando={trabajando}
          error={errorDialogo}
          onCerrar={cerrarDialogo}
          onUnir={(nombre) => ejecutar(() => unirNombres(tipo, seleccionados.flatMap((g) => g.claves), nombre), () => setSeleccion(new Map()))}
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
            return ejecutar(() => renombrarNombre(tipo, actual, nuevo), () => setSeleccion(new Map()));
          }}
        />
      )}
      {dialogo?.tipo === "separar" && (
        <Modal titulo="Separar variante" onCerrar={cerrarDialogo}>
          <p className="text-sm text-ink-muted">
            La variante <span className="font-medium text-ink">{dialogo.variante.nombre_original}</span> saldrá de «
            {dialogo.grupo.nombre_homologado}» y quedará sola, con su nombre original como nombre estándar, confirmada.
          </p>
          <ErrorBox texto={errorDialogo} />
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={cerrarDialogo}>
              Cancelar
            </Button>
            <Button
              loading={trabajando}
              disabled={trabajando}
              onClick={() => {
                const clave = dialogo.variante.clave;
                return ejecutar(() => separarNombre(tipo, clave), () => setSeleccion(new Map()));
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
            Se confirmarán <span className="font-medium text-ink">{formatNumber(datos.pendientes_en_filtro)}</span> grupos pendientes
            {busqueda ? " que cumplen la búsqueda actual" : " (todos los pendientes)"}. El estado de la lista no limita esta acción.
          </p>
          <ErrorBox texto={errorDialogo} />
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={cerrarDialogo}>
              Cancelar
            </Button>
            <Button loading={trabajando} disabled={trabajando} onClick={() => ejecutar(() => confirmarPendientesNombres(tipo, busqueda))}>
              Confirmar {formatNumber(datos.pendientes_en_filtro)}
            </Button>
          </div>
        </Modal>
      )}
      {dialogo?.tipo === "asignar" && (
        <AsignarDialogo
          tipo={tipo}
          nombres={dialogo.nombres}
          trabajando={trabajando}
          error={errorDialogo}
          onCerrar={cerrarDialogo}
          onAsignar={(nombre, nuevo) =>
            ejecutar(
              () => asignarNombresNuevos(tipo, dialogo.nombres.map((n) => n.clave), nombre, nuevo),
              () => setSeleccionNuevos(new Map())
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
  grupos: GrupoNombre[];
  trabajando: boolean;
  error: string | null;
  onCerrar: () => void;
  onUnir: (nombre: string) => void;
}) {
  const opciones = useMemo(() => {
    const vistos = new Set<string>();
    const lista: string[] = [];
    for (const g of [...grupos].sort((a, b) => b.cif_usd - a.cif_usd)) {
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
      <Text className="mb-2 text-ink-muted">Elige el nombre estándar con el que quedarán todos (confirmados):</Text>
      <div className="max-h-56 space-y-1 overflow-y-auto rounded-tremor-small border border-line p-2">
        {opciones.map((o) => (
          <label key={o} className="flex cursor-pointer items-start gap-2 text-sm text-ink">
            <input
              type="radio"
              name="nombre-estandar"
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
          <input type="radio" name="nombre-estandar" className="mt-1" checked={usarEscrito} onChange={() => setUsarEscrito(true)} />
          <span className="flex-1">Otro nombre:</span>
        </label>
        <TextInput
          value={escrito}
          onValueChange={(v) => {
            setEscrito(v);
            setUsarEscrito(true);
          }}
          maxLength={400}
          placeholder="Escribe el nombre estándar"
        />
      </div>
      <ErrorBox texto={error} />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCerrar}>
          Cancelar
        </Button>
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
  grupo: GrupoNombre;
  trabajando: boolean;
  error: string | null;
  onCerrar: () => void;
  onRenombrar: (nuevo: string) => void;
}) {
  const [nuevo, setNuevo] = useState(grupo.nombre_homologado);
  const limpio = nuevo.trim();
  return (
    <Modal titulo="Renombrar grupo" onCerrar={onCerrar}>
      <Text className="mb-1 text-xs text-ink-muted">Nombre estándar</Text>
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
        <Button variant="secondary" onClick={onCerrar}>
          Cancelar
        </Button>
        <Button loading={trabajando} disabled={trabajando || !limpio || limpio === grupo.nombre_homologado} onClick={() => onRenombrar(limpio)}>
          Guardar
        </Button>
      </div>
    </Modal>
  );
}

function AsignarDialogo({
  tipo,
  nombres,
  trabajando,
  error,
  onCerrar,
  onAsignar,
}: {
  tipo: TipoNombres;
  nombres: NombreNuevo[];
  trabajando: boolean;
  error: string | null;
  onCerrar: () => void;
  onAsignar: (nombre: string, nuevo: boolean) => void;
}) {
  const [modo, setModo] = useState<"nuevo" | "existente">("nuevo");
  const [nombreNuevo, setNombreNuevo] = useState(nombres[0]?.nombre_ejemplo ?? "");
  const [busqueda, setBusqueda] = useState("");
  const [resultados, setResultados] = useState<GrupoNombre[]>([]);
  const [elegido, setElegido] = useState<string | null>(null);

  useEffect(() => {
    if (modo !== "existente" || busqueda.trim().length < 2) {
      setResultados([]);
      return;
    }
    const t = setTimeout(() => {
      listarGruposNombres(tipo, busqueda.trim(), "todas", 1, 8)
        .then((r) => setResultados(r.grupos))
        .catch(() => setResultados([]));
    }, 300);
    return () => clearTimeout(t);
  }, [tipo, modo, busqueda]);

  const nombre = modo === "nuevo" ? nombreNuevo.trim() : elegido ?? "";
  return (
    <Modal titulo={nombres.length === 1 ? "Asignar nombre nuevo" : `Asignar ${nombres.length} nombres nuevos`} onCerrar={onCerrar}>
      <ul className="mb-3 max-h-24 list-inside list-disc overflow-y-auto text-sm text-ink-muted">
        {nombres.map((n) => (
          <li key={n.clave}>{n.nombre_ejemplo}</li>
        ))}
      </ul>
      <div className="space-y-3">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
          <input type="radio" name="modo" checked={modo === "nuevo"} onChange={() => setModo("nuevo")} />
          Crear un grupo nuevo
        </label>
        {modo === "nuevo" && (
          <TextInput autoFocus value={nombreNuevo} onValueChange={setNombreNuevo} maxLength={400} placeholder="Nombre estándar del grupo" />
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
              {busqueda.trim().length >= 2 && resultados.length === 0 && <p className="text-xs text-ink-faint">Sin resultados.</p>}
            </div>
          </div>
        )}
      </div>
      <ErrorBox texto={error} />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCerrar}>
          Cancelar
        </Button>
        <Button loading={trabajando} disabled={trabajando || !nombre} onClick={() => onAsignar(nombre, modo === "nuevo")}>
          Asignar
        </Button>
      </div>
    </Modal>
  );
}

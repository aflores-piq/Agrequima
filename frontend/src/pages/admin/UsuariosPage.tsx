import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Badge, Button, Card, Select, SelectItem, TextInput, Title, Text } from "@tremor/react";
import { actualizarUsuario, cambiarPasswordUsuario, crearUsuario, listarUsuarios } from "../../api/usuarios";
import { mensajeError } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { SimpleDataTable } from "../../components/SimpleDataTable";
import type { Rol } from "../../types/auth";
import type { UsuarioOut } from "../../types/usuarios";

export function UsuariosPage() {
  const { sesion } = useAuth();
  // "Administrador de Usuarios" (personal de Agrequima) solo puede crear
  // o dejar cuentas con rol "Usuario" — asignar "Administrador" o
  // "Administrador de Usuarios" le está vedado también en el backend,
  // pero el selector ya no debe ni ofrecer esas opciones.
  const puedeAsignarRolesDeAdministracion = sesion?.rol === "Administrador";
  const [usuarios, setUsuarios] = useState<UsuarioOut[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [nombreUsuario, setNombreUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [nombreCompleto, setNombreCompleto] = useState("");
  const [rol, setRol] = useState<Rol>("Usuario");
  const [puedeExportar, setPuedeExportar] = useState(false);
  const [creando, setCreando] = useState(false);
  const [errorForm, setErrorForm] = useState<string | null>(null);

  const [editandoPasswordId, setEditandoPasswordId] = useState<number | null>(null);
  const [nuevaPassword, setNuevaPassword] = useState("");
  const [guardandoPassword, setGuardandoPassword] = useState(false);
  const [errorPassword, setErrorPassword] = useState<string | null>(null);

  function cargar() {
    setCargando(true);
    listarUsuarios()
      .then(setUsuarios)
      .catch((err) => setError(mensajeError(err)))
      .finally(() => setCargando(false));
  }

  useEffect(cargar, []);

  async function handleCrear(e: FormEvent) {
    e.preventDefault();
    setErrorForm(null);
    setCreando(true);
    try {
      await crearUsuario({
        nombre_usuario: nombreUsuario,
        password,
        nombre_completo: nombreCompleto || undefined,
        rol,
        puede_exportar: puedeExportar,
      });
      setNombreUsuario("");
      setPassword("");
      setNombreCompleto("");
      setRol("Usuario");
      setPuedeExportar(false);
      cargar();
    } catch (err) {
      setErrorForm(mensajeError(err));
    } finally {
      setCreando(false);
    }
  }

  async function cambiarRol(usuario: UsuarioOut, nuevoRol: Rol) {
    try {
      await actualizarUsuario(usuario.usuario_id, { rol: nuevoRol });
      cargar();
    } catch (err) {
      setError(mensajeError(err));
    }
  }

  async function alternarActivo(usuario: UsuarioOut) {
    try {
      await actualizarUsuario(usuario.usuario_id, { activo: !usuario.activo });
      cargar();
    } catch (err) {
      setError(mensajeError(err));
    }
  }

  function iniciarCambioPassword(usuario: UsuarioOut) {
    setEditandoPasswordId(usuario.usuario_id);
    setNuevaPassword("");
    setErrorPassword(null);
  }

  function cancelarCambioPassword() {
    setEditandoPasswordId(null);
    setNuevaPassword("");
    setErrorPassword(null);
  }

  async function guardarNuevaPassword(usuarioId: number) {
    setErrorPassword(null);
    if (nuevaPassword.length < 8) {
      setErrorPassword("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    setGuardandoPassword(true);
    try {
      await cambiarPasswordUsuario(usuarioId, { password: nuevaPassword });
      cancelarCambioPassword();
    } catch (err) {
      setErrorPassword(mensajeError(err));
    } finally {
      setGuardandoPassword(false);
    }
  }

  async function alternarPuedeExportar(usuario: UsuarioOut) {
    try {
      await actualizarUsuario(usuario.usuario_id, { puede_exportar: !usuario.puede_exportar });
      cargar();
    } catch (err) {
      setError(mensajeError(err));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Title className="text-ink">Usuarios</Title>
        <Text className="text-ink-muted">Crear, desactivar y cambiar el rol de las cuentas.</Text>
      </div>

      <Card className="bg-surface ring-1 ring-line">
        <Title className="mb-3 text-ink">Nuevo usuario</Title>
        <form onSubmit={handleCrear} className="flex flex-wrap items-end gap-3">
          <div>
            <Text className="mb-1 text-xs text-ink-muted">Usuario</Text>
            <TextInput value={nombreUsuario} onValueChange={setNombreUsuario} required className="w-40" />
          </div>
          <div>
            <Text className="mb-1 text-xs text-ink-muted">Contraseña</Text>
            <TextInput type="password" value={password} onValueChange={setPassword} required className="w-40" />
          </div>
          <div>
            <Text className="mb-1 text-xs text-ink-muted">Nombre completo</Text>
            <TextInput value={nombreCompleto} onValueChange={setNombreCompleto} className="w-48" />
          </div>
          <div>
            <Text className="mb-1 text-xs text-ink-muted">Rol</Text>
            <Select value={rol} onValueChange={(v) => setRol(v as Rol)} className="w-48">
              <SelectItem value="Usuario">Usuario</SelectItem>
              {puedeAsignarRolesDeAdministracion && (
                <SelectItem value="Administrador">Administrador</SelectItem>
              )}
              {puedeAsignarRolesDeAdministracion && (
                <SelectItem value="Administrador de Usuarios">Administrador de Usuarios</SelectItem>
              )}
            </Select>
          </div>
          <label className="flex items-center gap-2 pb-2 text-sm text-ink-muted">
            <input
              type="checkbox"
              checked={puedeExportar}
              onChange={(e) => setPuedeExportar(e.target.checked)}
              className="h-4 w-4 rounded border-line-strong bg-surface-hover text-teal-500 focus:ring-teal-500"
            />
            Puede exportar a Excel
          </label>
          <Button type="submit" loading={creando} disabled={creando || !nombreUsuario || !password}>
            Crear usuario
          </Button>
        </form>
        {errorForm && (
          <p role="alert" className="mt-3 rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">
            {errorForm}
          </p>
        )}
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      <Card className="bg-surface ring-1 ring-line">
        {cargando ? (
          <p className="text-sm text-ink-muted">Cargando…</p>
        ) : (
          <SimpleDataTable
            columnas={[
              { header: "Usuario", accessor: (r: UsuarioOut) => r.nombre_usuario },
              { header: "Nombre completo", accessor: (r: UsuarioOut) => r.nombre_completo ?? "—" },
              {
                header: "Rol",
                accessor: (r: UsuarioOut) => (
                  <Select
                    value={r.rol}
                    onValueChange={(v) => cambiarRol(r, v as Rol)}
                    className="w-48"
                  >
                    <SelectItem value="Usuario">Usuario</SelectItem>
                    {puedeAsignarRolesDeAdministracion && (
                      <SelectItem value="Administrador">Administrador</SelectItem>
                    )}
                    {puedeAsignarRolesDeAdministracion && (
                      <SelectItem value="Administrador de Usuarios">Administrador de Usuarios</SelectItem>
                    )}
                  </Select>
                ),
              },
              {
                header: "Estado",
                accessor: (r: UsuarioOut) => (
                  <Badge color={r.activo ? "emerald" : "slate"}>{r.activo ? "Activo" : "Inactivo"}</Badge>
                ),
              },
              {
                header: "Exportar",
                accessor: (r: UsuarioOut) => (
                  <label className="flex items-center gap-2 text-xs text-ink-muted">
                    <input
                      type="checkbox"
                      checked={r.puede_exportar}
                      onChange={() => alternarPuedeExportar(r)}
                      className="h-4 w-4 rounded border-line-strong bg-surface-hover text-teal-500 focus:ring-teal-500"
                    />
                    {r.puede_exportar ? "Sí" : "No"}
                  </label>
                ),
              },
              {
                header: "Último login",
                accessor: (r: UsuarioOut) => (r.ultimo_login ? new Date(r.ultimo_login).toLocaleString("es-GT") : "—"),
              },
              {
                header: "Contraseña",
                accessor: (r: UsuarioOut) =>
                  editandoPasswordId === r.usuario_id ? (
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <TextInput
                          type="password"
                          value={nuevaPassword}
                          onValueChange={setNuevaPassword}
                          placeholder="Nueva contraseña"
                          className="w-36"
                        />
                        <Button
                          size="xs"
                          loading={guardandoPassword}
                          disabled={guardandoPassword || !nuevaPassword}
                          onClick={() => guardarNuevaPassword(r.usuario_id)}
                        >
                          Guardar
                        </Button>
                        <button
                          type="button"
                          onClick={cancelarCambioPassword}
                          className="text-xs text-ink-muted hover:text-ink"
                        >
                          Cancelar
                        </button>
                      </div>
                      {errorPassword && <p className="text-xs text-danger">{errorPassword}</p>}
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => iniciarCambioPassword(r)}
                      className="text-xs font-medium text-teal-400 hover:text-teal-300"
                    >
                      Cambiar contraseña
                    </button>
                  ),
              },
              {
                header: "",
                accessor: (r: UsuarioOut) =>
                  r.usuario_id === sesion?.usuarioId ? (
                    <span className="text-xs text-ink-faint">Tu cuenta</span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => alternarActivo(r)}
                      className="text-xs font-medium text-teal-400 hover:text-teal-300"
                    >
                      {r.activo ? "Desactivar" : "Activar"}
                    </button>
                  ),
              },
            ]}
            filas={usuarios}
            getKey={(r) => r.usuario_id}
          />
        )}
      </Card>
    </div>
  );
}

import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireRole, RequireModulo, destinoPorRol } from "./auth/RequireRole";
import { ThemeProvider } from "./theme/ThemeContext";
import { LoginPage } from "./pages/LoginPage";
import { AppLayout } from "./pages/app/AppLayout";
import { DashboardPlaguicidasPage } from "./pages/app/DashboardPlaguicidasPage";
import { DashboardNutrientesPage } from "./pages/app/DashboardNutrientesPage";
import { DashboardFinancieroPage } from "./pages/app/DashboardFinancieroPage";
import { DashboardOtrosInformesPage } from "./pages/app/DashboardOtrosInformesPage";
import { DashboardPresupuestosPage } from "./pages/app/DashboardPresupuestosPage";
import { DashboardImportacionesFinancieroPage } from "./pages/app/DashboardImportacionesFinancieroPage";
import { DashboardOtroIngresoPage } from "./pages/app/DashboardOtroIngresoPage";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { CargaPlaguicidasPage } from "./pages/admin/CargaPlaguicidasPage";
import { CargaNutrientesPage } from "./pages/admin/CargaNutrientesPage";
import { CargaSaldoBancarioPage } from "./pages/admin/CargaSaldoBancarioPage";
import { CargaOtroIngresoPage } from "./pages/admin/CargaOtroIngresoPage";
import { NomenclaturaPlaguicidasPage } from "./pages/admin/NomenclaturaPlaguicidasPage";
import { AgrupadorNutrientesPage } from "./pages/admin/AgrupadorNutrientesPage";
import { UsuariosPage } from "./pages/admin/UsuariosPage";

function InicioRedirect() {
  const { sesion } = useAuth();
  if (!sesion) return <Navigate to="/login" replace />;
  return <Navigate to={destinoPorRol(sesion.rol)} replace />;
}

function AdminIndexRedirect() {
  const { sesion } = useAuth();
  const destino = sesion?.rol === "Administrador de Usuarios" ? "usuarios" : "cargas/plaguicidas";
  return <Navigate to={destino} replace />;
}

/** Destino de /app (index): el primer módulo al que el usuario SÍ tiene
 * acceso -- antes era un <Navigate to="plaguicidas"> fijo, que para un
 * usuario sin Importaciones entraba en loop con RequireModulo (rebota a
 * /app, que vuelve a mandarlo a plaguicidas, que vuelve a rebotar...).
 * Si no tiene acceso a NINGÚN módulo, se queda en una pantalla neutra
 * (no nombra ningún módulo, no es un rebote hacia una ruta que lo
 * volvería a mandar aquí). */
function AppIndexRedirect() {
  const { sesion } = useAuth();
  if (sesion?.accesoImportaciones) return <Navigate to="plaguicidas" replace />;
  if (sesion?.accesoFinanciero) return <Navigate to="financiero" replace />;
  return <p className="p-6 text-sm text-ink-muted">No tiene acceso a ningún módulo.</p>;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<InicioRedirect />} />
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/app"
            element={
              <RequireRole roles={["Administrador", "Usuario", "Administrador de Usuarios"]}>
                <AppLayout />
              </RequireRole>
            }
          >
            <Route index element={<AppIndexRedirect />} />
            <Route
              path="plaguicidas"
              element={
                <RequireModulo modulo="importaciones">
                  <DashboardPlaguicidasPage />
                </RequireModulo>
              }
            />
            <Route
              path="nutrientes"
              element={
                <RequireModulo modulo="importaciones">
                  <DashboardNutrientesPage />
                </RequireModulo>
              }
            />
            <Route
              path="financiero"
              element={
                <RequireModulo modulo="financiero">
                  <DashboardFinancieroPage />
                </RequireModulo>
              }
            />
            <Route
              path="financiero/otros-informes"
              element={
                <RequireModulo modulo="financiero">
                  <DashboardOtrosInformesPage />
                </RequireModulo>
              }
            />
            <Route
              path="financiero/presupuestos"
              element={
                <RequireModulo modulo="financiero">
                  <DashboardPresupuestosPage />
                </RequireModulo>
              }
            />
            <Route
              path="financiero/importaciones"
              element={
                <RequireModulo modulo="financiero">
                  <DashboardImportacionesFinancieroPage />
                </RequireModulo>
              }
            />
            <Route
              path="financiero/otros-ingresos"
              element={
                <RequireModulo modulo="financiero">
                  <DashboardOtroIngresoPage />
                </RequireModulo>
              }
            />
          </Route>

          <Route
            path="/admin"
            element={
              <RequireRole roles={["Administrador", "Administrador de Usuarios"]}>
                <AdminLayout />
              </RequireRole>
            }
          >
            <Route index element={<AdminIndexRedirect />} />
            {/* Carga/Nomenclatura: exclusivas de "Administrador" — "Administrador
                de Usuarios" solo entra a /admin para usar Usuarios. Un enlace
                directo a estas rutas debe rebotar, no solo estar oculto del menú. */}
            <Route
              path="cargas/plaguicidas"
              element={
                <RequireRole roles={["Administrador"]}>
                  <CargaPlaguicidasPage />
                </RequireRole>
              }
            />
            <Route
              path="cargas/nutrientes"
              element={
                <RequireRole roles={["Administrador"]}>
                  <CargaNutrientesPage />
                </RequireRole>
              }
            />
            <Route
              path="nomenclatura/plaguicidas"
              element={
                <RequireRole roles={["Administrador"]}>
                  <NomenclaturaPlaguicidasPage />
                </RequireRole>
              }
            />
            <Route
              path="nomenclatura/nutrientes"
              element={
                <RequireRole roles={["Administrador"]}>
                  <AgrupadorNutrientesPage />
                </RequireRole>
              }
            />
            <Route
              path="cargas/saldos-bancarios"
              element={
                <RequireRole roles={["Administrador"]}>
                  <CargaSaldoBancarioPage />
                </RequireRole>
              }
            />
            <Route
              path="cargas/otros-ingresos"
              element={
                <RequireRole roles={["Administrador"]}>
                  <CargaOtroIngresoPage />
                </RequireRole>
              }
            />
            <Route path="usuarios" element={<UsuariosPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  );
}

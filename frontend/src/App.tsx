import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireRole, destinoPorRol } from "./auth/RequireRole";
import { ThemeProvider } from "./theme/ThemeContext";
import { LoginPage } from "./pages/LoginPage";
import { AppLayout } from "./pages/app/AppLayout";
import { DashboardPlaguicidasPage } from "./pages/app/DashboardPlaguicidasPage";
import { DashboardNutrientesPage } from "./pages/app/DashboardNutrientesPage";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { CargaPlaguicidasPage } from "./pages/admin/CargaPlaguicidasPage";
import { CargaNutrientesPage } from "./pages/admin/CargaNutrientesPage";
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
            <Route index element={<Navigate to="plaguicidas" replace />} />
            <Route path="plaguicidas" element={<DashboardPlaguicidasPage />} />
            <Route path="nutrientes" element={<DashboardNutrientesPage />} />
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
            <Route path="usuarios" element={<UsuariosPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  );
}

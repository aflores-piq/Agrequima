import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireRole } from "./auth/RequireRole";
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
import { ExcepcionesPage } from "./pages/admin/ExcepcionesPage";
import { UsuariosPage } from "./pages/admin/UsuariosPage";

function InicioRedirect() {
  const { sesion } = useAuth();
  if (!sesion) return <Navigate to="/login" replace />;
  return <Navigate to={sesion.rol === "Administrador" ? "/admin" : "/app"} replace />;
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
              <RequireRole roles={["Administrador", "Usuario"]}>
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
              <RequireRole roles={["Administrador"]}>
                <AdminLayout />
              </RequireRole>
            }
          >
            <Route index element={<Navigate to="cargas/plaguicidas" replace />} />
            <Route path="cargas/plaguicidas" element={<CargaPlaguicidasPage />} />
            <Route path="cargas/nutrientes" element={<CargaNutrientesPage />} />
            <Route path="nomenclatura/plaguicidas" element={<NomenclaturaPlaguicidasPage />} />
            <Route path="nomenclatura/nutrientes" element={<AgrupadorNutrientesPage />} />
            <Route path="excepciones" element={<ExcepcionesPage />} />
            <Route path="usuarios" element={<UsuariosPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  );
}

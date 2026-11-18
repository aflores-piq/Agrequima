import { useState } from "react";
import { Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { AccountMenu } from "../components/layout/AccountMenu";
import { CampanaAvisos } from "../components/layout/CampanaAvisos";
import { CopilotoPanel } from "./CopilotoPanel";
import type { Pestana } from "./CopilotoPanel";
import { IndicadoresSidebar } from "./IndicadoresSidebar";
import { Icono } from "./iconos";
import "./indicadores.css";

const CLAVE_LATERAL = "indicadores_lateral_cerrada";
const CLAVE_COPILOTO = "indicadores_copiloto_abierto";

function leerBandera(clave: string, porDefecto: boolean): boolean {
  try {
    const v = localStorage.getItem(clave);
    return v === null ? porDefecto : v === "1";
  } catch {
    return porDefecto;
  }
}

function guardarBandera(clave: string, valor: boolean): void {
  try {
    localStorage.setItem(clave, valor ? "1" : "0");
  } catch {
    /* sin almacenamiento: la preferencia solo vale en esta sesión */
  }
}

/** Marco del módulo Indicadores (solo rutas /app/indicadores*): barra lateral azul marino colapsable, barra superior con la
 * campanita y el usuario y, SOLO para el rol Administrador, la tarjeta «Potencia tus análisis con IA» y el panel
 * «Copiloto PronostiQ» (solo interfaz). Importaciones y Financiero siguen con su propio AppLayout. */
export function IndicadoresLayout() {
  const { sesion } = useAuth();
  const esAdministrador = sesion?.rol === "Administrador";
  const [cerrada, setCerrada] = useState(() => leerBandera(CLAVE_LATERAL, false));
  const [copilotoAbierto, setCopilotoAbierto] = useState(() => leerBandera(CLAVE_COPILOTO, true));
  const [pestana, setPestana] = useState<Pestana>("chat");

  function alternarLateral() {
    setCerrada((v) => {
      guardarBandera(CLAVE_LATERAL, !v);
      return !v;
    });
  }

  function fijarCopiloto(abierto: boolean) {
    setCopilotoAbierto(abierto);
    guardarBandera(CLAVE_COPILOTO, abierto);
  }

  const nombre = sesion?.nombreCompleto || sesion?.nombreUsuario || "";

  return (
    <div className="ind-root">
      <IndicadoresSidebar
        cerrada={cerrada}
        mostrarIa={esAdministrador}
        onVerEjemplos={() => {
          setPestana("sugerencias");
          fijarCopiloto(true);
        }}
      />
      <div className="ind-main">
        <header className="ind-top">
          <button type="button" className="ind-btn" onClick={alternarLateral} aria-label={cerrada ? "Abrir la barra lateral" : "Cerrar la barra lateral"} title={cerrada ? "Abrir la barra lateral" : "Cerrar la barra lateral"}>
            <Icono nombre="menu" tam={22} />
          </button>
          <div className="espacio" />
          {esAdministrador && (
            <button
              type="button"
              className={`ind-btn${copilotoAbierto ? " activo" : ""}`}
              onClick={() => fijarCopiloto(!copilotoAbierto)}
              aria-pressed={copilotoAbierto}
              title={copilotoAbierto ? "Cerrar el Copiloto" : "Abrir el Copiloto"}
            >
              <Icono nombre="chispas" tam={20} />
              Copiloto
            </button>
          )}
          <CampanaAvisos />
          <AccountMenu />
        </header>
        <div className="ind-cuerpo">
          <Outlet />
          {esAdministrador && copilotoAbierto && (
            <CopilotoPanel nombre={nombre} pestana={pestana} onPestana={setPestana} onCerrar={() => fijarCopiloto(false)} />
          )}
        </div>
      </div>
    </div>
  );
}

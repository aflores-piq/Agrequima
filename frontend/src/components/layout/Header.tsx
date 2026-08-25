import type { ReactNode } from "react";
import pronostiqIcono from "../../assets/pronostiq-icono.png";
import pronostiqTexto from "../../assets/pronostiq-texto.png";
import agrequimaLogo from "../../assets/agrequima-logo.png";
import { AccountMenu } from "./AccountMenu";

/** Encabezado estándar de PronostiQ (mismo patrón que otros sistemas de
 * Pronostiq, ver docs/legacy/branding/): marca de la plataforma a la
 * izquierda (fija, siempre igual), logo del cliente (Agrequima), el
 * slot de navegación propio de cada layout al centro/derecha, y el
 * menú de cuenta al final. Reemplaza los headers ad-hoc que tenían
 * AppLayout y AdminLayout. */
export function Header({ nav }: { nav?: ReactNode }) {
  return (
    <header className="border-b border-line bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
        <div className="flex items-center gap-3">
          <img src={pronostiqIcono} alt="" className="h-8 w-auto shrink-0" />
          <div className="hidden flex-col leading-tight sm:flex">
            <img src={pronostiqTexto} alt="PronostiQ" className="h-4 w-auto" />
            <p className="mt-0.5 text-[10px] font-medium text-ink-faint">Business Intelligence Platform</p>
          </div>
        </div>

        {nav}

        <div className="flex items-center gap-4">
          <img src={agrequimaLogo} alt="Agrequima" className="h-10 w-auto shrink-0" />
          <AccountMenu />
        </div>
      </div>
    </header>
  );
}

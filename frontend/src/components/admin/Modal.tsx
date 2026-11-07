import { useEffect } from "react";
import type { ReactNode } from "react";
import { Card, Title } from "@tremor/react";

/** Ventana modal simple: se cierra con Esc o al hacer clic fuera. */
export function Modal({
  titulo,
  onCerrar,
  children,
}: {
  titulo: string;
  onCerrar: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCerrar();
    };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [onCerrar]);

  return (
    <div
      className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 px-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onCerrar();
      }}
    >
      <Card role="dialog" aria-label={titulo} className="max-h-[90vh] w-full max-w-lg overflow-y-auto bg-surface ring-1 ring-line">
        <Title className="mb-3 text-ink">{titulo}</Title>
        {children}
      </Card>
    </div>
  );
}


export function ErrorBox({ texto }: { texto: string | null }) {
  if (!texto) return null;
  return (
    <p role="alert" className="mt-3 rounded-tremor-small bg-danger-surface px-3 py-2 text-sm text-danger">
      {texto}
    </p>
  );
}

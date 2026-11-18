import { useEffect, useRef, useState } from "react";

/** Ancho y alto reales (px) de un elemento, para dibujar las gráficas SVG en píxeles reales (letras del tamaño exacto). */
export function useMedida<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [medida, setMedida] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const leer = () => {
      const r = el.getBoundingClientRect();
      setMedida((anterior) => {
        const w = Math.round(r.width);
        const h = Math.round(r.height);
        return anterior.w === w && anterior.h === h ? anterior : { w, h };
      });
    };
    leer();
    const obs = new ResizeObserver(leer);
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return { ref, ...medida };
}

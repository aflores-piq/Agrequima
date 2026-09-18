# Medidas reales confirmadas — Módulo Financiero

Registro vivo de medidas verificadas con captura/computedStyle real en el
navegador (no supuestos). Cada sección indica cuándo y cómo se confirmó.
Referenciado desde comentarios en el código (`TablaGrupoExpandible.tsx`,
`DashboardFinancieroPage.tsx`, etc.) — mantenerlo actualizado cuando una
medida cambie.

## 0. Imágenes de referencia reales

Las 5 capturas del reporte de Power BI original están dentro de
`docs/legacy/Financiero_capturas/Capturas_PowerBI.docx` (un .docx, no
.png sueltos) -- `image1`=portada/menú, `image2`=página 1 (Ingresos
mensual), `image3`=página 2 (Ingresos acumulado), `image4`=página 3
(Balance mensual), `image5`=página 4 (Balance comparativo). Para
inspeccionarlas: descomprimir el .docx como zip y mirar `word/media/`.

## 10. Etiquetas de las tarjetas KPI (color y alineación)

Medido pixel a pixel sobre `image2`/`image3`/`image4`/`image5`: el
trazo sólido del texto de la etiqueta ("Ingresos", "Activo", el título
de 2 líneas de la tarjeta comparativa) es **rgb(68,149,208) = #4495D0**,
un azul -- NO blanco ni gris (se había pedido "blanco" pero la
referencia real es este azul, consistente en las 4 páginas). El VALOR
(monto) sí es blanco/`text-ink`, sin cambios.

Alineación: páginas 1-3 con `items-end`; página 4 con `text-center`
(título, porcentaje y monto centrados, confirmado con el centro del
texto = centro del contenedor, diferencia 0px).

**[BUG ENCONTRADO Y CORREGIDO]** La primera vez que se aplicó
`items-end` en `KpiCardIcono` (páginas 1-3) pareció funcionar porque
`label.right === valor.right` -- pero esa comparación NO prueba nada
por sí sola: el div de contenido (`<div className="flex flex-col
items-end ...">`) no tenía `flex-1`, así que quedaba del ancho de su
propio contenido (~78px) y flotaba pegado al cuadrito de color, dejando
un hueco vacío de hasta **139.6px** antes del borde real de la
tarjeta (medido a 1794px de viewport). `items-end` alineaba la
etiqueta y el valor entre sí dentro de esa caja angosta -- que es
trivialmente cierto siempre, sin importar dónde esté la caja -- pero
NO contra el borde derecho real de la tarjeta, que es lo que se pedía.
Esto pasó las verificaciones anteriores (que solo comparaban
`label.right` contra `valor.right`) sin detectarlo.

Fix real: agregado `flex-1 min-w-0` al div de contenido, para que
ocupe todo el ancho restante de la tarjeta (después del cuadrito de
color) y `items-end` empuje el texto contra el borde derecho
VERDADERO. Verificado con la prueba correcta -- `cardRight -
labelRight` y `cardRight - valorRight` -- que debe dar el padding
esperado (`px-4` = 16px), no un número arbitrario:

| Página | Tarjeta | cardRight − labelRight | cardRight − valorRight |
|---|---|---|---|
| 1 | Ingresos | 16px | 16px |
| 1 | Egresos | 16px | 16px |
| 1 | Resultado | 16px | 16px |
| 2 | Ingresos | 16px | 16px |
| 2 | Egresos | 16px | 16px |
| 2 | Saldo | 16px | 16px |
| 3 | Activo | 16px | 16px |
| 3 | Pasivo | 16px | 16px |
| 3 | Patrimonio | 16px | 16px |

Las 9 tarjetas dan exactamente 16px (el padding real, no un hueco
espurio) en las 3 páginas. Página 4 (`KpiCardIconoComparativo`) ya
tenía `flex-1 min-w-0` desde antes -- por eso nunca tuvo este bug y no
se tocó.

## 11. Fondo único en las 4 páginas

Página 1 tenía un override propio (`AZUL_OSCURO_PAGINA1`, `#1e293b`) de
una ronda anterior -- eliminado por completo. Las 4 páginas usan
`FINANCIERO_SURFACE` sin excepciones. Confirmado:
`getComputedStyle(tarjeta).backgroundColor` = `rgb(68, 68, 68)` en las
4 páginas, en modo oscuro.

## 12. Tamaño de las tarjetas KPI de página 4

La tarjeta comparativa (`KpiCardIconoComparativo`) medía 315×101px
(`aspect-[3.125/1]`) -- visiblemente más grande que en la captura real,
aunque la PROPORCIÓN ancho de fila / ancho de tabla (59.6%/55%=1.084)
ya coincidía con la de la referencia (531px/490px=1.084, medido en
`image5`). La causa: el ancho fijo del contenido de Financiero en la
app (1658px) es más ancho que el lienzo nativo de Power BI (~1032px en
la captura), así que igualar el % no igualaba el tamaño ABSOLUTO.

Se usó el alto de la barra verde de encabezado (36px en la app, 25px en
`image5`) como referencia de escala independiente de la resolución: la
tarjeta mide 56px en `image5` → ratio card/header = 56/25 = 2.24.
Ajustado `aspect-[3.125/1]` → `aspect-[3.6/1]` y el ancho de la fila de
59.6% → 57% (mx-auto, se sacó el offset asimétrico `ml-[19.9%]` que ya
no hacía falta con un ancho más chico): tarjeta ahora mide 300.9×83.6px,
ratio card/header = 83.6/36 = **2.32** (vs. 2.24 target, dentro de ~4%).
Sigue siendo más grande que las tarjetas simples de páginas 1-3 (72.5px
de alto en página 1) -- confirmado.

Fuente de fila (57%) sigue siendo más ancha que la tabla (55%, ratio
1.036) -- confirmado con `getBoundingClientRect()`.

Fuentes de la tarjeta reducidas (ajuste moderado, no drástico): título
de `text-xs` (12px) a `text-[11px]`; porcentaje de `text-xl` (20px) a
`text-lg` (18px). Monto sin cambios (18px, bold).

## 1. Paleta de color (rutas /app/financiero/* únicamente)

Tokens propios de Financiero (`--color-financiero-app`, `--color-financiero-surface`,
ver `index.css`), independientes de los tokens generales (`--color-bg-app`,
`--color-bg-surface`) que sigue usando Plaguicidas/Nutrientes sin cambios.

| Token | Claro | Oscuro |
|---|---|---|
| `--color-financiero-app` (fondo principal) | `#f8fafc` (= bg-app claro) | `#1c1c1c` |
| `--color-financiero-surface` (tarjetas/tablas/paneles) | `#ffffff` (= bg-surface claro) | `#444444` |

Confirmado con `getComputedStyle(...).backgroundColor` en ambos modos:
oscuro → `rgb(28, 28, 28)` / `rgb(68, 68, 68)`; claro → `rgb(248, 250, 252)`
/ `rgb(255, 255, 255)`.

El menú lateral (`Sidebar.tsx`) usa `#444444` fijo (NO reactivo al tema,
es chrome de navegación compartida con Importaciones) — confirmado
`rgb(68, 68, 68)` en ambos modos.

## 2. Modo claro reactivo

`FINANCIERO_SURFACE` (antes hex fijo `#1e293b`) ahora es
`rgb(var(--color-financiero-surface))` — reactivo. Todo lo que lo usa
(KpiCardIcono, KpiCardIconoComparativo, tbody de TablaGrupoExpandible,
ChartCard `estiloTarjeta`, tooltip de BalanceDonut) cambia correctamente
entre claro/oscuro. Colores de texto/ejes que antes eran `#ffffff` fijo
(ejes y etiquetas de los 3 gráficos de barra, texto central de la dona)
pasaron a `rgb(var(--color-ink))` — confirmado con contraste correcto en
ambos modos.

## 3. Alto de banda verde de resumen ("Resultado del ejercicio" / "Total pasivo y patrimonio")

Debe medir EXACTAMENTE lo mismo que la fila de encabezado verde normal
(mismo padding de celda `px-3 py-2`, sin leyenda de columnas repetida
debajo). Confirmado con `getBoundingClientRect().height` en las 4
páginas: encabezado = banda = **36px** siempre.

## 4. Dona de Balance (página 3) — 4 categorías

Activo = Pasivo + Patrimonio + Fondos por aplicar (identidad contable) →
su porción mide exactamente 50% del anillo, sin forzar ángulos. Colores
(medidos de la captura real de Power BI):

| Etiqueta | Color |
|---|---|
| Patrimonio | `#375B7D` |
| Pasivo | `#E87471` |
| Fondos por aplicar | `#35B0A2` |
| Activo | `#3F6F6B` |

Orden de leyenda: Patrimonio, Pasivo, Fondos por aplicar, Activo.
Confirmado con los 4 `<path>` del `recharts-pie` y el texto de cada
`<li>` de la leyenda — porcentajes: 17.1% / 12.3% / 20.6% / 50.0%
(suman 100%, los primeros 3 suman el 50% restante).

## 5. Alto de panel de gráfico — 380px en las 4 páginas

`ALTURA_PANEL_COMPLETO = 380` (constante en `DashboardFinancieroPage.tsx`),
`altura` real pasada a los componentes de gráfico = `380 - 92` (overhead
fijo de título+padding de ChartCard) = 288. Confirmado con
`getBoundingClientRect().height` del `Card` que envuelve cada gráfico:
**380px exacto en las 4 páginas** (Ingresos mensual, Ingresos acumulado,
Balance mensual con dona, Balance comparativo). Anillo de la dona =
242px = 84% de 288 (fórmula sin cambios: `diametro = altura * 0.84`).

## 6. Etiquetas de valor dentro de las barras

Tamaño aumentado de 9-10px a **14px** (TresBarrasResultado, páginas 1) y
**13px** (ComparativoAnioBarChart, páginas 2 y 4), `font-weight: 600`,
color reactivo (`rgb(var(--color-ink))`). Margen superior del gráfico
subido de 20 a 28px para que la etiqueta no se corte contra el borde del
panel. Confirmado sin recorte (`label.top > svg.top` en las 4 páginas)
y sin superposición entre etiquetas de las 2 series (páginas 2/4).

## 7. Título principal

**[ACTUALIZADO]** Subido de `text-xl` (20px) a `text-3xl` (30px) -- se
veía como miniatura comparado con el título real de Power BI, pese a
que cumplía el ratio ~77% vs. la barra verde que se había confirmado en
una ronda anterior (ese ratio quedó obsoleto con este cambio). Sigue
centrado (diferencia entre el centro del título y el centro del
contenedor de contenido = 0px, confirmado con `getBoundingClientRect()`).

## 9. Ancho único de tabla (y KPI en páginas 1-3)

**Antes** (cada página con su propio %, medido con `table.closest('.ring-1.ring-line')`
a 1794px de viewport de contenido):

| Página | Tabla (antes) | KPI (antes) |
|---|---|---|
| 1 — Ingresos mensual | 910.55px (56%) | 910.55px (mismo wrapper) |
| 2 — Ingresos acumulado | 926.81px (57%) | 926.81px (mismo wrapper) |
| 3 — Balance mensual | 894.30px (55%) | 919.83px (56.57%, wrapper propio) |
| 4 — Balance comparativo | 894.30px (55%) | 969.09px (59.6% asimétrico -- excluida de la regla) |

**Después** (constante única `ANCHO_TABLA_FINANCIERO = "55%"` en
`DashboardFinancieroPage.tsx`, aplicada vía `style={{width}}` -- no
`className` arbitraria, porque Tailwind no genera una clase `w-[...]`
interpolada en runtime desde una sola constante):

| Página | Tabla (después) | KPI (después) |
|---|---|---|
| 1 | 894.30px | 894.30px (mismo wrapper) |
| 2 | 894.30px | 894.30px (mismo wrapper) |
| 3 | 894.30px | 894.30px (wrapper fusionado con la tabla) |
| 4 | 894.30px | 969.09px (sin cambios, excluida a propósito) |

Las 4 tablas miden **894.30px, diferencia cero** entre sí. El valor
55% se eligió por ser el que ya compartían 2 de las 4 páginas (3 y 4);
no es una nueva medida del .pbix, es una reconciliación explícita
pedida en esta ronda.

## 8. Slicer "Año y Mes" — alineado con la fila de KPIs

Reposicionado: en vez de centrado verticalmente en la barra angosta del
título (`top-1/2` de un `min-h-[64px]`, quedaba flotando muy arriba,
desalineado), ahora ancla su borde superior al mismo punto donde arranca
la fila de KPIs (`top-full mt-5` relativo al contenedor del título, que
coincide con el `gap-5` del `space-y-5` que envuelve todo). Confirmado
con `getBoundingClientRect().top`: filtro y fila de KPIs empiezan en la
MISMA coordenada Y en las 4 páginas (sin superposición horizontal, el
filtro queda a la derecha del contenido, la fila de KPIs centrada).

## Cajas/tarjetas ya cerradas en rondas anteriores (sin cambios esta ronda)

- KPI simple (`KpiCardIcono`, páginas 1-3): `aspect-[4/1]` (ratio 0.25).
- KPI comparativa (`KpiCardIconoComparativo`, página 4): `aspect-[3.125/1]`
  (ratio 0.32), 315×101px medido a 1794px de viewport de contenido.
  Letra ("A") = 42.7% del alto del cuadrado (target 40-45%), porcentaje
  `font-normal leading-tight`, monto `font-bold leading-none`, divisor
  `border-t` sin superposición (4px de margen a cada lado).
- Anchos de tabla/KPI por página: p1 56%, p2 57%, p3 56.57%(KPI)/55%(tabla),
  p4 KPI `ml-[19.9%] w-[59.6%]` (asimétrico) / tabla 55%.
- Anchos de gráfico: p1 ~48% c/u (2 gráficos), p2 52%, p3 (dona) 47%, p4 52%.

# Bitácora — Módulo Financiero

Registro vivo de decisiones de arquitectura, fuentes de datos y números de
control validados contra el `.pbix` original, pantalla por pantalla.
Referenciado desde comentarios en el código (por ejemplo
`cargar_datos_financiero_inicial.py`) — mantenerlo actualizado cuando se
agregue o corrija una pantalla del módulo Financiero.

## Conciliación bancaria / Flujo de caja (2026-09)

### Qué son y de dónde sale cada dato

**Conciliación bancaria**: por cada banco (BAC/BANCOR, BANRURAL, BI,
PROMÉRICA) muestra 5 filas — Saldo inicial, (+) Créditos, (−) Débitos,
(−) Documentos en Circulación, Totales — en dos columnas paralelas:
"Saldo Banco" (lo que reporta el banco) y "Saldo Contabilidad" (lo que
dice CONTACC).

- **Columna "Saldo Contabilidad"** ← `dbo.SaldosBancos`, cargada desde
  `vw_piq_saldos_bancos.csv` (vista de CONTACC). Es el lado CONTABLE.
- **Columna "Saldo Banco"** ← `dbo.SaldoBancario`, cargada desde
  `SaldoBancario.csv` (export directo de `Agrequima.dbo.SaldoBancario`,
  servidor real **10.10.0.6,65280**), con conceptos `Saldo inicial` /
  `Creditos` / `Debitos` por banco/mes. Es el lado BANCO real.
- **Documentos en Circulación** ← `dbo.ChequesCirculacion` (ya existía).
- El cruce BANCOR↔BAC se hace por coincidencia numérica exacta de
  Entradas/Salidas contra Débitos/Créditos de `BalanceGeneral` para
  Agosto 2026 (no por texto — `BANCOR` es el código informal de la
  cuenta formal "BAC 701111600 MONETARIA").

**Flujo de caja**: Caja + 4 bancos (saldo de `SaldosBancos`, FinalL del
mes) − Cheques en circulación (mismos totales de `ChequesCirculacion`
que en Conciliación) = Disponibilidad en depósitos, + Inversión Plazo
Fijo BAC + Inversión Plazo Fijo Promérica (ambas de `BalanceGeneral`,
YTD dentro del año) = Disponibilidad final.

### Números de control — Agosto 2026 (validados contra el .pbix)

**Conciliación bancaria** (Totales por banco, banco vs. contabilidad):

| Banco | Saldo Banco | Saldo Contabilidad |
|---|---|---|
| BAC (BANCOR) | Q3,061,395.55 | Q3,061,395.55 |
| BANRURAL | Q289,458.48 | Q289,458.64 |
| BI | Q41,349.17 | Q41,349.17 |
| PROMÉRICA | Q70,399.55 | Q70,399.55 |

(BANRURAL tiene una diferencia de Q0.16 entre banco y contabilidad —
confirmado que es real, no un bug: existe también en el `.pbix` de
referencia.)

**Flujo de caja**:

| Concepto | Valor |
|---|---|
| Caja y Caja Chica | Q1,200 |
| Banrural | Q289,459 |
| Banco Industrial | Q41,349 |
| BAC Reformador | Q3,061,396 |
| Promerica | Q70,400 |
| Total bancos | Q3,463,803 |
| (−) Cheques en circulación (Banrural Q4,000 + BAC Q19,250) | Q23,250 |
| Disponibilidad en depósitos monetarios y caja | Q3,463,803 |
| (+) Inversiones Plazo Fijo BAC | Q2,300,001 |
| (+) Inversiones Plazo Fijo Promérica | Q1,500,000 |
| **Disponibilidad al 31 de Agosto de 2026** | **Q7,263,804** |

Nota: "Disponibilidad en depósitos monetarios y caja" **no** resta los
cheques en circulación de "Total bancos" — así lo muestra el `.pbix`
real (el descuento de cheques ya quedó reflejado en la fila de
Conciliación, no se vuelve a restar acá); confirmado exacto contra el
control del cliente, no es un error de la implementación.

### Correcciones importantes de este ciclo

1. **El `.pbix` SÍ trae el modelo completo**, no solo el layout: es un
   `.pbix` con datos importados (no live-connection tal como se pensó al
   principio de la investigación). Con `pbixray` se puede leer el
   `DataModel` completo — tablas, medidas DAX y pasos de Power Query —
   y `Report/Layout` trae la posición y el tamaño exactos (x/y/width/
   height en píxeles) de cada visual de cada página.
2. **`dbo.SaldosBancos`** (cargada desde `vw_piq_saldos_bancos.csv`, una
   vista de CONTACC) es el lado **CONTABLE** de la conciliación — no el
   saldo que reporta el banco.
3. **"Saldo Banco"** (el lado banco real de la conciliación) sale de
   **`Agrequima.dbo.SaldoBancario`**, servidor **10.10.0.6,65280**, con
   los conceptos `Saldo inicial` / `Creditos` / `Debitos` por banco/mes.

### Fórmulas reales usadas

- **Cheques en circulación** (a una fecha de corte): 
  ```sql
  doc_fecha <= fin_de_mes
  AND (doc_fchcobro IS NULL OR doc_fchcobro > fin_de_mes)
  ```
  (outstanding real a cierre de período — no agrupa por el mes de
  emisión del cheque, es histórico completo filtrado por la fecha de
  corte.)
- **Caja** ← `BalanceGeneral`, cuenta `110101001`, YTD dentro del año
  (`Sal_Ano = :anio AND Sal_Mes <= :mes`).
- **Inversión BAC** ← `BalanceGeneral`, cuenta `110103003`, mismo YTD.
- **Inversión Promérica** ← `BalanceGeneral`, cuenta `110103004`, mismo
  YTD.
- **Totales Saldo Banco** (por banco) = Saldo inicial + Créditos −
  Débitos − Documentos en Circulación.

### Regla para próximas pantallas (anchos y posiciones)

Sacar anchos y posiciones de cada visual directamente de `Report/Layout`
dentro del `.pbix` (es un ZIP; `Report/Layout` es JSON UTF-16LE con
BOM). Referencia de canvas: página de **1920px** de ancho, menú lateral
embebido del propio reporte de **262px**, área de contenido real de
**1658px**. Expresar los anchos como % de esa área de contenido (no
píxeles fijos) para que escale responsivo. Confirmado con este patrón en
Conciliación bancaria (54.3%), Flujo de caja (61.8%, tabla y gráfica) y
Ejecución de Gastos (67.2% tabla+resumen, 94.3% gráficas).

### Pendientes

- Exportar `BalanceGeneral`, `SaldosBancos` y `SaldoBancario` juntos la
  próxima vez que se actualicen datos (para que los 3 períodos queden
  sincronizados entre sí).
- Correr `backend/deploy_servidor_real/13_saldos_bancos_financiero.sql`
  contra el servidor real cuando se publique el módulo Financiero ahí
  (hoy solo está probado contra la base de desarrollo).

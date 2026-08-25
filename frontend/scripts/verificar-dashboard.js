// Captura de pantalla automatizada de ambos dashboards, para
// autoverificación visual antes de reportar un cambio como terminado.
// Requiere que el backend (puerto 8001) y el frontend (puerto 5173) ya
// estén corriendo. Uso: node scripts/verificar-dashboard.js
import { chromium } from "@playwright/test";
import { execSync } from "child_process";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FRONTEND_URL = process.env.FRONTEND_URL || "http://localhost:5173";
const BACKEND_DIR = path.resolve(__dirname, "..", "..", "backend");
const PYTHON = path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe");
const OUT_DIR = path.resolve(__dirname, "..", "..", "docs", "legacy", "capturas-actuales");

function generarToken() {
  return execSync(`"${PYTHON}" -m app.scripts.token_verificacion`, { cwd: BACKEND_DIR })
    .toString()
    .trim();
}

async function capturar(page, ruta, archivoSalida) {
  await page.goto(`${FRONTEND_URL}${ruta}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(800); // dar tiempo a que rendericen los gráficos
  const destino = path.join(OUT_DIR, archivoSalida);
  await page.screenshot({ path: destino, fullPage: true });
  console.log(`Captura guardada: ${destino}`);
}

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const token = generarToken();

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });

  // Inyecta una sesión ya autenticada (evita depender de la pantalla de
  // login y de activar/desactivar cuentas de prueba a mano).
  await page.goto(FRONTEND_URL);
  await page.evaluate((t) => localStorage.setItem("agrequima_token", t), token);

  await capturar(page, "/app/plaguicidas", "plaguicidas.png");
  await capturar(page, "/app/nutrientes", "nutrientes.png");

  await browser.close();
})();

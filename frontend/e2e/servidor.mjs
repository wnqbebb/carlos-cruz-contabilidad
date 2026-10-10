#!/usr/bin/env node
/**
 * Servidor AISLADO para los recorridos del usuario (Playwright).
 *
 * Arranca la aplicación completa (API + interfaz compilada) con una base y una carpeta de datos
 * temporales, en el puerto 8010. Nunca toca la base del contador (datos_app/) ni su backend/.env.
 * Playwright lo inicia y lo detiene solo (ver playwright.config.ts).
 */
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = fileURLToPath(new URL("../..", import.meta.url));
const PUERTO = process.env.E2E_PUERTO || "8010";
const tmp = mkdtempSync(join(tmpdir(), "carloscruz-e2e-"));
const env = join(tmp, "e2e.env");
writeFileSync(env, "# configuración vacía de los recorridos\n");

const python = [join(RAIZ, ".venv", "Scripts", "python.exe"), join(RAIZ, ".venv", "bin", "python")].find(existsSync) || "python";
const hijo = spawn(python, ["-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", PUERTO], {
  cwd: RAIZ,
  stdio: "inherit",
  env: {
    ...process.env,
    CC_ENV: env,
    CC_SQLITE: join(tmp, "e2e.db"),
    CC_DATOS_APP: join(tmp, "datos"),
    CC_TMP_SUBIDAS: join(tmp, "subidas"),
    ALMACENAMIENTO: "local",
    DATABASE_URL: "",
    CC_SIN_LLAVERO: "1",
    CC_MIGRAR_SECRETOS: "0",
    CC_SIN_RESPALDO: "1",
    CC_ARGON_RAPIDO: "1",
    CC_LIMITE_GENERAL: "1000000",
    CC_LIMITE_COSTOSAS: "1000000",
    CLAVE_SESION: "sesion-de-los-recorridos-0123456789abcdef",
    CC_TESSERACT: join(RAIZ, "datos_app", "tesseract", "tesseract.exe"),
    CC_OCR: join(RAIZ, "datos_app"),
  },
});
const salir = () => hijo.kill();
process.on("SIGINT", salir);
process.on("SIGTERM", salir);
hijo.on("exit", (c) => process.exit(c ?? 0));

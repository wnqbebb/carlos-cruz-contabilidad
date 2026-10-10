# CLAUDE.md — Reglas permanentes del proyecto «Carlos Cruz · Contabilidad»

Claude Code lee este archivo al iniciar. Estas reglas valen para **todas** las sesiones.

## Qué es
Mini-SaaS contable para el contador Carlos Cruz (Colombia).
- Backend: FastAPI (Python 3.12) en `backend/`.
- Frontend: React + Vite + TypeScript en `frontend/`.
- Base de datos: Supabase (Postgres) o SQLite local.
- Despliegue: Vercel (frontend, y dirección única del usuario) y Render (backend, detrás del proxy `/api/*` de Vercel).
- Entorno del usuario: Windows (usa **CMD**), repositorio en `C:\Users\Admin\Documents\DON CARLOS\carlos-cruz-contabilidad`. Dale los comandos para CMD, no para PowerShell.
- Idioma de la app, de los mensajes y de los informes: **español de Colombia**, claro y sin jerga.

## Cómo verificar (correr SIEMPRE antes de decir que algo está hecho)
```
cd backend && python -m pytest -q
cd frontend && npx tsc --noEmit && npm run build && npm run lint:diseno
cd frontend && npx playwright test        # recorridos del usuario (e2e)
```
En la nube:
```
curl -s https://carloscruz-api.onrender.com/api/salud
curl -s https://carlos-cruz-contabilidad.vercel.app/api/salud
```
Ambos deben devolver **JSON**.

## Reglas de honestidad (no negociables)
1. **Nunca digas «hecho», «resuelto», «100 %» o «verificado» sin pegar la salida real del comando que lo prueba.** Si un comando falla o no se pudo correr, dilo tal cual.
2. **«Terminado» = el recorrido del usuario pasa en un navegador real** (Playwright), no solo las pruebas unitarias.
3. **Una función que existía no se quita sin preguntarle al usuario.**
4. **Si algo depende del usuario** (cuentas, claves, decisiones), pídeselo con una pregunta concreta y sigue con el resto.
5. **Los secretos nunca pasan por el chat.** El usuario los escribe en el panel de Render o Vercel o en su `.env`.
6. **Ningún dato real de clientes en git:** fotos, cédulas, NIT, nombres. Van en `privado/`, que está ignorado.
7. **Antes de cada commit:** pruebas, `tsc` y build en verde. Un error de tipos es un error, aunque Vite compile.
8. **Al final de cada tarea, informe corto con:**
   - qué se hizo;
   - la salida de las verificaciones;
   - qué falta;
   - qué necesita el usuario.

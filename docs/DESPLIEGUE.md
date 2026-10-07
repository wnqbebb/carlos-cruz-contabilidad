# Subir Carlos Cruz a la nube

El objetivo es concreto: que el programa quede **instalado en la nube**, de modo
que usted pueda corregir errores y subir mejoras desde cualquier parte del país
sin tocar el computador del cliente, y **sin que él pierda ni un dato**.

```
   Vercel  ──────▶  Render  ──────▶  Supabase
  la pantalla     el motor que      donde viven
  que él abre     hace las cuentas   los datos
```

Cada pieza es gratis. Las tres se actualizan **solas** cada vez que usted sube
cambios a GitHub: el cliente no instala nada, solo recarga la página.

---

## Estado actual

| Pieza | Estado |
|---|---|
| **Supabase** | ✅ Listo. Proyecto `jnyakmcnplrhnpvkunfq`, región São Paulo, 12 tablas creadas, RLS activa. Probado de punta a punta contra Postgres. |
| **GitHub** | ⬜ Falta subir el repositorio |
| **Render** (backend) | ⬜ Falta crear el servicio |
| **Vercel** (frontend) | ⬜ Falta crear el proyecto |

Todo lo que se necesita ya está en el repositorio: `render.yaml`,
`frontend/vercel.json` y el workflow que impide que Supabase se pause.

---

## PASO 1 — Subir el código a GitHub

Render y Vercel leen el código de ahí; es el requisito de los dos.

```bash
cd "sistema-contable-fanant"
git add -A
git commit -m "Carlos Cruz v2.0.0"
gh repo create carlos-cruz --private --source=. --push
```

Si no tiene `gh`, cree el repositorio en <https://github.com/new> (marque
**Private**) y después:

```bash
git remote add origin https://github.com/SU-USUARIO/carlos-cruz.git
git branch -M main
git push -u origin main
```

> **El archivo `backend/.env` NO se sube**: está en `.gitignore`. Compruébelo
> con `git check-ignore -v backend/.env` antes de hacer push. Las claves se
> cargan como variables de entorno en Render, nunca en el código.

## PASO 2 — Backend en Render

1. <https://render.com> → entrar con GitHub.
2. **New** → **Blueprint** → elegir el repositorio. Render lee `render.yaml` solo.
3. Pide cuatro valores. Son los mismos que ya están en `backend/.env`:

   | Variable | De dónde |
   |---|---|
   | `DATABASE_URL` | cópiela tal cual de `backend/.env` |
   | `SUPABASE_URL` | ídem |
   | `SUPABASE_ANON_KEY` | ídem |
   | `SUPABASE_SERVICE_KEY` | ídem |

4. Deje `CORS_ORIGENES` vacío por ahora; se llena en el paso 4.
5. **Create**. Tarda unos 5 minutos la primera vez.
6. Al terminar, copie la URL (algo como `https://carloscruz-api.onrender.com`) y
   compruebe que `…/api/salud` responde con `"ok": true` y `"es_postgres": true`.

> **Plan gratuito:** el servicio se duerme a los 15 minutos sin uso. La primera
> carga del día tarda ~30 segundos; después va normal. El plan más bajo de pago
> lo evita, pero para un contador que entra unas veces al día no suele estorbar.

## PASO 3 — Frontend en Vercel

1. <https://vercel.com> → entrar con GitHub.
2. **Add New** → **Project** → el mismo repositorio.
3. **Root Directory**: escriba `frontend` (importante).
4. **Environment Variables**: agregue

   ```
   VITE_API = https://carloscruz-api.onrender.com
   ```

   (la URL del paso 2).
5. **Deploy**. Vercel lee `frontend/vercel.json` solo.

## PASO 4 — Cerrar el círculo

En Render → su servicio → **Environment**, ponga en `CORS_ORIGENES` la URL que
le dio Vercel:

```
CORS_ORIGENES=https://carlos-cruz.vercel.app
```

Guarde. Render se reinicia solo. (Las URL de prueba `*.vercel.app` ya están
permitidas por `allow_origin_regex` en `backend/app/main.py`.)

## PASO 5 — Que Supabase no se pause

El plan gratuito pausa un proyecto que pasa varios días sin actividad. Ya está
resuelto en el repositorio:

1. GitHub → su repositorio → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**.
2. Nombre `DATABASE_URL`, valor el mismo de `backend/.env`.

Listo. `.github/workflows/mantener-supabase-vivo.yml` consulta la base cada
3 días desde los servidores de GitHub. **No depende de que ningún computador
esté encendido**, así que su cliente puede irse dos meses y al volver todo sigue.

---

## Cómo subir una corrección después

Esto es lo que resuelve su problema de fondo:

```bash
git add -A
git commit -m "corrige lo que sea"
git push
```

Y ya. Render y Vercel detectan el push, compilan y publican solos en 2 o 3
minutos. **El cliente no instala nada**: recarga la página y tiene la corrección.
**Los datos no se tocan**: viven en Supabase, aparte del código.

Si una versión sale mal, en Vercel se vuelve a la anterior con un clic
(*Deployments* → la buena → *Promote to Production*), y en Render igual desde
*Events* → *Rollback*.

---

## Lista de verificación

- [ ] `git check-ignore -v backend/.env` confirma que el `.env` está ignorado
- [ ] `…/api/salud` de Render responde `"ok": true` y `"es_postgres": true`
- [ ] La página de Vercel abre y abajo a la izquierda dice **Supabase** en verde
- [ ] Se puede crear un cliente desde la web y sigue ahí al recargar
- [ ] Calcular un periodo guarda y aparece en la pestaña «Estados financieros»
- [ ] El secreto `DATABASE_URL` está puesto en GitHub Actions
- [ ] En el celular: menú inferior, tablas legibles, nada se sale de la pantalla

---

## Copias de seguridad

Supabase hace copias automáticas en el plan pagado. En el gratuito conviene
bajar una cada cierto tiempo:

```bash
pg_dump "$DATABASE_URL" -Fc -f respaldo-$(date +%Y%m%d).dump
```

Lo que **no** se puede perder es la tabla `cierres`: es la que encadena los
saldos de un periodo con el siguiente. Sin ella hay que reconstruir los saldos
iniciales a mano.

---

## Y si prefiere que además quede en el computador del cliente

Las dos cosas conviven. El mismo código corre en la nube y como programa
instalado; lo decide `ALMACENAMIENTO` en la configuración. Ver
[INSTALAR_EN_EL_CLIENTE.md](INSTALAR_EN_EL_CLIENTE.md).

Si el programa instalado apunta a **la misma** `DATABASE_URL` de Supabase, el
cliente trabaja desde su computador y usted ve exactamente los mismos datos
desde la web. Es la combinación más cómoda: velocidad de escritorio y respaldo
en la nube.

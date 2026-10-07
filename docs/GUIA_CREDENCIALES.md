# Guía: cómo conseguir las credenciales y pasármelas

Escrita para alguien que **nunca ha usado** Supabase, Render ni Vercel.
Todo lo que sale aquí es **gratis**. Tiempo: unos 20 minutos la primera vez.

---

## Antes de empezar: ¿de verdad lo necesita?

Hay dos formas de usar la aplicación, y conviene decidir antes de gastar tiempo.

| | **Solo en su computador** | **En línea** |
|---|---|---|
| Qué hay que configurar | Nada. Ya funciona. | Lo de esta guía |
| Costo | $0 | $0 (con los límites de abajo) |
| Entrar desde el celular | No | Sí |
| Si se daña el computador | Pierde los datos | Están a salvo |
| Velocidad | Instantánea | Depende de internet |
| ¿Se "duerme"? | Nunca | Sí, ver más abajo |

Con **5.000 clientes** la versión local va sobrada: SQLite maneja eso sin
despeinarse. La razón real para pasar a Supabase es querer entrar desde el
celular o desde otro computador, y tener los datos respaldados fuera de la casa.

> **Mi recomendación honesta:** si va a trabajar siempre desde el mismo
> computador, quédese en local y haga una copia del archivo
> `datos_app/carloscruz.db` a una USB o a Drive cada mes. Es gratis, instantáneo
> y nunca se cae. Pase a Supabase cuando de verdad necesite entrar desde otro
> lado.

Si decide seguir, continúe.

---

## Lo que es gratis y lo que tiene letra pequeña

| Servicio | Para qué | Plan gratis | La letra pequeña |
|---|---|---|---|
| **Supabase** | Guardar los datos | 500 MB de base, 2 proyectos | **El proyecto se pausa si pasa 1 semana sin usarlo.** Hay que entrar al panel y despausarlo a mano. |
| **Render** | Correr el motor contable | 750 horas/mes | **El servicio se duerme a los 15 minutos sin uso.** La primera carga del día tarda ~30 segundos. |
| **Vercel** | Mostrar la pantalla | Generoso | Ninguna relevante. |

500 MB alcanzan de sobra: 5.000 clientes con varios años de contabilidad ocupan
menos de 100 MB.

Lo de la **pausa de Supabase** es lo más molesto para un contador que trabaja por
temporadas. Si cada mes entra al menos una vez, no la verá nunca.

---

## PASO 1 — Crear la cuenta de Supabase

1. Entre a **<https://supabase.com>** y pulse **Start your project**.
2. Entre con su cuenta de GitHub o con su correo. (Si usa correo, confirme el
   mensaje que le llega.)
3. Ya adentro verá **New project**. Púlselo.

## PASO 2 — Crear el proyecto

Le va a pedir cuatro cosas:

| Campo | Qué poner |
|---|---|
| **Name** | `carlos-cruz` |
| **Database Password** | Pulse **Generate a password** y **CÓPIELA YA** a un papel o a su gestor de contraseñas. |
| **Region** | `South America (São Paulo)` — es la más cercana a Colombia |
| **Pricing Plan** | **Free** |

> ⚠️ **La contraseña de la base NO se vuelve a mostrar nunca.** Si la pierde,
> toca restablecerla desde *Settings → Database → Reset database password*.
> No es grave, pero es un paso de más.

Pulse **Create new project** y espere 1 o 2 minutos mientras lo prepara.

## PASO 3 — Crear las tablas

1. En el menú de la izquierda busque el icono **SQL Editor** (parece una hoja
   con `>_`).
2. Pulse **New query**.
3. Abra en su computador el archivo
   `sistema-contable-fanant/supabase/migraciones/001_esquema.sql`,
   seleccione **todo** el contenido (Ctrl+A), cópielo (Ctrl+C) y péguelo en esa
   caja de Supabase.
4. Pulse **Run** (o Ctrl+Enter). Debe decir *Success*.
5. Pulse **New query** otra vez y repita lo mismo con
   `supabase/migraciones/002_seguridad.sql`.

> El orden importa: primero el 001, después el 002. Los dos se pueden volver a
> ejecutar las veces que quiera sin dañar nada.

## PASO 4 — Copiar las cuatro credenciales

Ahora vamos a sacar cuatro datos. Abra en su computador el archivo
`sistema-contable-fanant/backend/.env` con el Bloc de notas; ahí va a pegar cada
uno.

### 4.1 — DATABASE_URL (la más importante)

1. En Supabase, abajo a la izquierda, pulse **Project Settings** (el engranaje).
2. Entre a **Database**.
3. Busque la sección **Connection string** y elija la pestaña **URI**.
4. Arriba hay un selector de modo: elija **Transaction pooler**
   (es el que usa el puerto **6543**).
5. Copie el texto completo. Se ve parecido a esto:

```
postgresql://postgres.abcdefghijklmnop:[YOUR-PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
```

6. **Reemplace `[YOUR-PASSWORD]`** (incluidos los corchetes) por la contraseña
   que copió en el paso 2.
7. **Agregue al final** `?sslmode=require`.

Debe quedar así de completo:

```
DATABASE_URL=postgresql://postgres.abcdefghijklmnop:MiClaveReal123@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

### 4.2 — Las otras tres

En **Project Settings → API** encontrará:

| En Supabase dice | Péguelo en |
|---|---|
| **Project URL** | `SUPABASE_URL=` |
| **anon** `public` | `SUPABASE_ANON_KEY=` |
| **service_role** `secret` | `SUPABASE_SERVICE_KEY=` |

> La clave **service_role** es la llave maestra de la base. Nunca la pegue en un
> chat, ni en un correo, ni en una captura de pantalla. Solo va en ese archivo
> `.env`, que está configurado para no subirse nunca a internet.

### 4.3 — Cambiar el modo

En el mismo archivo, busque la última línea y cámbiela:

```
ALMACENAMIENTO=supabase
```

Guarde el archivo (Ctrl+S) y ciérrelo.

## PASO 5 — Comprobar que quedó bien

Abra la carpeta `sistema-contable-fanant` y ejecute:

```
.venv\Scripts\python backend\comprobar.py
```

Le va a decir, línea por línea, qué está bien y qué falta. Si algo quedó mal, el
mensaje dice exactamente dónde arreglarlo. No muestra ninguna clave completa, así
que puede mandarme esa salida sin riesgo.

Cuando todo salga en `[ OK ]`:

```
.venv\Scripts\python backend\sembrar.py
iniciar.bat
```

Listo: la aplicación ya está guardando en Supabase. Lo confirma el punto
**verde** abajo a la izquierda del menú, que dirá *Supabase*.

---

## Cómo pasarme las credenciales (importante)

**Nunca por chat.** Si las escribe en una conversación quedan en el historial y
hay que revocarlas.

La forma correcta es la de esta guía: **usted las pega en `backend/.env`**. Ese
archivo:

- vive solo en su computador;
- está en `.gitignore`, así que **nunca** se sube a GitHub;
- es el único sitio de donde la aplicación las lee.

Si algo no funciona, mándeme **la salida de `comprobar.py`**, que está hecha a
propósito para no revelar ninguna clave: muestra los primeros y últimos
caracteres y cuántos hay, lo justo para detectar un error de copiado.

---

## Si ya pegó alguna clave en un chat

Revóquela y genere otra. Toma un minuto:

| Credencial | Dónde se revoca |
|---|---|
| **Supabase** (token `sbp_…`) | <https://supabase.com/dashboard/account/tokens> → el token → *Revoke* |
| **GitHub** (token `ghp_…`) | <https://github.com/settings/tokens> → el token → *Delete* |
| **Vercel** (token) | <https://vercel.com/account/tokens> → el token → *Delete* |
| **Contraseña de la base** | Supabase → *Settings → Database → Reset database password* |

---

## Publicar en internet (después, cuando ya funcione en local)

Esto viene en [DESPLIEGUE.md](DESPLIEGUE.md). Resumen de qué hace cada servicio:

```
   Vercel  ──────▶  Render  ──────▶  Supabase
  la pantalla     el motor que      donde viven
  que usted ve    hace las cuentas   los datos
```

Se necesita que el código esté en GitHub (gratis) para que Render y Vercel lo
lean. Esa parte la hacemos cuando usted dé el visto bueno a lo que ve en local.

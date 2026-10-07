# Instalar Carlos Cruz en el computador del cliente

El programa queda como una carpeta que se copia y se abre con doble clic. En el
computador del cliente **no hay que instalar Python, ni Node, ni nada**.

---

## 1. Construir el programa (en SU computador, una sola vez)

```
empaquetar\construir.bat
```

Tarda unos 3 minutos. Al terminar queda:

```
empaquetar\salida\CarlosCruz\
    CarlosCruz.exe          ← el programa
    LEAME.txt               ← instructivo para el cliente
    _internal\              ← Python, el motor y la interfaz, todo adentro
```

Son unos 65 MB en total.

## 2. Llevarlo al computador del cliente

Copie **la carpeta `CarlosCruz` completa** —no solo el .exe— a una USB, a Drive
o a donde prefiera. En el computador del cliente, péguela donde quiera que viva;
por ejemplo en `C:\Carlos Cruz`.

Conviene crear un acceso directo en el escritorio: clic derecho sobre
`CarlosCruz.exe` → *Enviar a* → *Escritorio (crear acceso directo)*.

## 3. Abrirlo

Doble clic en `CarlosCruz.exe`. Se abre una ventana negra (el motor) y enseguida
el navegador con el programa. Para cerrarlo todo, se cierra la ventana negra.

> **Windows va a mostrar una advertencia la primera vez** ("Windows protegió su
> PC"). Es porque el programa no tiene firma digital, que es un certificado de
> pago. Se pulsa *Más información* → *Ejecutar de todas formas*. Solo pasa una vez.

---

## Dónde quedan los datos

```
Documentos\Carlos Cruz\
    carloscruz.db           ← TODOS los clientes y toda la contabilidad
    configuracion.env       ← configuración (local o en línea)
```

Separar los datos del programa es a propósito: así se puede reemplazar la
carpeta del programa por una versión nueva sin tocar la información del cliente.

### Copia de seguridad

Una vez al mes, copie `carloscruz.db` a una USB o a la nube. Con eso basta: si
el computador se daña, se copia ese archivo de vuelta y no se pierde nada.

Para automatizarlo, el Programador de tareas de Windows puede ejecutar:

```
copy "%USERPROFILE%\Documents\Carlos Cruz\carloscruz.db" "D:\Respaldos\carloscruz-%DATE%.db"
```

---

## Local o en línea: cuál conviene

| | **Local** (lo que trae de fábrica) | **En línea** (Supabase) |
|---|---|---|
| Costo | $0 | $0 con límites |
| Internet | No hace falta | Obligatorio |
| Velocidad | Instantánea | Depende de la conexión |
| Entrar desde el celular | No | Sí |
| Se pausa por inactividad | **Nunca** | Sí, en el plan gratuito |

**Para un contador que trabaja en su oficina, lo local es mejor**: más rápido,
sin internet y sin pausas. Lo en línea tiene sentido si necesita entrar desde
varios lugares.

### Si elige en línea: que no se pause

El plan gratuito de Supabase pausa un proyecto que pasa varios días sin
actividad. Hay dos formas de evitarlo, las dos gratis:

1. **En el computador del cliente** — ejecutar una vez `programar.bat`. Crea una
   tarea de Windows que cada 3 días consulta la base. Funciona mientras el
   computador se encienda de vez en cuando.

2. **En GitHub, sin depender de ningún computador** (más confiable) — ya está
   `.github/workflows/mantener-supabase-vivo.yml`. Solo hay que subir el
   repositorio y guardar `DATABASE_URL` en *Settings → Secrets and variables →
   Actions*. GitHub lo ejecuta cada 3 días, encendido o no el computador.

Con la opción 2, el cliente puede irse dos meses y al volver todo sigue ahí.

---

## Actualizar a una versión nueva

1. Construya de nuevo con `empaquetar\construir.bat`.
2. En el computador del cliente, **cierre el programa**.
3. Reemplace la carpeta `CarlosCruz` por la nueva.
4. Listo. Los datos no se tocan: viven en `Documentos\Carlos Cruz`.

---

## Si algo falla

El programa escribe lo que pasa en la ventana negra. Si no abre, esa ventana
dice por qué y espera a que se pulse Enter, para que dé tiempo de leerla.

Para un diagnóstico más completo, desde la carpeta del código fuente:

```
.venv\Scripts\python backend\comprobar.py
```

Revisa configuración, conexión, tablas, datos e interfaz, y dice qué arreglar.
No muestra ninguna clave completa, así que esa salida se puede compartir.

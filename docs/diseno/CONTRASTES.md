# Contrastes medidos (v2.2)

Generado por `frontend/scripts/contrastes.mjs` a partir de `src/styles/tokens.css`.
No es una lista escrita a mano: si un token cambia, se vuelve a correr y el informe cambia.
Los colores translúcidos se componen sobre el fondo que tienen debajo.

Criterios: superficies ≥ 1,10:1 además de su borde (8.1); texto AA 4,5:1.
El color de cada cliente (8.3) se ajusta solo a 4,5:1 sobre la hoja, en cada modo
(`colorCliente.ts`); las ocho muestras están en el catálogo `/diseno`.

## Modo claro

| Par | Contraste | Mínimo | | Uso |
|---|---|---|---|---|
| `--hoja` sobre `--lienzo` | **1.14:1** | 1,10:1 | ✅ | superficie: tarjeta sobre lienzo |
| `--barra` sobre `--lienzo` | **1.11:1** | 1,10:1 | ✅ | superficie: barra lateral sobre lienzo |
| `--campo` sobre `--hoja` | **1.11:1** | 1,10:1 | ✅ | superficie: campo sobre tarjeta (con borde --borde-campo) |
| `--borde-campo` sobre `--hoja` | **1.69:1** | 1,50:1 | ✅ | borde del campo sobre tarjeta |
| `--tinta` sobre `--lienzo` | **14.53:1** | 4,50:1 | ✅ | texto principal |
| `--tinta` sobre `--hoja` | **16.63:1** | 4,50:1 | ✅ | texto principal |
| `--tinta` sobre `--campo` | **18.42:1** | 4,50:1 | ✅ | texto en campos |
| `--grafito` sobre `--lienzo` | **8.99:1** | 4,50:1 | ✅ | texto secundario |
| `--grafito` sobre `--hoja` | **10.29:1** | 4,50:1 | ✅ | texto secundario, etiquetas de campo |
| `--grafito` sobre `--barra` | **10.02:1** | 4,50:1 | ✅ | navegación inactiva |
| `--gris` sobre `--hoja` | **6.15:1** | 4,50:1 | ✅ | metadatos |
| `--gris` sobre `--lienzo` | **5.37:1** | 4,50:1 | ✅ | metadatos |
| `--gris` sobre `--hoja-2` | **5.73:1** | 4,50:1 | ✅ | metadatos sobre zona secundaria |
| `--azul-tinta` sobre `--hoja` | **8.82:1** | 4,50:1 | ✅ | enlaces |
| `--azul-tinta` sobre `--lienzo` | **7.71:1** | 4,50:1 | ✅ | enlaces |
| `--azul` sobre `--hoja` | **6.44:1** | 4,50:1 | ✅ | estado «Cuadra» |
| `--sobre-color` sobre `--azul` | **7.13:1** | 4,50:1 | ✅ | botón principal |
| `--rojo` sobre `--hoja` | **5.41:1** | 4,50:1 | ✅ | pérdidas y descuadres |
| `--rojo` sobre `--rojo-suave` | **5.11:1** | 4,50:1 | ✅ | aviso de error |
| `--ambar` sobre `--hoja` | **5.01:1** | 4,50:1 | ✅ | advertencias |
| `--ambar` sobre `--ambar-suave` | **4.93:1** | 4,50:1 | ✅ | aviso de advertencia |
| `--sobre-tinta` sobre `--tinta` | **16.61:1** | 4,50:1 | ✅ | texto sobre tinta (Expediente, píldora) |
| `--sobre-tinta-2` sobre `--tinta` | **7.65:1** | 4,50:1 | ✅ | texto secundario sobre tinta |
| `--banda-texto` sobre `--banda-taller` | **13.82:1** | 4,50:1 | ✅ | banda de taller (Trabajar) |
| `--banda-texto-2` sobre `--banda-taller` | **9.13:1** | 4,50:1 | ✅ | banda de taller, secundario |
| `--banda-azul-tinta` sobre `--banda-taller` | **8.49:1** | 4,50:1 | ✅ | enlace en la banda de taller |
| `--tinta` sobre `--cabecera-clientes` | **13.22:1** | 4,50:1 | ✅ | título sobre la cabecera de Clientes |
| `--gris` sobre `--cabecera-clientes` | **4.89:1** | 4,50:1 | ✅ | metaencabezado sobre la cabecera de Clientes |
| `--tinta` sobre `--cabecera-parametros` | **14.89:1** | 4,50:1 | ✅ | título sobre la cabecera de Parámetros |
| `--gris` sobre `--cabecera-parametros` | **5.51:1** | 4,50:1 | ✅ | metaencabezado sobre la cabecera de Parámetros |
| `--sobre-color` sobre `--frio-oscuro` | **8.10:1** | 4,50:1 | ✅ | píldora activa de Parámetros |
| `--sobre-color` sobre `--azul-tinta` | **9.77:1** | 4,50:1 | ✅ | píldora activa de Clientes |
| `--sobre-tinta` sobre `--grafito` | **10.28:1** | 4,50:1 | ✅ | píldora activa de Trabajar |

## Modo oscuro

| Par | Contraste | Mínimo | | Uso |
|---|---|---|---|---|
| `--hoja` sobre `--lienzo` | **1.12:1** | 1,10:1 | ✅ | superficie: tarjeta sobre lienzo |
| `--barra` sobre `--lienzo` | **1.11:1** | 1,10:1 | ✅ | superficie: barra lateral sobre lienzo |
| `--campo` sobre `--hoja` | **1.11:1** | 1,10:1 | ✅ | superficie: campo sobre tarjeta (con borde --borde-campo) |
| `--borde-campo` sobre `--hoja` | **1.77:1** | 1,50:1 | ✅ | borde del campo sobre tarjeta |
| `--tinta` sobre `--lienzo` | **16.09:1** | 4,50:1 | ✅ | texto principal |
| `--tinta` sobre `--hoja` | **14.37:1** | 4,50:1 | ✅ | texto principal |
| `--tinta` sobre `--campo` | **15.97:1** | 4,50:1 | ✅ | texto en campos |
| `--grafito` sobre `--lienzo` | **9.87:1** | 4,50:1 | ✅ | texto secundario |
| `--grafito` sobre `--hoja` | **8.81:1** | 4,50:1 | ✅ | texto secundario, etiquetas de campo |
| `--grafito` sobre `--barra` | **8.91:1** | 4,50:1 | ✅ | navegación inactiva |
| `--gris` sobre `--hoja` | **5.43:1** | 4,50:1 | ✅ | metadatos |
| `--gris` sobre `--lienzo` | **6.08:1** | 4,50:1 | ✅ | metadatos |
| `--gris` sobre `--hoja-2` | **4.97:1** | 4,50:1 | ✅ | metadatos sobre zona secundaria |
| `--azul-tinta` sobre `--hoja` | **9.23:1** | 4,50:1 | ✅ | enlaces |
| `--azul-tinta` sobre `--lienzo` | **10.34:1** | 4,50:1 | ✅ | enlaces |
| `--azul` sobre `--hoja` | **7.45:1** | 4,50:1 | ✅ | estado «Cuadra» |
| `--sobre-color` sobre `--azul` | **8.34:1** | 4,50:1 | ✅ | botón principal |
| `--rojo` sobre `--hoja` | **6.83:1** | 4,50:1 | ✅ | pérdidas y descuadres |
| `--rojo` sobre `--rojo-suave` | **6.73:1** | 4,50:1 | ✅ | aviso de error |
| `--ambar` sobre `--hoja` | **8.52:1** | 4,50:1 | ✅ | advertencias |
| `--ambar` sobre `--ambar-suave` | **7.96:1** | 4,50:1 | ✅ | aviso de advertencia |
| `--sobre-tinta` sobre `--tinta` | **15.36:1** | 4,50:1 | ✅ | texto sobre tinta (Expediente, píldora) |
| `--sobre-tinta-2` sobre `--tinta` | **7.13:1** | 4,50:1 | ✅ | texto secundario sobre tinta |
| `--banda-texto` sobre `--banda-taller` | **12.82:1** | 4,50:1 | ✅ | banda de taller (Trabajar) |
| `--banda-texto-2` sobre `--banda-taller` | **8.47:1** | 4,50:1 | ✅ | banda de taller, secundario |
| `--banda-azul-tinta` sobre `--banda-taller` | **7.87:1** | 4,50:1 | ✅ | enlace en la banda de taller |
| `--tinta` sobre `--cabecera-clientes` | **14.65:1** | 4,50:1 | ✅ | título sobre la cabecera de Clientes |
| `--gris` sobre `--cabecera-clientes` | **5.54:1** | 4,50:1 | ✅ | metaencabezado sobre la cabecera de Clientes |
| `--tinta` sobre `--cabecera-parametros` | **13.90:1** | 4,50:1 | ✅ | título sobre la cabecera de Parámetros |
| `--gris` sobre `--cabecera-parametros` | **5.26:1** | 4,50:1 | ✅ | metaencabezado sobre la cabecera de Parámetros |
| `--sobre-color` sobre `--frio-oscuro` | **9.46:1** | 4,50:1 | ✅ | píldora activa de Parámetros |
| `--sobre-color` sobre `--azul-tinta` | **10.34:1** | 4,50:1 | ✅ | píldora activa de Clientes |
| `--sobre-tinta` sobre `--grafito` | **9.42:1** | 4,50:1 | ✅ | píldora activa de Trabajar |

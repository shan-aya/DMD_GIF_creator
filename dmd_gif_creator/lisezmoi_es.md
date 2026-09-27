# DMD GIF Creator — Guía de uso

Aplicación Python/Tkinter que convierte imágenes, logotipos y texto en animaciones
GIF optimizadas para una pantalla DMD 128×32 (arcade / pinball / mueble RetroBox).
Esta guía describe, pestaña por pestaña, cada función de la interfaz y su uso
concreto.

> Guía actualizada para la versión **3.1**. Las capturas se hicieron con la versión
> **2.7.4**, tema oscuro, interfaz en español: las pestañas VIDEO y AYUDA, añadidas
> después, no aparecen.
>
> **Nota sobre la localización:** algunas etiquetas y paneles de información (por
> ejemplo los nombres de campo de los paneles "Información de la Imagen" y "Vídeo de
> origen", como `Fichier:` o `Résolution:`) pueden aparecer todavía en francés sea
> cual sea el idioma elegido, igual que los mensajes de la pestaña DEBUG. Las capturas
> de abajo, hechas con una versión anterior, muestran algunas palabras en francés por
> el mismo motivo.

---

## Menú

1. [Visión general](#visión-general)
2. [Pestaña AUTO — análisis y propuestas de IA](#pestaña-auto--análisis-y-propuestas-de-ia)
3. [Pestaña MANUAL — edición avanzada](#pestaña-manual--edición-avanzada)
4. [Pestaña VIDEO — GIF a partir de un vídeo](#pestaña-video--gif-a-partir-de-un-vídeo)
5. [Pestaña TEXTSCROLL — texto animado](#pestaña-textscroll--texto-animado)
6. [Pestaña AJUSTES](#pestaña-ajustes)
7. [Pestaña DEBUG](#pestaña-debug)
8. [Pestaña AYUDA](#pestaña-ayuda)
9. [Función transversal: Modo DMD / Forzar pixel-perfect](#función-transversal-modo-dmd--forzar-pixel-perfect)
10. [Función transversal: Puntuación de calidad y ventana Revisar](#función-transversal-puntuación-de-calidad-y-ventana-revisar)
11. [Buenas prácticas y limitaciones conocidas](#buenas-prácticas-y-limitaciones-conocidas)

---

## Visión general

Al iniciar, la aplicación muestra una columna de pestañas a la izquierda:

**AUTO** · **MANUAL** · **VIDEO** · **TEXTSCROLL** · **AJUSTES** · **DEBUG** · **AYUDA**

Cada pestaña corresponde a una forma diferente de producir una animación GIF 128×32:

| Pestaña | Uso |
|---|---|
| AUTO | Cargue una o varias imágenes (logotipos, ilustraciones...), la IA analiza cada una y propone 6 renders listos para usar. La forma más rápida de procesar un lote de imágenes. |
| MANUAL | Cargue una imagen y ajuste usted mismo cada parámetro (efectos, animación, dibujo) — control total, sin automatismos. |
| VIDEO | Cargue un vídeo, elija el fragmento y el encuadre (seguimiento automático o a mano) y obtenga un GIF 128×32. |
| TEXTSCROLL | Escriba texto y elija una fuente/efecto/animación — no necesita imagen de origen. |
| AJUSTES | Idioma, tema, ajustes de exportación y rendimiento de la aplicación. |
| DEBUG | Registro de actividad de la aplicación, útil para diagnosticar un problema. |
| AYUDA | Esta guía, en el idioma de la interfaz. |

Pasar el ratón por encima de un ajuste poco evidente (pixel-perfect, perfil,
tolerancia, easing, modos de encuadre de vídeo...) muestra una **ayuda
emergente** en el idioma de la interfaz.

---

## Pestaña AUTO — análisis y propuestas de IA

![Pestaña AUTO](images/auto_es.png)

Es la pestaña más completa: carga masiva, análisis automático de
legibilidad/ocupación, y generación de 6 propuestas de render por imagen.

### 1. Parámetros Globales (barra superior)

Estos ajustes se aplican a **todas** las propuestas y a cualquier procesamiento por
lotes:

- **FPS**: fotogramas por segundo de la animación generada (1 a 60).
- **Duración (s)**: duración objetivo de la animación en segundos.
- **Velocidad scroll**: velocidad de desplazamiento en modo Fill/scroll (0.1 a 10,
  permite un desplazamiento más lento que 1 píxel/fotograma).
- **Contraste** / **Saturación**: intensidad aplicada por el motor de optimización
  DMD (`optimize_for_dmd`) antes del render — una protección interna evita que estos
  ajustes "quemen" a blanco puro los píxeles ya claros.
- **Colores GIF**: paleta de cuantización final (8 a 256 colores).
- **Modo DMD / Forzar pixel-perfect**: ver la
  [sección dedicada](#función-transversal-modo-dmd--forzar-pixel-perfect) más abajo —
  esta casilla está **compartida con las pestañas MANUAL y TEXTSCROLL** (marcarla
  aquí la marca en todas partes).
- **Perfil**: ver más abajo.

Cambiar cualquiera de estos ajustes relanza automáticamente el análisis de la imagen
seleccionada.

#### Perfil

Un perfil agrupa todos los ajustes anteriores y tres opciones propias del DMD. El
motor en sí no impone ningún límite: decide el perfil elegido. Se incluyen tres
perfiles:

| Perfil | Para qué | Ajustes |
|---|---|---|
| **Genérico** (por defecto) | Cualquier uso | Sin regla de desplazamiento, sin límite de duración, inversión de logos oscuros activa, 10 i/s. |
| **Logos Recalbox (navegación)** | Logos de juegos mostrados por el panel durante la navegación | Desplazamiento forzado desde 2:1, límite de ida y vuelta de 30 s, inversión de logos oscuros, 15 i/s. |
| **DMD playlist** | GIF reproducidos en playlist en el panel | Desplazamiento forzado desde 2:1, sin límite, inversión de logos oscuros, 20 i/s para mayor fluidez. |

Las tres opciones, modificables a mano bajo la lista de perfiles:

- **Desplazamiento forzado desde (A/A)**: cuando el logo (sin los márgenes
  transparentes) es al menos N veces más ancho que alto, se usa el modo
  Fill/desplazamiento en lugar de Resize. No se recorta nada: todo el logo pasa por
  la pantalla. Desmarcada, se elige según la puntuación.
- **Invertir logos oscuros**: un logo oscuro y casi monocromo sobre fondo
  transparente (por ejemplo texto negro pensado para un fondo claro) es invisible en
  un DMD negro. El motor prueba también su versión invertida y solo la conserva si la
  puntuación de calidad mejora claramente.
- **Límite ida y vuelta (s)**: duración máxima de una ida y vuelta de
  desplazamiento. Por encima, el desplazamiento se acelera (más píxeles por imagen,
  mismos fotogramas por segundo), sin recortar nada.

Botones junto a la lista:

- **➕**: abre la página de creación de un perfil, rellenada con los ajustes
  actuales.
- **✏**: abre la página del perfil seleccionado.
- **💾**: guarda los ajustes actuales en el perfil seleccionado.
- **🗑**: borra un perfil personal, o devuelve un perfil incluido a sus valores de
  origen (con confirmación).

La **página de perfil** muestra cada parámetro con su campo, una ayuda emergente al
pasar el ratón y un botón **?** que muestra su explicación. Los valores fuera de
rango se rechazan antes de guardar. Los perfiles se guardan en `profiles.json`, en la
carpeta de configuración: no hace falta ninguna edición manual.

### 2. Panel "Imágenes" (columna izquierda)

- **📁**: añade una carpeta completa (siempre se escanea de forma recursiva — una
  carpeta que solo contiene subcarpetas se detecta correctamente).
- **🖼️**: añade uno o varios archivos de imagen individualmente.
- **Arrastrar y soltar**: funciona en cualquier parte de la ventana (carpeta o
  archivos).
- **✓ / ✗ / ⇄**: seleccionar todo / deseleccionar todo / invertir la selección en la
  lista.
- **🔓 Réautoriser** ("Reautorizar"): reautoriza una imagen previamente marcada como
  ya exportada (ver abajo).
- **🗑 Vider** ("Vaciar"): vacía la lista por completo.
- Formatos aceptados: **PNG, JPG, BMP, GIF y raw565** (el formato bruto RGB565 que
  lee el DMD — práctico para retocar imágenes ya convertidas).
- **Carpetas grandes**: el escaneo se hace en segundo plano y la ventana sigue
  utilizable; la barra de título muestra « Buscando imágenes… n » mientras no ha
  terminado. Decenas de miles de imágenes se cargan en unos segundos.
- Cada adición es **aditiva** (no sobrescribe la lista existente) y se eliminan
  duplicados.
- Clic derecho sobre una imagen, o tecla `Supr`: elimina la imagen seleccionada de la
  lista (menú contextual "🗑 Retirer de la liste").
- Hacer clic en una imagen de la lista lanza su análisis y muestra su vista previa.

### 3. Panel "Información de la Imagen"

Muestra, para la imagen seleccionada: nombre de archivo, formato, dimensiones, modo
de color, tamaño en disco, paleta dominante detectada y relación ancho/alto
comparada con el objetivo DMD (4.0 = 128/32). Las etiquetas de campo de este panel
solo están disponibles en francés por ahora (`Fichier:`, `Format:`, `Dimensions:`...).

### 4. Vistas previas centrales

- **Imagen Original**: la imagen de origen tal cual (fondo negro garantizado incluso
  en un PNG con transparencia).
- **Vista Previa DMD Principal (128×32)**: el render de la propuesta actualmente
  seleccionada, ampliado en pantalla. Animado de forma continua (scroll, efectos...).
  Si "Modo DMD / Forzar pixel-perfect" está marcado, cada fotograma se simula en
  estilo LED físico (puntos redondos con halo) en lugar de un simple ampliado
  cuadrado.
- Debajo de la vista previa original, un mensaje de estado indica qué propuesta se
  retuvo automáticamente y por qué (p. ej. "'Optimizado' elegido (puntuación: 3.99),
  base: Fill (desplazamiento)"). Se añade una nota cuando ha intervenido una opción
  del perfil: "(logo ancho → Fill aplicado)" o "(logo oscuro → invertido)".

### 5. Propuestas IA (cuadrícula 3×2)

Para cada imagen se calculan y muestran 6 renders en miniatura:

| # | Nombre | Principio |
|---|---|---|
| 1 | Resize (adapté) | Toda la imagen se escala para caber en 128×32 sin recortes (con bandas negras). |
| 2 | Fill (scrolling) | La imagen llena toda la altura de 32px, normalmente más ancha que 128px → se desplaza horizontalmente. |
| 3 | Optimisé | La mejor de las dos anteriores (puntuación más alta), con limpieza y pixel-perfect probados y conservados solo si mejoran el render. Es la propuesta usada por defecto en el procesamiento por lotes. |
| 4-6 | Artistique 1-3 | Un efecto de la pestaña MANUAL (color_shift, wave, spiral, fade, pulse, zoom...) aplicado sobre la animación de la propuesta 3, elegido según las características de la imagen (densidad de bordes, colorido). |

- **Al hacer clic en una miniatura** se selecciona esa propuesta para la vista previa
  principal y para la exportación.
- Al pasar el cursor sobre una miniatura aparece un tooltip con los ajustes exactos
  usados.
- **Propuestas 1-3**: casilla "🔒 Bloquear para el lote" — fuerza esta propuesta
  concreta (en lugar de la mejor puntuación automática) para **todas** las imágenes
  procesadas en el siguiente lote. Solo se puede bloquear una propuesta a la vez.
- **Propuestas 4-6**: botón "🔄 New proposition" (aún no traducido) — sortea un nuevo
  efecto artístico aleatorio (distinto del anterior) para esa casilla.

### 6. Procesamiento por lotes

- **🚀 Procesar todo**: exporta un GIF para cada imagen de la lista.
- **✅ Procesar selección**: exporta solo las imágenes seleccionadas en la lista.
- **⛔ Detener**: cancela un lote en curso.
- Se solicita una carpeta de salida en la primera ejecución; la estructura relativa
  de carpetas de las imágenes de origen (respecto a la carpeta cargada) se recrea
  dentro de la carpeta de salida. Al terminar, un mensaje ofrece abrir directamente
  la carpeta de salida.
- Las imágenes se procesan **en paralelo**, usando casi todos los núcleos del
  procesador (hasta 12 imágenes a la vez): un lote termina mucho más rápido que
  imagen por imagen.
- Cada GIF producido recibe una **puntuación de calidad** (0 a 100). El mensaje de
  fin de lote indica el número de GIF, la puntuación media y el reparto por nota, y
  propone abrir la ventana **Revisar** si hay GIF bajos o malos. Ver la
  [sección dedicada](#función-transversal-puntuación-de-calidad-y-ventana-revisar).
- **🔍 Revisar**: abre directamente la ventana de revisión del último lote. La carpeta
  solo se pide la primera vez; **📂 Otra carpeta…**, en la ventana, permite revisar
  otra.

---

## Pestaña MANUAL — edición avanzada

![Pestaña MANUAL](images/manual_es.png)

Control total, sin ningún automatismo de legibilidad: usted elige cada efecto y cada
parámetro de animación.

### 1. Barra de herramientas (arriba)

- **📂 Cargar**: carga una imagen desde el disco.
- **✂️ Recortar 128×32**: coloca un marco en formato 4:1 sobre la imagen, por defecto
  de 128×32 píxeles de la imagen (un píxel por LED, sin escalado). Arrástrelo para
  moverlo (un clic fuera del marco lo centra en ese punto), flechas = 1 píxel (Mayús:
  10), rueda del ratón = tamaño (se mantiene el formato 4:1). La barra de estado indica
  el tamaño, la posición y los píxeles por LED. Doble clic o Intro = aplicar; Escape o
  nuevo clic en el botón = cancelar.
- **▭ Zona** / **✕ Zona**: limita los efectos a una parte de la imagen. En modo Zona,
  trace un rectángulo con el ratón; arrastre dentro para moverlo; un simple clic fuera
  lo borra. Mientras exista una zona (marco azul claro), los controles y los filtros solo
  afectan a su contenido; Rotación 90° siempre gira toda la imagen (y borra la zona).
  «✕ Zona» vuelve a los efectos sobre toda la imagen; la zona también se borra al
  recortar y al cargar otra imagen.
- **↶ Deshacer** / **↷ Rehacer**: historial de deshacer/rehacer incremental.
  Cada filtro, relleno, borrador mágico o recorte es un punto del historial;
  deshacer y luego rehacer recupera exactamente los estados intermedios (no
  solo el principio/final). Realizar una nueva acción tras deshacer borra la
  rama "rehacer" siguiente, igual que en cualquier editor estándar. Los 4
  controles deslizantes de efectos en tiempo real (siguiente sección) no crean
  puntos de historial (ajuste continuo, no una acción puntual).
- **💾 Exportar GIF**: exporta la animación actualmente generada.
- **📚 Multi-imágenes**: carga varias imágenes para hacer un morphing (aparece la
  lista "Images chargées (morphing)" justo debajo).
- **🎬 Morphing**: genera una animación de transición fundida entre las
  multi-imágenes cargadas.

### 2. Efectos en Tiempo Real

4 controles deslizantes aplicados **inmediatamente** sobre la imagen mostrada
(mecanismo totalmente independiente del motor de optimización de AUTO — aquí no se
aplica ninguna protección automática contra el recorte de altas luces, el control se
deja intencionadamente por completo en manos del usuario):

- **Brillo** (0.5–2.0), **Contraste** (0.5–3.0), **Saturación** (0.0–2.0),
  **Nitidez** (0.0–3.0).

Los controles actúan sobre el estado actual de la imagen (recorte, filtros y rellenos
incluidos). En la siguiente acción permanente (filtro, recorte, relleno, goma), sus
ajustes se integran en la imagen y vuelven a 1,00; «↶ Deshacer» vuelve a antes de esa
acción. Con una **zona** (ver más abajo), solo afectan a la zona.

### 3. Filtros

Botones de efecto inmediato y acumulativo: Desenfoque, Desenfoque Gaussiano, Bordes,
Relieve, Detalle+, Invertir, Espejo H, Espejo V, Rotar 90°, Escala de grises,
Posterizar, Solarizar, Ecualizar, Auto-contraste.

**🔍 Zoom − / 🔍 Zoom + / 100 %**: amplía o reduce el logo en el panel, por pasos del
50 % al 300 %. 100 % corresponde al tamaño calculado automáticamente para 128×32; por
encima, el logo desborda y se desplaza más tiempo; por debajo, es más pequeño y
centrado. Es un ajuste de la animación: la imagen de trabajo no se modifica y el zoom
vuelve al 100 % con cada nueva imagen. La vista previa se rehace en cada cambio.

### 4. Herramientas de Dibujo

- **🎨 Relleno**: modo bote de pintura (clic en la imagen = rellena la zona de color
  contiguo con el color elegido, según la **Tolerancia** ajustada).
- **🧹 Borrador Mágico**: borra (deja transparente/negro) una zona de color similar al
  clic, con la misma lógica de tolerancia.
- **Color**: elige el color activo para el relleno (vista previa mostrada junto al
  botón).
- **Tolerancia**: sensibilidad de detección de color para el relleno/borrador
  (0–100).
- **Fondo negro**: casilla indicativa ligada al renderizado de fondo.
- **Modo DMD / Forzar pixel-perfect**: casilla compartida con AUTO y TEXTSCROLL, ver
  la [sección dedicada](#función-transversal-modo-dmd--forzar-pixel-perfect).

### 5. Edición (lienzo)

Lienzo principal (640×480) que muestra la imagen en edición — aquí es donde se
aplican los clics de las herramientas de dibujo.

### 6. Vista Previa Animación DMD (columna derecha)

- Lienzo de 512×128 que muestra la animación en bucle. Si "Modo DMD / Forzar
  pixel-perfect" está marcado, se renderiza en estilo LED simulado (igual que en
  AUTO); si no, render clásico ampliado en cuadrado.
- **🎬 Previsualizar**: (re)genera la animación a partir de los ajustes actuales.

### 7. Animaciones y Parámetros

- **Animación**: 18 tipos disponibles (scroll, fade_in/out, zoom_in/out, rotate,
  wave, bounce, flash, slide_left/right, spiral, shake, pulse, glitch, pixelate,
  blur_transition, color_shift).
- **Dirección**: horizontal / vertical (relevante para animaciones tipo scroll).
- **FPS**, **Velocidad**, **Duración (s)**: mismos principios que en AUTO pero con
  ajustes propios de la pestaña MANUAL (no compartidos).
- **Bucle**: normal / ping-pong / infinito, con un número de **Repeticiones**.
- **⚙️ Contrôles Avancés** (cuadro aún no traducido): se aplican como
  postprocesado sobre los fotogramas ya generados, sea cual sea el tipo de
  animación elegido.
  - **Easing** (linear/ease-in/ease-out/ease-in-out/bounce): cambia la
    velocidad relativa de reproducción a lo largo de la animación (acelera o
    ralentiza el inicio o el final) sin cambiar el número de fotogramas ni la
    duración total.
  - **Retraso inicio (s)**: añade fotogramas estáticos (imagen inicial
    congelada) al principio de la animación, una sola vez (no se repite en
    cada bucle).
  - **Invertir dirección**: reproduce la secuencia de fotogramas en orden
    inverso.
  - **Rebote en bordes**: la secuencia va y viene en lugar de detenerse o
    reiniciar bruscamente al final, dentro de la misma duración total.
  - **Opacidad**: fundido global de la animación hacia el negro, aplicado en
    último lugar.

### 8. Información de la Imagen

La misma información que en AUTO (dimensiones, modo de color, memoria, relación,
paleta dominante), más el número de estados en el historial de deshacer. Las
etiquetas de campo aquí también están disponibles solo en francés por ahora.

---

## Pestaña VIDEO — GIF a partir de un vídeo

Convierte un fragmento de un vídeo (MP4, M4V, MOV, AVI, MKV, WEBM, WMV, FLV, MPG, MPEG,
TS, 3GP, OGV) en un GIF 128×32. Un códec poco común puede seguir siendo ilegible sea
cual sea la extensión. Necesita
el módulo `opencv-contrib-python` (incluido en el ejecutable de Windows); si falta,
la pestaña lo indica.

### 1. Cargar y reproducir

- **📹 Cargar Vídeo**: abre un archivo de vídeo. También puede **arrastrar y soltar**
  un vídeo en cualquier lugar de la ventana, sea cual sea la pestaña mostrada.
- **Reproducción**: el vídeo se reproduce en bucle en miniatura. **Haga clic** para
  abrirlo a tamaño real en el reproductor de vídeo de Windows.
- **ℹ️ Vídeo de origen**: nombre del archivo, resolución, duración, imágenes por
  segundo, número total de imágenes y tamaño del archivo.

### 2. Ajustes GIF Vídeo

- **FPS** (1 a 60): se ajusta al principio al del vídeo.
- **Duración (s)**: duración del GIF; por defecto, la de la selección.
- **Colores GIF**: 8 a 256.
- **Modo DMD / Forzar pixel-perfect**: la misma casilla que en las otras pestañas.
- **🪄 Calidad automática**: ajusta contraste, saturación y brillo a partir de
  algunas imágenes del vídeo antes del render DMD.
- **Bucle** (normal / ping-pong / infinito) y **Repeticiones**.
- **ℹ️ GIF a exportar** y **Peso GIF estimado**: resumen actualizado en directo.

### 3. Selección (recorte)

Una tira de miniaturas muestra el vídeo. El **tirador verde** (inicio) y el
**tirador rojo** (fin) delimitan el fragmento conservado: se mueven arrastrándolos,
un simple clic en otro sitio no los mueve. La duración seleccionada aparece encima de
la tira.

La **línea cian** (con su triángulo) es el **tiempo de encuadre**: muévala para
recorrer el vídeo y ver o editar el encuadre en ese instante, sin cambiar la
selección.

### 4. Zona de interés (encuadre de vídeo)

Un vídeo casi nunca tiene formato 128×32: se elige qué parte de la imagen conservar.
**Modo de encuadre** — tres modos, solo uno activo a la vez:

| Modo | Principio |
|---|---|
| 🎯 **Seguimiento automático** | Dibuje un rectángulo una vez sobre el sujeto; un rastreador (OpenCV) lo sigue durante todo el vídeo. Tamaño del encuadre calculado automáticamente. |
| 🪄 **Encuadre automático (zoom)** | Usted coloca el encuadre (arrastre el rectángulo); su tamaño se calcula automáticamente. Sin seguimiento, un solo encuadre. |
| ✋ **Manual** | Sin automatismos: se colocan puntos en el tiempo, cada uno con su zona y su zoom. |

En modo **✋ Manual**:

- **➕ Punto aquí**: dibuje un rectángulo sobre la zona deseada; al soltarlo, se
  convierte en un punto de zona en el tiempo de encuadre actual (sustituye a un punto
  ya muy cercano). Arrastre el interior del rectángulo para moverlo, con vista previa
  en directo.
- **🔍 Zoom aquí**: coloca un punto de zoom en el tiempo actual, con el valor del
  cursor **Zoom de encuadre** (-100 % = imagen entera redimensionada, 0 = recorte
  ajustado, +100 % = zoom). Entre dos puntos, zona y zoom evolucionan
  progresivamente.
- **🗑️ Eliminar este punto**: elimina el punto más cercano al tiempo actual;
  **🗑️ Borrar puntos** los elimina todos; **🔄 Recentrar** recentra el encuadre.
- **↶ Deshacer** / **↷ Rehacer**: deshace o rehace la última acción sobre los
  puntos; **📜 Historial de encuadre** enumera esas acciones.
- **Línea de tiempo de los puntos** (bajo la tira): disco naranja = punto de
  seguimiento automático, cuadrado violeta = punto manual, rombo verde azulado =
  punto de zoom. Arrastre un punto para moverlo en el tiempo.

**Vista previa del encuadre** muestra en directo la parte de la imagen que se
conservará.

### 5. Generar y exportar

- **🎬 Generar Vista Previa**: calcula el GIF (encuadre, calidad, render DMD) y lo
  anima en **Vista Previa Animación (Vídeo)** — en Modo DMD, con la lupa 🔍 y el
  cursor 💡 Brillo LED, como en las otras pestañas.
- **💾 Exportar GIF**: guarda el GIF.

---

## Pestaña TEXTSCROLL — texto animado

![Pestaña TEXTSCROLL](images/textscroll_es.png)

Genera una animación directamente a partir de texto escrito, sin necesidad de imagen
de origen.

### 1. Texto

Cuadro de texto multilínea; el texto escrito se renderiza directamente como imagen
DMD (no se carga ningún archivo, así que no hay problemas de transparencia/PNG aquí).

### 2. Fuente

- **Familia**: lista de fuentes del sistema disponibles.
- **Tamaño**: 8 a 48 px.
- **Negrita** / **Cursiva**.
- **Color texto**: selector de color (vista previa junto a él).

### 3. Efectos de Texto

- **Efecto**: normal, 3d, fire, snow, ice, metal, neon, graffiti, pixel_art, outline,
  shadow.
- **Color fondo**: color de fondo del render de texto.
- **Efecto color** (activo solo con el efecto "normal"): none, rainbow, matrix, fire,
  gradient.

### 4. Animación

- **Tipo**: scroll_horizontal, scroll_vertical, scroll_wave, starwars,
  bounce_scroll, typewriter, explode, matrix_rain, spiral, shake, glitch, fade_in,
  static.
- **FPS**, **Velocidad**, **Duración (s)** (se amplía automáticamente para textos
  largos).
- **Auto-ajustar**: amplía automáticamente la duración para textos de más de 50
  caracteres.
- **Modo DMD / Forzar pixel-perfect**: casilla compartida con AUTO y MANUAL — cambia
  la vista previa a renderizado LED simulado (ver la
  [sección dedicada](#función-transversal-modo-dmd--forzar-pixel-perfect)).

### 5. Acciones

- **🎬 Generar Vista Previa**: calcula la animación y la muestra en el cuadro "Vista
  previa Animación" (número de fotogramas, FPS y tamaño estimado del GIF se indican
  bajo el lienzo — esta línea de información aún no está traducida y permanece en
  francés: "Durée: 4.5s | Taille estimée: 576.0 KB").
- **💾 Exportar GIF**: exporta la animación generada.

---

## Pestaña AJUSTES

![Pestaña AJUSTES](images/settings_es.png)

Ajustes globales de la aplicación (no ligados a ninguna imagen o proyecto en
particular):

- **🌍 Idioma**: Français / English / Español — requiere reiniciar la aplicación
  para aplicarse por completo.
- **Apariencia**: tema Oscuro o Claro (se aplica de inmediato).
- **Comportamiento**: casilla "Añadir tipo de animación al nombre" al exportar.
- **Exportar**: número de colores GIF por defecto (8 a 256).
- **Rendimiento**: casilla "Activar caché IA" y botón "🗑️ Vaciar caché".
- **Registros**: casilla "Guardar registros automáticamente" y botón "📄 Exportar
  registros" (escribe el registro de actividad en un archivo).

---

## Pestaña DEBUG

![Pestaña DEBUG](images/debug_es.png)

Registro de actividad de la aplicación en tiempo real — útil para diagnosticar un
error o entender qué está haciendo la IA internamente.

- **🗑️ Effacer logs** ("Borrar registros", aún no traducido): vacía la vista (y el
  historial interno de registros).
- **Auto-scroll**: mantiene siempre visible la última línea.
- **Filtrar**: ALL / INFO / WARNING / ERROR / DEBUG — solo muestra las entradas del
  nivel elegido.
- Cada línea lleva marca de tiempo y color según su nivel (verde = INFO, naranja =
  WARNING, rojo = ERROR, azul = DEBUG). Nota: los **mensajes de registro en sí**
  están escritos en francés en el código fuente de la aplicación y no se traducen
  con el ajuste de idioma — verá texto en francés en este panel sin importar el
  idioma de la interfaz seleccionado.

---

## Pestaña AYUDA

Muestra esta guía en el idioma elegido en AJUSTES (francés, inglés o español), con
los colores del tema. El menú al principio de la guía es clicable.
**🌐 Abrir en el navegador** abre el archivo de la guía con el programa asociado a los
archivos `.md` en su PC.

---

## Función transversal: Modo DMD / Forzar pixel-perfect

Esta casilla existe en las **cuatro** pestañas de generación (AUTO, MANUAL, VIDEO,
TEXTSCROLL) y apunta a **la misma variable**: marcarla en una pestaña la marca
automáticamente en las demás.

Tiene dos efectos combinados:

1. **Escalado**: impone un factor de escala entero exacto en lugar de un
   redimensionado a escala fraccionaria, para un alineado de píxeles perfecto en la
   cuadrícula DMD.
2. **Renderizado de la vista previa**: en los 4 lienzos de vista previa animada, cada
   fotograma se simula en estilo LED físico (puntos redondos separados por un marco
   oscuro, con un ligero halo) en lugar de un simple ampliado cuadrado — para
   visualizar en pantalla un render cercano al de la pantalla real del mueble. Si la
   casilla está desmarcada, la vista previa vuelve al render clásico (nítido,
   ampliado en cuadrado).

Dos extras disponibles en las mismas 4 pestañas, solo mientras la casilla está
marcada:

- **🔍 Lupa al pasar el cursor**: al pasar el cursor sobre el lienzo de vista previa
  aparece un icono de lupa en la esquina superior derecha. Al hacer clic se abre una
  ventana aparte con el renderizado LED ampliado, animada en vivo y sincronizada con
  la vista previa normal.
- **💡 Brillo LED**: control deslizante vertical junto al lienzo (0-100%, 50% por
  defecto). Simula el ajuste de brillo físico de un panel LED: más brillo empuja los
  colores hacia el blanco y aumenta el halo de bloom (un LED más brillante "sangra"
  más sobre sus vecinos); menos brillo oscurece y reduce el halo. 50% es el
  renderizado neutro por defecto.

---

## Función transversal: Puntuación de calidad y ventana Revisar

Cada GIF producido recibe una **puntuación de calidad de 0 a 100**, calculada sobre
sus imágenes: proporción de píxeles encendidos, contraste, ocupación de la pantalla,
número de imágenes y duración. Es una **ayuda para la revisión, no una decisión
automática**: nada se borra, y un GIF solo se sustituye si acepta una corrección
propuesta (ver más abajo).

| Nota | Puntuación |
|---|---|
| Excelente | 86 a 100 |
| Bueno | 71 a 85 |
| Aceptable | 51 a 70 |
| Bajo | 31 a 50 |
| Malo | 0 a 30 |

La puntuación va acompañada de **motivos** en el idioma de la interfaz (pantalla casi
vacía, contraste bajo, fondo lleno, animación demasiado corta…). Una pantalla
totalmente negra obtiene 0.

- **Procesamiento por lotes**: las puntuaciones se guardan en un archivo
  `dmd_scores.json` de la carpeta de salida. Un segundo lote en la misma carpeta
  completa este archivo en lugar de borrarlo.
- **Exportaciones MANUAL, VIDEO y TEXTSCROLL**: la puntuación aparece en el mensaje
  "GIF exportado".

**Ventana Revisar** (botón **🔍 Revisar** de la pestaña AUTO, que abre el último lote,
o propuesta al final de un lote cuando hay GIF bajos o malos):

- **📂 Otra carpeta…**: revisar otra carpeta de salida, en la misma ventana;

- lista de los GIF de la carpeta, **del más bajo al mejor**, con punto de color,
  puntuación, ruta y motivos; hacer clic en un encabezado de columna ordena la lista;
- hacer clic en una fila reproduce el GIF con el renderizado LED y, encima, muestra la
  **imagen de origen** con sus dimensiones, sobre un damero gris: las partes negras,
  invisibles en el DMD, siguen viéndose;
- **✎ Editar en MANUAL**: cuando las propuestas no convienen, abre el origen en la
  pestaña MANUAL con el ritmo del lote (FPS, duración mínima, velocidad de
  desplazamiento, bucle). Al exportar, la aplicación propone **sustituir este GIF** en
  la carpeta del lote (el original se aparta en `_a_revoir/_avant_correction`, nunca se
  borra) o guardar en otro lugar. MANUAL conserva su propio escalado: el GIF rehecho
  puede ser más pequeño o más corto que el del lote;
- **Umbral** (30 por defecto) y botón **Mover ≤ umbral a _a_revoir**: tras la
  confirmación (con el número exacto de archivos), los GIF afectados se **mueven,
  nunca se borran**, a una subcarpeta `_a_revoir` de la carpeta de salida,
  conservando la estructura de carpetas. Esta carpeta se ignora al volver a cargar la
  carpeta en la aplicación.
- **🪄 Proponer correcciones ≤ umbral**: para cada GIF con puntuación menor o igual al
  umbral, la aplicación prueba en segundo plano correcciones de la **imagen de origen**
  (el origen nunca se modifica) y rehace el GIF con los ajustes del lote original:
  - **vacío eliminado**: márgenes transparentes o negros quitados (sin cortar contenido);
  - **oscuros aclarados**: texto y contornos negros, invisibles en un DMD negro, pasados
    a claro, conservando los colores vivos;
  - **gamma** y **niveles**: un logo demasiado oscuro se aclara;
  - **inversión**: útil para logos oscuros de un solo color, pero cambia los colores de
    un logo de color; solo se propone si mejora claramente.

  La columna **Corrección** indica la ganancia posible (🪄 +62). Hacer clic en la fila
  muestra hasta dos propuestas con su vista previa LED y su puntuación: **✓ Conservar
  esta versión** sustituye el GIF y aparta el original en `_a_revoir/_avant_correction`
  (nunca se borra); **✗ Rechazar las propuestas** deja el GIF tal cual. Una propuesta
  debe ganar al menos 10 puntos. Las imágenes con fondo lleno (placa de color) no
  reciben propuesta, porque las correcciones también aclararían el fondo. La puntuación
  no mide el brillo: juzgue a simple vista, un renderizado apagado puede tener buena
  nota.

  El procesamiento por lotes guarda sus ajustes en `dmd_batch.json`. Para una carpeta
  generada por una versión anterior, la aplicación pide la carpeta de las imágenes de
  origen y usa los ajustes actuales de la pestaña AUTO.

La lista sigue fluida incluso con decenas de miles de GIF.

---

## Buenas prácticas y limitaciones conocidas

- **Imágenes con fondo transparente (PNG RGBA)**: gestionadas correctamente en todas
  partes (el fondo transparente siempre se compone sobre negro, nunca se deja tal
  cual) — evita halos blancos/de color alrededor de logotipos recortados.
- **Pestaña MANUAL, controles deslizantes en tiempo real**: sin protección contra el
  recorte de altas luces (a diferencia de AUTO) — con valores altos de
  contraste/saturación es posible "quemar" píxeles claros a blanco puro; es una
  decisión intencionada para dejar el control total al usuario.
- **Desplazamiento forzado desde (A/A)** (perfil): 2 es el valor usado para los
  logos Recalbox, elegido sobre un pack real de más de 54 000 logos. Más bajo, más
  logos se desplazan, en primer plano; más alto, más logos quedan fijos, más
  pequeños.
- **Logos animados y panel**: un logo que se desplaza se muestra más grande, por lo
  que enciende más LED. En un panel alimentado por un simple puerto USB, una imagen
  muy luminosa puede provocar reinicios: prevea una alimentación suficiente para el
  panel.
- **Inversión de logos oscuros**: la inversión también cambia los colores (un
  contorno naranja se vuelve azul). Solo se conserva si la puntuación mejora
  claramente; si el resultado no le convence, desmarque la opción o elija otra
  propuesta.
- **Localización parcial**: como se indica al principio de esta guía, varias cadenas
  de la interfaz (texto de arrastrar y soltar, algunas etiquetas de botones, el
  contenido de los paneles de Información de la Imagen, la línea de tamaño estimado
  en TEXTSCROLL, algunas palabras de los subtítulos de propuestas, y todos los
  mensajes de registro internos) permanecen fijas en francés sin importar el idioma
  seleccionado. Es una limitación conocida y registrada — no un error de esta guía
  traducida.

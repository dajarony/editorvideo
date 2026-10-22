# 🎬 AEGS — Editor de Vídeo Automático con IA

El editor permite previsualizar ocho segundos en una comparación lado a lado
(original a la izquierda, edición a la derecha), consultar el avance de FFmpeg
y cancelar un trabajo. El botón **Proponer con modelo local** usa Ollama instalado
en este ordenador; escribe el contrato propuesto en la caja JSON para revisarlo
antes de ejecutarlo. Configura `AEGS_MODELO` con el nombre de un modelo de Ollama.

El automontaje genera por defecto subtítulos desde `texto_narracion` y la duración
medida de cada escena. Este modo no necesita Whisper: reparte el tiempo entre
grupos de palabras, por lo que sirve para subtítulos legibles, no para sincronía
exacta de cada palabra. Para transcripción de la voz real, configura
`"subtitulos": {"generar": true, "modo": "transcripcion"}` e instala uno de
los extras de subtítulos.

> Sistema en Python para **mejorar, editar y montar vídeos automáticamente**.
> Combina FFmpeg, IA local (Whisper, Demucs, Real-ESRGAN) y un sistema de
> **contratos de herramientas seguras** controlable por lenguaje natural en español.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![FFmpeg required](https://img.shields.io/badge/requires-FFmpeg-red)](https://ffmpeg.org/)
[![Tests](https://img.shields.io/badge/tests-pytest-blue)](#-tests)

---

## ✨ ¿Qué es?

AEGS tiene **dos partes** que funcionan de forma independiente:

### 🅰️ Editor de vídeo (mejorar y editar cualquier vídeo)
Coges un vídeo cualquiera y lo dejas listo para publicar: más nítido, con mejor
color, subtítulos, formato vertical, voz limpia y efectos en los momentos que
elijas. Se controla por **interfaz gráfica**, por **comandos en español** o por
**contratos JSON**.

### 🅱️ Automontaje (proyecto.json → vídeo final)
Le pasas una carpeta con un `proyecto.json` que describe escenas, clips, textos a
narrar y música → te devuelve un MP4 con narración (Edge TTS), música con ducking,
transiciones reales y subtítulos sincronizados.

---

## 🧰 Funciones principales

| Función | Descripción |
|---|---|
| ✂️ **Cortar silencios** | Elimina silencios largos automáticamente |
| 🗣️ **Quitar muletillas** | Detecta y elimina *"umm, eh, este..."* (Whisper) |
| 🎨 **Color grading** | 4 estilos: natural, neutro, cálido, cinematográfico |
| ✨ **Mejora visual real** | Nitidez + brillo + color vivo + resolución ×2 (sin plastificar) |
| 🤖 **Super-resolución IA** | Ampliación ×4 con Real-ESRGAN |
| 📱 **Vertical 9:16** | Convierte a formato TikTok / Reels / Shorts |
| 💬 **Subtítulos automáticos** | Transcribe y quema subtítulos (faster-whisper) |
| 🎙️ **Aislar voz / quitar música** | Separación de voz con IA (Demucs) |
| 🔊 **Audio fades** | Fundidos suaves de audio en inicio y fin |
| ⏱️ **Efectos por momento** | Texto, imagen/logo, zoom y corte en el segundo exacto |
| 🧠 **Editor por comandos** | Órdenes en español → contrato validado |
| 🎬 **Automontaje** | `proyecto.json` → vídeo completo con narración y música |

---

## 🚀 Instalación

### 1. Requisitos del sistema

**FFmpeg** y **ffprobe** deben estar en el `PATH`:

- **Windows**: [ffmpeg.org/download.html](https://ffmpeg.org/download.html) → añadir a `PATH`
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### 2. Clonar e instalar dependencias

```bash
git clone https://github.com/dajarony/editorvideo.git
cd editorvideo
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r automontaje/requirements.txt
```

### 3. Dependencias de IA (recomendadas)

```bash
pip install customtkinter pillow        # interfaz gráfica
pip install edge-tts                    # narración (automontaje)
pip install faster-whisper              # subtítulos y transcripción
pip install demucs torch                # aislar voz / quitar música (opcional, pesado)
```

### 4. Real-ESRGAN — super-resolución IA (opcional)

La ampliación ×4 con IA necesita el ejecutable portable de Real-ESRGAN:

1. Descarga `realesrgan-ncnn-vulkan` desde
   [github.com/xinntao/Real-ESRGAN/releases](https://github.com/xinntao/Real-ESRGAN/releases)
2. Descomprime dentro de la carpeta `realesrgan/` en la raíz del proyecto:

```
realesrgan/
├── realesrgan-ncnn-vulkan.exe
└── models/
    ├── realesrgan-x4plus.bin / .param
    └── realesrgan-x4plus-anime.bin / .param
```

> Sin Real-ESRGAN el resto del programa funciona igual; solo se desactiva la
> opción "Ampliar ×4 con IA".

---

## ⚡ Uso

### Modo 1 — Interfaz gráfica (lo más cómodo)

```bash
python interfaz.py
```

Abre una ventana donde seleccionas un vídeo o imagen, marcas las mejoras que
quieres y pulsas **PROCESAR**. Incluye:

- Casillas para cada mejora (silencios, color, subtítulos, vertical, voz...)
- **Editor por comandos** — escribe lo que quieres en español
- **Contrato de herramientas** — caja JSON con botones *Validar* / *Ejecutar*

### Modo 2 — Editor por comandos

Escribe órdenes en español y el sistema las traduce a ajustes seguros:

```
mejora calidad media, quita silencios y hazlo vertical para reels
```
```
en el segundo 12 pon texto "Idea clave" durante 3 segundos
en 00:18 zoom suave durante 2 segundos
corta de 7 a 9
```

### Modo 3 — Contrato de herramientas (JSON)

La IA (o tú) describe la edición como un contrato; el sistema lo **valida** y
lo **ejecuta paso a paso de forma segura**:

```json
{
  "herramientas": [
    {"herramienta": "mejora_real", "parametros": {"nivel": "media"}},
    {"herramienta": "texto", "parametros": {"texto": "Mira esto", "inicio": 12, "duracion": 3}},
    {"herramienta": "zoom", "parametros": {"inicio": 20, "duracion": 2, "intensidad": "suave"}},
    {"herramienta": "vertical_9_16", "parametros": {}},
    {"herramienta": "subtitulos", "parametros": {"idioma": "es"}}
  ]
}
```

**Los segundos son los del vídeo original.** En «corta de 7 a 9 y pon un texto en el
segundo 12», el 12 es el del vídeo que tienes delante: como el corte quita 2 s, el
texto aparece en el segundo 10 del resultado, sobre la misma imagen. Si un momento
pedido cae en un tramo que otro paso ya quitó, se usa el siguiente que queda y se
avisa; un corte de algo ya quitado se omite. Para que cada paso use los segundos del
vídeo que le llega, añade `"tiempos": "resultado"` al contrato.

### Modo 4 — Mejorar un vídeo por CLI

```bash
python mejorar_video.py "mi_video.mp4" --estilo natural_claro
python mejorar_video.py "mi_video.mp4" --comando "hazlo vertical, mejora fuerte y ponle subtitulos"
```

### Modo 5 — Automontaje (proyecto.json → vídeo)

```bash
python automontaje/main.py /ruta/a/mi_proyecto/
```

| Flag | Qué hace |
|---|---|
| `--skip-subs` | Omite la fase de subtítulos |
| `--skip-tts` | No regenera narraciones; usa las existentes |
| `--no-cache` | Fuerza regenerar todas las voces |
| `--keep-temp` | Conserva los clips temporales |
| `--srt-sidecar` | Genera SRT pero no lo quema en el vídeo |
| `--solo-narracion` | Valida, genera la voz y escribe `output/narracion_duraciones.json`; no monta (los clips aún pueden no existir) |
| `--duracion-estricta` | Cada clip debe durar lo que su escena (±1 fotograma): si no, falla en vez de recortar o congelar; solo cortes `cut` |
| `-v, --verbose` | Logging detallado |

---

## 🛠️ Herramientas del sistema de contratos

El núcleo seguro registra **11 herramientas**. Cada una valida sus parámetros
antes de tocar el vídeo:

| Herramienta | Acción | Parámetros principales |
|---|---|---|
| `cortar_silencios` | Quita silencios largos | `umbral_db`, `duracion_min` |
| `color_grading` | Color grading protegido | `estilo` |
| `mejora_real` | Nitidez + color + ×2 | `nivel` |
| `vertical_9_16` | Formato vertical | — |
| `subtitulos` | Subtítulos automáticos | `idioma`, `modelo` |
| `limpiar_voz` | Aísla voz / quita música | `nivel` |
| `fades_audio` | Fades de audio | `duracion_ms` |
| `corte` | Quita un tramo del vídeo | `inicio`, `fin` |
| `texto` | Texto en pantalla | `texto`, `inicio`, `duracion`, `posicion` |
| `imagen` | Logo/imagen superpuesta | `archivo`, `inicio`, `duracion`, `posicion` |
| `zoom` | Zoom suave (punch-in) | `inicio`, `duracion`, `intensidad` |

**Filosofía de seguridad:** la IA nunca ejecuta FFmpeg en crudo. Solo puede pedir
herramientas registradas; un **validador maestro** revisa el contrato y, si algo
está mal, lo rechaza con un error claro **sin tocar el vídeo**.

---

## 📂 Estructura del proyecto

```
editorvideo/
├── interfaz.py                 ← interfaz gráfica (editor de vídeo)
├── mejorar_video.py            ← CLI para mejorar un vídeo
├── superresolucion_video.py    ← CLI de super-resolución Real-ESRGAN
├── automontaje/
│   ├── main.py                 ← pipeline proyecto.json → vídeo
│   ├── modulos/
│   │   ├── mejoras.py          ← mejoras de vídeo (silencios, color, voz...)
│   │   ├── efectos.py          ← efectos por momento (corte, texto, zoom...)
│   │   ├── contrato_edicion.py ← registro de herramientas + validador + ejecutor
│   │   ├── editor_comandos.py  ← comandos en español → contrato
│   │   ├── subtitulos.py       ← transcripción y subtítulos
│   │   ├── narracion.py        ← narración con Edge TTS
│   │   ├── mezclador_audio.py  ← mezcla de audio con ducking
│   │   ├── montador_video.py   ← montaje y transiciones
│   │   └── validador.py        ← validación de proyectos
│   ├── tests/                  ← suite de tests (pytest)
│   └── doc/                    ← documentación técnica completa
└── realesrgan/                 ← Real-ESRGAN (descarga aparte)
```

---

## 🧪 Tests

```bash
pip install -e "automontaje[dev]"   # desde la raíz, sin PyTorch
python -m pytest automontaje/tests -q
```

Los 4 omitidos habituales llaman al servicio real de Edge TTS y solo se ejecutan con `AEGS_TEST_INTERNET=1`. Sin FFmpeg (ni en el PATH ni en `AEGS_FFMPEG`/`AEGS_FFPROBE`) se omiten además las pruebas de integración con vídeo real. CI (GitHub Actions) ejecuta la suite en Ubuntu con Python 3.12 y 3.13.

---

## 📚 Documentación

| Documento | Contenido |
|---|---|
| [ARQUITECTURA.md](automontaje/doc/ARQUITECTURA.md) | Diseño técnico del sistema |
| [ESTANDAR_EDICION.md](automontaje/doc/ESTANDAR_EDICION.md) | Estándar de edición y herramientas |
| [CONTRATO_JSON.md](automontaje/doc/CONTRATO_JSON.md) | Especificación del proyecto.json |
| [GUIA_COMPLETA.md](automontaje/doc/GUIA_COMPLETA.md) | Guía de uso para no-técnicos |
| [INSTALACION.md](automontaje/doc/INSTALACION.md) | Setup paso a paso |
| [API_MODULOS.md](automontaje/doc/API_MODULOS.md) | Referencia de funciones por módulo |
| [CHANGELOG.md](automontaje/doc/CHANGELOG.md) | Historial de versiones |
| [ROADMAP.md](automontaje/doc/ROADMAP.md) | Mejoras planificadas |
| [TESTING.md](automontaje/doc/TESTING.md) | Cómo ejecutar los tests |

---

## 🗺️ Roadmap

- [x] Mejora visual real sin plastificar
- [x] Subtítulos automáticos (faster-whisper)
- [x] Aislar voz / quitar música (Demucs)
- [x] Sistema de contratos de herramientas seguras
- [x] Efectos por momento (corte, texto, imagen, zoom)
- [x] Editor por comandos en español
- [ ] Presets de 1 clic (Reels / YouTube / Podcast)
- [ ] Preview antes/después
- [ ] Cola de procesamiento por lotes
- [ ] IA que sugiere contratos desde la transcripción
- [ ] CI con GitHub Actions

---

## ⚠️ Notas honestas

- Un vídeo de **baja resolución** tiene un límite: los filtros limpian y mejoran,
  pero no inventan detalle que no existe.
- La **super-resolución IA** y la **separación de voz** son lentas en vídeos largos
  (procesan con IA fotograma a fotograma / por análisis).
- Los **subtítulos automáticos** dependen de que la voz se oiga clara. Con mucho
  ruido de fondo, ninguna IA transcribe bien.

---

## 📄 Licencia

[MIT](LICENSE) — Copyright (c) 2026 dajarony

---

## 🤝 Contribuir

PRs bienvenidos. Por favor:

1. Mantén la cabecera **SUME DOCBLOCK** en cada módulo.
2. Añade tests para la lógica nueva.
3. Sigue la convención de commits: `tipo: descripción` (`feat:`, `fix:`, `docs:`...).

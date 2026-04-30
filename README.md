# 🎬 AEGS — Automontaje de Vídeo

> Sistema en Python que convierte un `proyecto.json` en un vídeo final completo con narración (Edge TTS), música con ducking, transiciones reales y subtítulos sincronizados (Whisper).

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![FFmpeg required](https://img.shields.io/badge/requires-FFmpeg-red)](https://ffmpeg.org/)

---

## ✨ ¿Qué hace?

Le pasas una carpeta con un `proyecto.json` que describe escenas, clips de vídeo, textos a narrar y música → te devuelve un MP4 listo para publicar.

**Pipeline en 5 fases**:

```
Validar  →  Narrar (TTS)  →  Mezclar audio  →  Montar vídeo  →  Subtitular
  ↓             ↓                 ↓                  ↓              ↓
proyecto.json   MP3 por        WAV maestro      MP4 con         SRT + MP4
                escena         con ducking      transiciones    subtitulado
```

Cada fase es independiente, valida sus entradas, y aborta limpiamente si algo falla.

---

## 🚀 Instalación

### 1. Requisitos del sistema

Necesitas **FFmpeg** y **ffprobe** en el `PATH`:

- **Windows**: [ffmpeg.org/download.html](https://ffmpeg.org/download.html) (añadir a `PATH`)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### 2. Dependencias Python

```bash
git clone https://github.com/dajarony/editorvideo.git
cd editorvideo/automontaje
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

---

## ⚡ Uso rápido

```bash
python main.py /ruta/a/mi_proyecto/
```

### Flags útiles

| Flag             | Qué hace                                                  |
|------------------|-----------------------------------------------------------|
| `--skip-subs`    | Omite la fase de subtítulos                               |
| `--skip-tts`     | No regenera narraciones; usa las existentes               |
| `--no-cache`     | Fuerza regenerar todas las voces (ignora la caché)        |
| `--keep-temp`    | Conserva la carpeta de clips temporales                   |
| `--srt-sidecar`  | Genera SRT pero **no** lo quema en el vídeo               |
| `-v, --verbose`  | Logging detallado                                          |

```bash
python main.py ./mi_video/ --skip-subs --keep-temp
```

---

## 📦 Estructura de un proyecto

```
mi_proyecto/
├── proyecto.json            ← receta del vídeo
├── clips/
│   ├── escena_intro.mp4
│   └── escena_cierre.mp4
├── musica/
│   └── ambient.mp3
└── output/                  ← se genera al ejecutar
    ├── narracion/           ← MP3s por escena
    ├── narracion_cache.json ← caché TTS por hash
    ├── audio_mezclado.wav
    ├── timeline.json
    ├── video_final.mp4
    ├── subtitulos.srt
    └── video_final_subtitulado.mp4
```

Mira [`automontaje/plantillas/proyecto_ejemplo.json`](automontaje/plantillas/proyecto_ejemplo.json) para una plantilla completa.

---

## 🎚️ Transiciones disponibles

| Transición          | Efecto                                                   |
|---------------------|----------------------------------------------------------|
| `cut`               | Corte seco                                               |
| `fade_from_black`   | Fundido desde negro al inicio del clip                   |
| `fade_to_black`     | Fundido a negro al final del clip                        |
| `dip_to_black`      | Pequeño fade out + fade in en bordes (sin solapar)       |
| `crossfade`         | **xfade real** entre clips adyacentes (filter_complex)   |

> El sistema detecta automáticamente si tienes `crossfade` y cambia a un grafo `filter_complex` con `xfade` real, en vez del concat-demuxer rápido.

---

## 🧠 Caché TTS

Cada narración se identifica por `SHA-1(texto + voz + velocidad)`. Si vuelves a renderizar el mismo proyecto sin tocar texto/voz, **no se regenera ningún MP3** → ahorras tiempo y peticiones a Edge TTS.

Para forzar regeneración: `--no-cache`.

---

## 🎙️ Música con ducking

La música se baja automáticamente cuando el narrador habla, con fades suavizados de 200 ms en los bordes. No hay cortes bruscos de volumen.

```json
"musica": {
  "fuente": "archivo",
  "archivo": "musica/ambient.mp3",
  "volumen_base": 0.30,
  "volumen_durante_voz": 0.08,
  "fade_in_segundos": 3.0,
  "fade_out_segundos": 5.0
}
```

---

## 📝 Subtítulos sincronizados

Whisper transcribe la pista **limpia** de voz (sin música) por escena, y los timestamps se desplazan al offset matemático del timeline. Resultado: subtítulos que cuadran al milisegundo con el vídeo final.

```json
"subtitulos": {
  "generar": true,
  "fuente": "Arial",
  "tamano": 24,
  "sidecar": false   // si true → solo SRT, no quema
}
```

---

## 📚 Documentación completa

| Documento | Contenido |
|-----------|-----------|
| [ROADMAP.md](automontaje/doc/ROADMAP.md) | Mejoras planificadas, fases A–I, visión N8N |
| [CHANGELOG.md](automontaje/doc/CHANGELOG.md) | Historial de versiones y bugs resueltos |
| [ARQUITECTURA.md](automontaje/doc/ARQUITECTURA.md) | Diseño técnico del sistema |
| [HISTORIAL_DISENO.md](automontaje/doc/HISTORIAL_DISENO.md) | Decisiones de arquitectura del diseño inicial |
| [CONTRATO_JSON.md](automontaje/doc/CONTRATO_JSON.md) | Especificación completa del proyecto.json |
| [GUIA_COMPLETA.md](automontaje/doc/GUIA_COMPLETA.md) | Guía de uso para no-técnicos |
| [INSTALACION.md](automontaje/doc/INSTALACION.md) | Setup paso a paso |
| [API_MODULOS.md](automontaje/doc/API_MODULOS.md) | Referencia de funciones por módulo |
| [TESTING.md](automontaje/doc/TESTING.md) | Cómo ejecutar los tests |

---

## 🧪 Tests

```bash
cd automontaje
pip install -r requirements.txt   # incluye pytest
pytest -v
```

---

## 🛠️ Roadmap

- [ ] Soporte de imágenes estáticas como "clip"
- [ ] Progreso de FFmpeg en consola (parsing %)
- [ ] CI con GitHub Actions
- [ ] Descarga automática de FFmpeg si no está
- [ ] Soporte de B-roll superpuesto
- [ ] Plantilla CLI interactiva (`aegs init`)

---

## 📄 Licencia

[MIT](LICENSE) — Copyright (c) 2026 dajarony

---

## 🤝 Contribuir

PRs bienvenidos. Por favor:
1. Mantén el patrón de SUME DOCBLOCK al cabecera de cada módulo.
2. Añade tests para nueva lógica.
3. Sigue la convención de mensajes: `tipo: descripción corta` (`fix:`, `feat:`, `docs:`, etc.).

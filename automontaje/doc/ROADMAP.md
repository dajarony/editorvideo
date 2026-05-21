# 🗺️ AEGS — Roadmap de Mejoras y Actualizaciones

> Documento maestro de planificación. Recoge todo lo discutido, lo implementado y lo que viene.
> Última actualización: 2026-04-30 | Versión actual: **0.2.0**

---

## Estado actual del sistema (v0.2.0)

### Pipeline completo funcionando

```
proyecto.json
      │
      ▼
FASE 0 ─ Validador          → verifica estructura, clips, voz, tiempos
FASE 1 ─ Narración TTS      → Edge TTS + caché SHA-1 + reintentos backoff
FASE 2 ─ Mezcla de audio    → ducking suavizado 200ms, loop música, WAV maestro
FASE 3 ─ Montaje de vídeo   → xfade real (filter_complex), GOP fijo, 1080p
FASE 4 ─ Subtítulos         → Whisper sobre MP3 limpio + offset matemático
      │
      ▼
video_final.mp4 + subtitulos.srt
```

### Lo que ya está resuelto

| Módulo | Estado | Notas |
|--------|--------|-------|
| `validador.py` | ✅ Hardening completo | narrador como dict, clip_inicio vs duración, tipado |
| `narracion.py` | ✅ Caché SHA-1 + backoff | 3 reintentos con espera progresiva |
| `mezclador_audio.py` | ✅ Fix div-zero | pista vacía y música 0ms protegidas |
| `montador_video.py` | ✅ xfade real | filter_complex encadenado + GOP fijo |
| `subtitulos.py` | ✅ UTF-8 BOM + sidecar | FFmpeg Windows compatible |
| `main.py` | ✅ argparse CLI | --skip-tts, --skip-subs, --no-cache, --keep-temp, --srt-sidecar |
| `utilidades.py` | ✅ verificar_ffmpeg + hash_tts | check al arranque + SHA-1 |
| `configuracion.py` | ✅ constantes centralizadas | caché, reintentos, backoff, fade |

---

## 📋 Mejoras planificadas

### 🔴 FASE A — Formatos de exportación para redes sociales

**Prioridad: Alta · Dificultad: Media · Impacto: Muy alto**

Objetivo: un solo proyecto.json → 3 formatos automáticos.

```bash
python main.py ./mi_proyecto/ --formatos youtube,reels,feed
```

**Salidas:**
```
output/
├── video_final_youtube.mp4     ← 1920x1080  (16:9)
├── video_final_reels.mp4       ← 1080x1920  (9:16)  TikTok / Instagram Reels
└── video_final_feed.mp4        ← 1080x1080  (1:1)   Instagram Feed
```

**Técnica para vertical (9:16):**
- Opción A (simple): vídeo centrado + blur lateral del mismo frame
- Opción B (pro): smart crop por detección de movimiento con FFmpeg `cropdetect`

**Subtítulos adaptados por formato:**
- YouTube: parte baja, tamaño 28
- Reels/TikTok: centrado, tamaño 40, fuente más gruesa
- Feed: parte baja, tamaño 32

**Archivos a crear/modificar:**
- `modulos/exportador.py` (nuevo)
- `main.py` — añadir flag `--formatos`
- `configuracion.py` — añadir `FORMATOS_EXPORTACION`

---

### 🔴 FASE B — Integración directa con Higgsfield AI

**Prioridad: Alta · Dificultad: Media · Impacto: Muy alto**

Objetivo: generar clips de vídeo IA directamente desde el JSON, sin pasos manuales.

**JSON extendido:**
```json
{
  "id": "escena_intro",
  "clip": null,
  "clip_ia": {
    "fuente": "higgsfield",
    "imagen_prompt": "hacker frente a pantallas azules, noir, cinematográfico",
    "video_prompt": "cámara acercándose lentamente, código fluyendo",
    "modelo_imagen": "nano_banana_2",
    "modelo_video": "grok_video",
    "duracion": 5
  },
  "texto_narracion": "En el mundo digital..."
}
```

**Flujo automático:**
```
AEGS lee clip_ia → genera imagen → anima → descarga → monta como clip normal
```

**Archivos a crear/modificar:**
- `modulos/generador_clips_ia.py` (nuevo)
- `modulos/validador.py` — aceptar `clip` = null si hay `clip_ia`
- `configuracion.py` — `HIGGSFIELD_MODEL_IMAGEN`, `HIGGSFIELD_MODEL_VIDEO`

**Caché de clips IA:** igual que TTS, hash del prompt → reutiliza si ya existe.

---

### 🟡 FASE C — Imágenes estáticas como clip (Ken Burns)

**Prioridad: Media · Dificultad: Baja · Impacto: Alto**

Objetivo: aceptar JPG/PNG como "clip" y convertirlo a vídeo con movimiento automático.

**Tipos de movimiento:**
```json
"clip": "fotos/hacker.jpg",
"efecto_ken_burns": "zoom_in"   // zoom_in, zoom_out, pan_left, pan_right, auto
```

**Implementación FFmpeg:**
```
zoompan=z='zoom+0.001':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:fps=30
```

**Detección automática:** si la extensión es `.jpg/.jpeg/.png/.webp` → activa Ken Burns automáticamente.

**Archivos a modificar:**
- `modulos/montador_video.py` — detectar imagen y preprocesar
- `modulos/validador.py` — aceptar imágenes como clips válidos

---

### 🟡 FASE D — Múltiples voces por escena

**Prioridad: Media · Dificultad: Baja · Impacto: Medio**

Objetivo: cada escena puede tener su propia voz (diálogos, entrevistas, diferentes narradores).

**JSON extendido:**
```json
{
  "id": "escena_entrevista",
  "narrador_override": {
    "voz": "es-ES-ElviraNeural",
    "velocidad": "+0%"
  },
  "texto_narracion": "La experta en seguridad explica..."
}
```

**Archivos a modificar:**
- `modulos/narracion.py` — leer `narrador_override` por escena
- `modulos/validador.py` — validar voz del override

---

### 🟡 FASE E — Títulos y lower thirds en pantalla

**Prioridad: Media · Dificultad: Media · Impacto: Alto**

Objetivo: texto superpuesto sobre el vídeo sin editor externo.

**JSON extendido:**
```json
{
  "id": "escena_intro",
  "titulo_pantalla": {
    "texto": "Capítulo 1: El Hacker",
    "posicion": "top",           // top, center, bottom, lower_third
    "fuente": "Arial Bold",
    "tamano": 56,
    "color": "white",
    "fondo": "rgba(0,0,0,0.6)",
    "aparece_en_seg": 1.0,
    "desaparece_en_seg": 4.0
  }
}
```

**Lower thirds** (estilo documental/TV):
```
┌─────────────────────────────────┐
│  Dr. Carlos Mendez              │ ← nombre
│  Experto en Ciberseguridad      │ ← cargo
└─────────────────────────────────┘
```

**Archivos a crear/modificar:**
- `modulos/graficos.py` (nuevo) — gestiona overlays de texto
- `modulos/montador_video.py` — integrar filtros drawtext

---

### 🟡 FASE F — B-roll superpuesto

**Prioridad: Media · Dificultad: Alta · Impacto: Alto**

Objetivo: vídeo secundario encima del principal (típico de documentales).

```json
{
  "id": "escena_explicacion",
  "clip": "clips/presentador.mp4",
  "broll": {
    "clip": "clips/codigo_pantalla.mp4",
    "inicio_seg": 2.0,
    "fin_seg": 6.0,
    "opacidad": 1.0,
    "posicion": "fullscreen"    // fullscreen, pip_topright, pip_bottomleft
  }
}
```

---

### 🟢 FASE G — Modo draft / preview rápido

**Prioridad: Baja · Dificultad: Muy baja · Impacto: Medio**

```bash
python main.py ./mi_proyecto/ --borrador
```

Renderiza en 480p con `-preset ultrafast -crf 35` → 10x más rápido para revisar montaje antes del render final.

---

### 🟢 FASE H — Intro y outro automáticos

**Prioridad: Baja · Dificultad: Media · Impacto: Medio**

El proyecto genera automáticamente:
- **Intro**: fondo animado + título del documental + música crescendo
- **Outro**: créditos con lista de clips usados + fade out

Desde el JSON:
```json
{
  "titulo": "Ciberseguridad: La Amenaza Interna",
  "intro": { "duracion_seg": 4, "estilo": "tech" },
  "outro": { "duracion_seg": 5, "creditos": true }
}
```

---

### 🟢 FASE I — GUI Web (Gradio / Flask)

**Prioridad: Baja · Dificultad: Alta · Impacto: Muy alto**

Interfaz en el navegador: rellenas un formulario → lanzas el render → ves el progreso → descargas el vídeo.

Sin tocar JSON ni terminal. Ideal para compartir con otras personas.

```bash
python app.py  →  http://localhost:7860
```

---

## 🤖 FASE ULTIMATE — N8N + AEGS: Estudio Automático 24/7

**Prioridad: Futura · Dificultad: Alta · Impacto: Brutal**

### Visión completa

```
Trigger (tiempo / RSS / comentario / manual)
        │
        ▼
   N8N Workflow
        │
        ├─► API de IA (LLM)  →  genera guión JSON automáticamente
        │
        ├─► Higgsfield  →  genera clips de vídeo IA
        │
        ├─► AEGS        →  monta vídeo completo
        │
        └─► Publicación automática
               ├── YouTube (título + descripción + tags)
               ├── TikTok Reels (formato vertical)
               └── Instagram Feed (formato cuadrado)
```

### Casos de uso reales

| Trigger | Resultado |
|---------|-----------|
| Cada lunes 9am | Nuevo episodio del canal de ciberseguridad |
| Nueva noticia en RSS | Vídeo de 30s sobre la noticia publicado en 10 min |
| Comentario en YouTube | Vídeo de respuesta generado automáticamente |
| Nuevo artículo en blog | Resumen en vídeo para todas las redes |
| Manual desde Telegram | Envías el tema, recibes el vídeo en 15 minutos |

### Stack técnico

```
N8N (self-hosted, gratis)
  │
  ├── API de IA (LLM)  (~0.01$/guión)
  ├── Higgsfield  (créditos según plan)
  ├── AEGS        (tu herramienta, cero coste)
  ├── YouTube API (gratis con límites)
  ├── TikTok API  (gratis con límites)
  └── Instagram Graph API (gratis con límites)

Coste estimado por vídeo: 0.05$ - 0.50$ dependiendo de clips IA usados
```

### Nodos N8N del workflow

```
[Cron / RSS / Webhook]
        ↓
[HTTP Request → API de IA (LLM)]  ← genera proyecto.json
        ↓
[Execute Command → AEGS]      ← renderiza el vídeo
        ↓
[IF formato = reels] ─────────────────────┐
        ↓                                  ↓
[YouTube Upload]              [TikTok + Instagram Upload]
        ↓
[Telegram Notification]  ← te avisa cuando está listo
```

---

## 📅 Orden de implementación recomendado

```
v0.3.0  ─ FASE A (formatos redes)  +  FASE C (imágenes Ken Burns)
v0.4.0  ─ FASE B (Higgsfield JSON) +  FASE D (múltiples voces)
v0.5.0  ─ FASE E (títulos pantalla) + FASE G (modo draft)
v0.6.0  ─ FASE F (B-roll) + FASE H (intro/outro)
v0.7.0  ─ FASE I (GUI Web)
v1.0.0  ─ N8N integration completa → Estudio automático 24/7
```

---

## 📁 Estructura de archivos del proyecto (actual)

```
editor de video automatico/
│
├── README.md                          ← entrada principal al proyecto
├── LICENSE                            ← MIT
├── .gitignore
│
└── automontaje/                       ← código fuente
    ├── main.py                        ← CLI + orquestador
    ├── configuracion.py               ← constantes globales
    ├── requirements.txt               ← dependencias pip
    ├── pyproject.toml                 ← metadata del paquete
    │
    ├── modulos/
    │   ├── utilidades.py              ← ffmpeg check, hash TTS, logging
    │   ├── validador.py               ← Fase 0
    │   ├── narracion.py               ← Fase 1 (TTS + caché)
    │   ├── mezclador_audio.py         ← Fase 2 (ducking)
    │   ├── montador_video.py          ← Fase 3 (xfade real)
    │   └── subtitulos.py              ← Fase 4 (Whisper + SRT)
    │
    ├── doc/                           ← documentación completa
    │   ├── ROADMAP.md                 ← este archivo
    │   ├── CHANGELOG.md               ← historial de versiones
    │   ├── ARQUITECTURA.md            ← diseño técnico del sistema
    │   ├── API_MODULOS.md             ← referencia de funciones
    │   ├── CONTRATO_JSON.md           ← spec del proyecto.json
    │   ├── GUIA_COMPLETA.md           ← guía de uso para no-técnicos
    │   ├── GUIA_USO.md                ← referencia rápida CLI
    │   ├── INSTALACION.md             ← setup paso a paso
    │   └── TESTING.md                 ← cómo ejecutar los tests
    │
    ├── plantillas/
    │   └── proyecto_ejemplo.json      ← plantilla base con todos los campos
    │
    └── tests/
        ├── conftest.py
        ├── test_validador.py
        ├── test_narracion.py
        ├── test_montador.py
        ├── test_subtitulos.py
        ├── test_configuracion_y_audio.py
        └── test_utilidades.py
```

---

*Documento generado y mantenido por el equipo AEGS.*
*Para proponer nuevas mejoras, abrir un issue en https://github.com/dajarony/editorvideo/issues*

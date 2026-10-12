# 🎬 AEGS — Guía Completa: Instalación, Preparación y Uso

> Todo lo que necesitas para crear vídeos con narración automática, desde cero.

---

## 📋 PARTE 1: ¿QUÉ HACE ESTE SISTEMA?

Este sistema toma:
- **Clips de vídeo** (tus grabaciones, stock footage, lo que sea)
- **Un archivo JSON** donde escribes qué quieres que diga el narrador en cada escena
- **Un archivo de música** (opcional)

Y produce automáticamente:
- Un **vídeo final** con narración de voz IA, música de fondo con ducking, transiciones suaves y subtítulos

**Tú solo escribes el texto. El sistema hace todo lo demás.**

---

## 🔧 PARTE 2: INSTALACIÓN (UNA SOLA VEZ)

### Paso 1: Python

Necesitas Python 3.11 o superior.

**¿Ya lo tienes?** Abre PowerShell y ejecuta:
```powershell
python --version
```
Si dice `Python 3.11.x` o superior, perfecto. Si no, descárgalo de:
👉 https://www.python.org/downloads/

> ⚠️ **IMPORTANTE**: Al instalar, marca la casilla **"Add Python to PATH"**.

---

### Paso 2: FFmpeg

FFmpeg es el motor que procesa vídeo y audio. Es obligatorio.

**Instalación rápida (recomendada):**
```powershell
winget install --id Gyan.FFmpeg -e
```

**Verificar que funciona** (cierra y reabre PowerShell después de instalar):
```powershell
ffmpeg -version
ffprobe -version
```

Si ves la versión, está listo. Si dice "no reconocido", necesitas reiniciar la terminal o añadir FFmpeg al PATH manualmente.

**Instalación manual (si winget no funciona):**
1. Ve a https://www.gyan.dev/ffmpeg/builds/
2. Descarga `ffmpeg-release-full.7z`
3. Extrae en `C:\ffmpeg\`
4. Añade `C:\ffmpeg\bin\` al PATH del sistema:
   - Buscar "Variables de entorno" en el menú Inicio
   - Clic en "Variables de entorno..."
   - En "Path" del sistema → Editar → Nuevo → `C:\ffmpeg\bin`
   - Aceptar todo y reiniciar PowerShell

---

### Paso 3: Dependencias Python

Abre PowerShell y navega a la carpeta del sistema:

```powershell
cd "C:\ruta\a\editorvideo"
pip install -e "automontaje[dev]"
# Opcional, solo para subtítulos automáticos (instala PyTorch, varios GB):
pip install -e "automontaje[subtitulos]"
```

Esto instala:
| Paquete | Para qué sirve |
|---------|----------------|
| `edge-tts` | Genera la voz del narrador (gratis, Microsoft) |
| `pydub` | Mezcla audio, aplica ducking |
| `audioop-lts` | Compatibilidad con Python 3.13+ |
| `openai-whisper` | Genera subtítulos automáticos (OPCIONAL) |

> **Nota sobre Whisper**: Es pesado (instala PyTorch, varios GB) y va en el extra opcional `subtitulos`. Si NO necesitas subtítulos automáticos, puedes omitirlo: pon `"generar": false` en el JSON y todo funciona sin él.

---

### Paso 4: Verificar que Todo Funciona

```powershell
cd "C:\ruta\a\editorvideo"
python -m pytest automontaje/tests -q
```

Deberías ver `133 passed, 4 skipped`: los 4 omitidos son los que llaman a Edge TTS real y solo se ejecutan con `AEGS_TEST_INTERNET=1`. Sin FFmpeg se omiten además los 16 casos de integración que montan vídeo.

---

## 📁 PARTE 3: PREPARAR UN PROYECTO

### Estructura de Carpetas

Crea una carpeta nueva para tu proyecto:

```
mi_documental/
├── proyecto.json          ← Lo creas tú (el "guión")
├── clips/                 ← Tus clips de vídeo
│   ├── intro.mp4
│   ├── desarrollo.mp4
│   └── cierre.mp4
└── musica/                ← Tu música de fondo (opcional)
    └── fondo.mp3
```

### Reglas Importantes

1. **Los clips** pueden ser MP4, AVI, MOV, MKV — cualquier formato que FFmpeg soporte
2. **La música** es opcional. Sin ella, el vídeo tendrá solo narración
3. **Las rutas** en el JSON son relativas a la carpeta del proyecto
4. **Cada escena** necesita un clip de vídeo y un texto de narración
5. **Los IDs** de escena deben ser únicos (sin espacios ni caracteres especiales)

---

## ✍️ PARTE 4: ESCRIBIR EL PROYECTO.JSON

Este es el corazón del sistema. Aquí defines todo lo que el vídeo debe contener.

### Plantilla Mínima (copiar y pegar)

```json
{
  "titulo": "Mi Primer Vídeo",
  "idioma": "es",

  "narrador": {
    "voz": "es-ES-AlvaroNeural",
    "velocidad": "-5%"
  },

  "subtitulos": {
    "generar": false
  },

  "escenas": [
    {
      "id": "escena_01",
      "clip": "clips/mi_clip.mp4",
      "texto_narracion": "Aquí va el texto que el narrador dirá en esta escena."
    }
  ]
}
```

### Plantilla Completa (con todas las opciones)

```json
{
  "titulo": "Mi Documental Completo",
  "idioma": "es",
  "resolucion": "1920x1080",
  "fps": 30,

  "narrador": {
    "voz": "es-ES-AlvaroNeural",
    "velocidad": "-5%"
  },

  "musica": {
    "fuente": "archivo",
    "archivo": "musica/fondo.mp3",
    "volumen_base": 0.30,
    "volumen_durante_voz": 0.08,
    "fade_in_segundos": 3.0,
    "fade_out_segundos": 5.0
  },

  "subtitulos": {
    "generar": true,
    "fuente": "Arial",
    "tamano": 24
  },

  "escenas": [
    {
      "id": "intro",
      "clip": "clips/intro.mp4",
      "clip_inicio_seg": 0,
      "clip_fin_seg": null,
      "texto_narracion": "Bienvenidos a este documental sobre...",
      "pausa_antes_seg": 2.0,
      "pausa_despues_seg": 1.0,
      "transicion_entrada": "fade_from_black",
      "transicion_salida": "crossfade"
    },
    {
      "id": "desarrollo",
      "clip": "clips/desarrollo.mp4",
      "clip_inicio_seg": 5,
      "clip_fin_seg": 20,
      "texto_narracion": "Lo que vamos a descubrir hoy es...",
      "pausa_antes_seg": 1.0,
      "pausa_despues_seg": 1.5,
      "transicion_entrada": "crossfade",
      "transicion_salida": "crossfade"
    },
    {
      "id": "cierre",
      "clip": "clips/cierre.mp4",
      "texto_narracion": "Y así concluye nuestra historia...",
      "pausa_antes_seg": 1.0,
      "pausa_despues_seg": 3.0,
      "transicion_entrada": "crossfade",
      "transicion_salida": "fade_to_black"
    }
  ]
}
```

### Explicación de Cada Campo

#### Campos Principales
| Campo | Qué es | Ejemplo |
|-------|--------|---------|
| `titulo` | Nombre del proyecto | `"Mi Documental"` |
| `idioma` | Idioma de la narración | `"es"`, `"en"`, `"pt"` |
| `resolucion` | Resolución del vídeo | `"1920x1080"` (Full HD) |
| `fps` | Frames por segundo | `30` |

#### Narrador
| Campo | Qué es | Ejemplo |
|-------|--------|---------|
| `voz` | Voz de Microsoft (ver tabla abajo) | `"es-ES-AlvaroNeural"` |
| `velocidad` | Más lento (-) o más rápido (+) | `"-5%"`, `"+10%"` |

#### Voces Disponibles
| Voz | Idioma | Género |
|-----|--------|--------|
| `es-ES-AlvaroNeural` | Español España | Hombre |
| `es-ES-ElviraNeural` | Español España | Mujer |
| `es-MX-JorgeNeural` | Español México | Hombre |
| `es-MX-DaliaNeural` | Español México | Mujer |
| `en-US-GuyNeural` | Inglés US | Hombre |
| `en-US-AriaNeural` | Inglés US | Mujer |

Para ver TODAS las voces:
```powershell
python -m edge_tts --list-voices
```

#### Música (opcional)
| Campo | Qué es | Ejemplo |
|-------|--------|---------|
| `archivo` | Ruta al MP3 de música | `"musica/fondo.mp3"` |
| `volumen_base` | Volumen cuando NO habla (0-1) | `0.30` |
| `volumen_durante_voz` | Volumen cuando SÍ habla (0-1) | `0.08` |
| `fade_in_segundos` | Fade al inicio | `3.0` |
| `fade_out_segundos` | Fade al final | `5.0` |

#### Escenas
| Campo | Qué es | Ejemplo |
|-------|--------|---------|
| `id` | Nombre único de la escena | `"intro"` |
| `clip` | Ruta al vídeo | `"clips/intro.mp4"` |
| `texto_narracion` | Lo que dice el narrador | `"Texto..."` |
| `clip_inicio_seg` | Desde qué segundo del clip | `5` |
| `clip_fin_seg` | Hasta qué segundo (`null` = todo) | `20` o `null` |
| `pausa_antes_seg` | Silencio antes de hablar | `2.0` |
| `pausa_despues_seg` | Silencio después de hablar | `1.0` |
| `transicion_entrada` | Efecto al entrar | Ver tabla |
| `transicion_salida` | Efecto al salir | Ver tabla |

#### Transiciones
| Valor | Efecto |
|-------|--------|
| `"cut"` | Corte seco (sin efecto) |
| `"fade_from_black"` | Aparece desde negro |
| `"fade_to_black"` | Desaparece a negro |
| `"crossfade"` | Mezcla suave entre escenas |

---

## ▶️ PARTE 5: EJECUTAR

```powershell
cd "C:\ruta\a\editorvideo\automontaje"
python main.py "C:\ruta\a\mi_proyecto\"
```

### ¿Qué Pasa Internamente?

```
FASE 0 → Valida que todo esté bien (JSON, clips, música)
FASE 1 → Genera la narración con IA (Edge TTS)
FASE 2 → Mezcla narración + música con ducking automático
FASE 3 → Procesa los clips, aplica transiciones, sincroniza
FASE 4 → Genera subtítulos con Whisper (si están activados)
         Limpia temporales y muestra resumen
```

### Resultado

```
mi_proyecto/
├── output/
│   ├── video_final.mp4                ← TU VÍDEO 🎬
│   ├── video_final_subtitulado.mp4    ← Con subtítulos (si activados)
│   ├── audio_mezclado.wav             ← Solo el audio
│   ├── subtitulos.srt                 ← Para YouTube/VLC
│   └── timeline.json                  ← Mapa de tiempos
└── logs/
    └── proceso.log                    ← Log completo
```

---

## ❓ PARTE 6: PROBLEMAS FRECUENTES

### "ffmpeg no reconocido"
→ Cierra y reabre PowerShell. Si sigue, reinstala FFmpeg y verifica el PATH.

### "ModuleNotFoundError: No module named 'edge_tts'"
→ Ejecuta: `pip install edge-tts`

### "ModuleNotFoundError: No module named 'audioop'"
→ Ejecuta: `pip install audioop-lts` (solo Python 3.13+)

### "ModuleNotFoundError: No module named 'whisper'"
→ Ejecuta: `pip install -e "automontaje[subtitulos]"` (es opcional y pesado)
→ O desactiva subtítulos: `"generar": false` en el JSON

### "El vídeo se congela en una escena"
→ El clip es más corto que la narración. El sistema congela el último frame.
→ Solución: usa un clip más largo o acorta el texto.

### "La narración falla"
→ Verifica que tienes conexión a internet (Edge TTS necesita internet).
→ Verifica que la voz existe: `python -m edge_tts --list-voices`

### "El audio suena cortado"
→ Aumenta `pausa_antes_seg` y `pausa_despues_seg` en tus escenas.

---

## 🎯 PARTE 7: EJEMPLO RÁPIDO PASO A PASO

### 1. Crea la carpeta

```powershell
mkdir C:\MiVideo\clips
mkdir C:\MiVideo\musica
```

### 2. Pon tus archivos

- Copia tus clips `.mp4` a `C:\MiVideo\clips\`
- Copia tu música `.mp3` a `C:\MiVideo\musica\` (opcional)

### 3. Crea el JSON

Crea `C:\MiVideo\proyecto.json` con un editor de texto:

```json
{
  "titulo": "Mi Primer Vídeo Automático",
  "idioma": "es",
  "narrador": {
    "voz": "es-ES-AlvaroNeural",
    "velocidad": "-5%"
  },
  "subtitulos": { "generar": false },
  "escenas": [
    {
      "id": "escena_01",
      "clip": "clips/mi_clip.mp4",
      "texto_narracion": "Aquí escribes lo que quieras que diga el narrador.",
      "pausa_antes_seg": 1.0,
      "pausa_despues_seg": 1.0,
      "transicion_entrada": "fade_from_black",
      "transicion_salida": "fade_to_black"
    }
  ]
}
```

### 4. Ejecuta

```powershell
cd "C:\ruta\a\editorvideo\automontaje"
python main.py "C:\MiVideo\"
```

### 5. Recoge tu vídeo

```
C:\MiVideo\output\video_final.mp4
```

¡Listo! 🎬

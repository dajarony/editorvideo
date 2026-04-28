# 🚀 Guía de Uso

## Flujo de Trabajo

```
1. Crear carpeta del proyecto
2. Añadir clips de vídeo y música
3. Escribir proyecto.json
4. Ejecutar: python main.py /ruta/proyecto/
5. Recoger vídeo final en output/
```

---

## 1. Estructura de un Proyecto

Cada proyecto es una carpeta con la siguiente estructura:

```
mi_proyecto/
├── proyecto.json              ← Contrato de edición (obligatorio)
├── clips/                     ← Clips de vídeo por escena
│   ├── intro.mp4
│   ├── desarrollo.mp4
│   └── cierre.mp4
└── musica/                    ← Música de fondo (opcional)
    └── ambient_piano.mp3
```

### Reglas

- El archivo `proyecto.json` **debe** estar en la raíz de la carpeta.
- Los clips se referencian por ruta relativa desde la raíz del proyecto.
- La música es opcional. Sin ella, el vídeo solo tendrá narración.
- Los formatos soportados dependen de FFmpeg (MP4, AVI, MOV, MKV, etc.).

---

## 2. Crear el Contrato JSON

Copiar la plantilla de `plantillas/proyecto_ejemplo.json` y adaptarla:

```json
{
  "titulo": "Mi Documental",
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
    "volumen_durante_voz": 0.08
  },
  "escenas": [
    {
      "id": "intro",
      "clip": "clips/intro.mp4",
      "texto_narracion": "Bienvenidos a este documental..."
    }
  ]
}
```

> Consulta [CONTRATO_JSON.md](CONTRATO_JSON.md) para la referencia completa de todos los campos.

---

## 3. Ejecutar el Sistema

```bash
cd automontaje
python main.py C:\ruta\a\mi_proyecto\
```

### Salida en Consola

```
╔═══════════════════════════════════════════════════════╗
║     AEGS — SISTEMA DE AUTOMONTAJE DE VÍDEO          ║
║  Proyecto: mi_proyecto                               ║
╚═══════════════════════════════════════════════════════╝

━━━ FASE 0: Verificando integridad del proyecto ━━━
  ✓ Proyecto validado correctamente.

━━━ FASE 1: Generando narración con Edge TTS ━━━
  [1/3] Narración 'intro' generada (4.50s)
  [2/3] Narración 'desarrollo' generada (6.20s)
  [3/3] Narración 'cierre' generada (5.10s)

━━━ FASE 2: Ensamblando audio maestro con ducking ━━━
  Ducking: base=-10.5dB, voz=-21.9dB, fade=200ms
  Audio maestro exportado: 25.80s

━━━ FASE 3: Montando vídeo con transiciones ━━━
  [1/3] Procesando clip 'intro'...
  [2/3] Procesando clip 'desarrollo'...
  [3/3] Procesando clip 'cierre'...

━━━ FASE 4: Postproducción y subtítulos ━━━
  SRT generado: 12 subtítulos

╔═══════════════════════════════════════════════════════╗
║           PROYECTO RENDERIZADO CON ÉXITO             ║
║  Escenas procesadas : 3                              ║
║  Duración del vídeo : 25.80 segundos                 ║
║  Tiempo de proceso  : 45.2 segundos                  ║
╚═══════════════════════════════════════════════════════╝
```

---

## 4. Archivos Generados

```
mi_proyecto/
├── output/
│   ├── narracion/                     ← MP3 individual por escena
│   │   ├── intro.mp3
│   │   ├── desarrollo.mp3
│   │   └── cierre.mp3
│   ├── narracion_duraciones.json      ← Duraciones reales medidas
│   ├── audio_mezclado.wav             ← Mezcla voz + música (sin pérdida)
│   ├── timeline.json                  ← Mapa temporal matemático
│   ├── video_final.mp4                ← Vídeo sin subtítulos
│   ├── video_final_subtitulado.mp4    ← Vídeo con subtítulos (si activados)
│   └── subtitulos.srt                 ← Archivo SRT exportable
└── logs/
    └── proceso.log                    ← Log completo del renderizado
```

### ¿Qué archivo usar?

| Necesidad | Archivo |
|-----------|---------|
| Vídeo final con subtítulos | `video_final_subtitulado.mp4` |
| Vídeo final sin subtítulos | `video_final.mp4` |
| Solo el audio para podcast | `audio_mezclado.wav` |
| Subtítulos para YouTube | `subtitulos.srt` |
| Depuración de tiempos | `timeline.json` |
| Log de errores | `logs/proceso.log` |

---

## 5. Re-ejecutar un Proyecto

El sistema **sobrescribe** los archivos de salida en cada ejecución. Para re-renderizar:

```bash
python main.py C:\ruta\a\mi_proyecto\
```

No necesitas borrar la carpeta `output/` manualmente. Los temporales (`temp_clips/`) se limpian automáticamente tras un renderizado exitoso.

---

## 6. Voces Disponibles

El sistema usa Microsoft Edge TTS. Algunas voces populares:

| Voz | Idioma | Género |
|-----|--------|--------|
| `es-ES-AlvaroNeural` | Español (España) | Masculino |
| `es-ES-ElviraNeural` | Español (España) | Femenino |
| `es-MX-JorgeNeural` | Español (México) | Masculino |
| `es-MX-DaliaNeural` | Español (México) | Femenino |
| `en-US-AriaNeural` | Inglés (US) | Femenino |
| `en-US-GuyNeural` | Inglés (US) | Masculino |

Para listar todas las voces disponibles:

```bash
python -m edge_tts --list-voices
```

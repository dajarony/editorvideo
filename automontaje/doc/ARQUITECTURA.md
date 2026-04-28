# 🏗️ Arquitectura del Sistema

## Visión General

AEGS sigue una arquitectura de **pipeline unidireccional** con 6 fases secuenciales. Cada fase depende estrictamente de la anterior y el sistema aborta inmediatamente si cualquier fase falla.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Módulo 0   │    │  Módulo 1   │    │  Módulo 2   │    │  Módulo 3   │    │  Módulo 4   │
│  Validador  │───►│  Narración  │───►│  Mezclador  │───►│  Montador   │───►│ Subtítulos  │
│             │    │   (TTS)     │    │   Audio     │    │   Vídeo     │    │  (Whisper)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       ▲                                                                           │
       │                        Módulo 5: Orquestador (main.py)                    │
       └───────────────────────────────────────────────────────────────────────────┘
```

---

## Diagrama de Archivos y Dependencias

```
automontaje/
├── main.py                    ← Módulo 5: Orquestador
│   ├── importa → modulos/validador.py
│   ├── importa → modulos/narracion.py
│   ├── importa → modulos/mezclador_audio.py
│   ├── importa → modulos/montador_video.py
│   └── importa → modulos/subtitulos.py
│
├── configuracion.py           ← Constantes globales (sin dependencias)
│
├── modulos/
│   ├── __init__.py
│   ├── utilidades.py          ← Logger + FFprobe + Limpieza
│   ├── validador.py           ← Módulo 0
│   ├── narracion.py           ← Módulo 1
│   ├── mezclador_audio.py     ← Módulo 2
│   ├── montador_video.py      ← Módulo 3
│   └── subtitulos.py          ← Módulo 4
│
├── tests/                     ← Suite de tests
├── plantillas/                ← JSON de ejemplo
└── doc/                       ← Documentación
```

---

## Flujo de Datos

```
proyecto.json ──► Validador ──► datos_proyecto (dict)
                                      │
                                      ▼
                               Narración TTS
                                      │
                        ┌─────────────┼─────────────┐
                        ▼             ▼             ▼
                   escena_01.mp3  escena_02.mp3  escena_03.mp3
                        │             │             │
                        └─────────────┼─────────────┘
                                      ▼
                        narracion_duraciones.json
                                      │
                                      ▼
                            Mezclador de Audio ◄── musica.mp3
                                      │
                                      ▼
                            audio_mezclado.wav
                                      │
                                      ▼
         clips/*.mp4 ──► Montador de Vídeo ──► timeline.json
                                      │
                                      ▼
                            video_final.mp4
                                      │
                                      ▼
                        Subtítulos (Whisper) ──► subtitulos.srt
                                      │
                                      ▼
                      video_final_subtitulado.mp4
```

---

## Los 4 Ajustes de Calidad

El sistema implementa 4 decisiones de diseño específicas para garantizar la calidad del resultado:

### Ajuste 1: FFprobe Unificado
Una sola función (`obtener_info_media()` en `utilidades.py`) para extraer metadatos de cualquier archivo multimedia. Evita inconsistencias entre módulos.

### Ajuste 2: Pipeline WAV
La mezcla de audio se exporta en formato **WAV sin pérdida**. La compresión a AAC solo ocurre en el paso final de muxeo, evitando degradación acumulativa.

### Ajuste 3: Verificación Post-TTS
Después de generar cada MP3 con Edge TTS, el sistema verifica con ffprobe que:
- El archivo existe
- La duración es >= 0.5 segundos
Si falla, reintenta automáticamente.

### Ajuste 4: Whisper Limpio
Los subtítulos se generan transcribiendo las pistas de voz **sin música** (los MP3 individuales, no el audio mezclado). Esto maximiza la precisión de Whisper.

---

## Gestión de Errores

| Fase | Error | Comportamiento |
|------|-------|---------------|
| 0 | JSON inválido | **ABORTAR** — `sys.exit(1)` |
| 0 | Clip no encontrado | **ABORTAR** — error bloqueante |
| 1 | TTS falla | **REINTENTAR** 1 vez, luego abortar |
| 2 | Música no encontrada | **WARNING** — continúa solo con voz |
| 3 | FFmpeg falla en clip | **ABORTAR** — `RuntimeError` |
| 4 | Whisper falla | **ABORTAR** — error en módulo |
| 4 | Subtítulos desactivados | **OMITIR** — flujo normal |

---

## Concurrencia

El Módulo 1 (Narración) es el único que usa concurrencia. Genera todos los MP3 en paralelo con `asyncio.gather()`:

```python
resultados = await asyncio.gather(*tareas)
```

Esto reduce significativamente el tiempo de generación TTS cuando hay muchas escenas, ya que cada llamada a Edge TTS es una operación de red independiente.

El resto del pipeline es secuencial por naturaleza (cada fase depende de la anterior).

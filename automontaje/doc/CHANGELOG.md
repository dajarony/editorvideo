# 📝 Changelog

Historial de cambios, bugs corregidos y decisiones técnicas.

---

## v1.0.0 — 2026-04-28 (Construcción Inicial)

### Módulos Creados
- `configuracion.py` — Configuración global centralizada
- `modulos/utilidades.py` — Logger dual + FFprobe unificado + limpieza
- `modulos/validador.py` — Módulo 0: Validación de proyectos
- `modulos/narracion.py` — Módulo 1: Generación TTS con Edge TTS
- `modulos/mezclador_audio.py` — Módulo 2: Mezcla de audio con ducking
- `modulos/montador_video.py` — Módulo 3: Montaje de vídeo con transiciones
- `modulos/subtitulos.py` — Módulo 4: Subtítulos con Whisper
- `main.py` — Módulo 5: Orquestador del pipeline

### Bugs Corregidos Durante Testing

#### 🔴 BUG-001: Event Loop de Windows
- **Síntoma**: `aiodns needs a SelectorEventLoop on Windows`
- **Causa**: Python en Windows usa `ProactorEventLoop` por defecto. La librería `aiodns` (dependencia interna de `edge-tts`) requiere `SelectorEventLoop`.
- **Fix**: Añadido al inicio de `narracion.py`:
  ```python
  if sys.platform == "win32":
      asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
  ```
- **Impacto**: Sin este fix, la narración TTS falla al 100% en Windows.

#### 🔴 BUG-002: PyDub + Python 3.13
- **Síntoma**: `ModuleNotFoundError: No module named 'audioop'`
- **Causa**: Python 3.13 eliminó el módulo `audioop` de la stdlib. PyDub lo usa internamente para manipulación de audio.
- **Fix**: Añadido `audioop-lts>=0.2.1` al `requirements.txt`.
- **Impacto**: Sin este fix, el mezclador de audio no puede importarse en Python 3.13+.

### Decisiones de Diseño Documentadas
- API Python directa de Edge TTS en lugar del CLI (evita bugs de comillas)
- Pipeline WAV sin pérdida (compresión solo en el muxeo final)
- Ducking suavizado con márgenes ±200ms y fades en bordes
- Whisper sobre pistas limpias (sin música) para máxima precisión
- Transiciones como filtros FFmpeg reales (`fade`, no decorativas)

### Testing
- 53 tests creados y pasando al 100%
- Cobertura: todos los módulos excepto ejecución FFmpeg directa (requiere instalación)

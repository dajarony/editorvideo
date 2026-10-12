# 📝 Changelog

Historial de cambios, bugs corregidos y decisiones técnicas.

---

## Sin publicar — integración con Aura Motion Studio (F1)

Auditoría completa en [`AUDITORIA_2026-10.md`](AUDITORIA_2026-10.md).

- **Instalable como paquete:** `pyproject.toml` declara `py-modules` y `packages`; antes `pip install -e automontaje` fallaba siempre.
- **Whisper opcional:** pasa al extra `subtitulos`; la instalación mínima ya no arrastra PyTorch. Sin él, los subtítulos fallan con un mensaje que dice cómo instalarlo.
- **Tests sin red:** los 4 que llaman a Edge TTS real llevan la marca `internet` y solo corren con `AEGS_TEST_INTERNET=1` (uno de ellos no estaba documentado como de red y pasaba siempre porque su aserción no comprobaba nada).
- **FFmpeg configurable:** `AEGS_FFMPEG` y `AEGS_FFPROBE`; todas las llamadas pasan por `utilidades.binario()`, que las devuelve como ruta absoluta (una relativa fallaba en Linux con `cwd`), y pydub las usa solo si están definidas. Una ruta mala o no ejecutable da un error claro, no una excepción.
- **CI:** GitHub Actions en Ubuntu con Python 3.12 y 3.13.

---

## v0.2.0 — 2026-04-29 (Hardening + Caché + xfade real)

### Auditoría completa del sistema → 10 bugs/mejoras identificados y resueltos

#### ✅ MEJORA-001: Verificación de FFmpeg al arranque
- Añadida función `verificar_ffmpeg()` en `utilidades.py`
- El sistema aborta con mensaje claro si FFmpeg no está en PATH
- Se ejecuta ANTES de la Fase 0, no a mitad de pipeline

#### ✅ MEJORA-002: Validador endurecido
- `narrador` ahora se valida como `dict` (antes crashaba si era string)
- `clip_inicio_seg` se compara contra la duración real del clip (antes no)
- `clip_fin_seg` emite warning si excede la duración del clip
- `texto_narracion` se valida como `str` antes de llamar `.strip()`
- `escenas` se valida como `list` antes de iterar

#### ✅ MEJORA-003: Caché TTS por hash SHA-1
- Añadida función `hash_tts(texto, voz, velocidad)` en `utilidades.py`
- `narracion.py` lee/escribe `output/narracion_cache.json`
- Si el hash coincide y el MP3 existe → reutiliza sin llamar a Edge TTS
- Flag `--no-cache` en CLI para forzar regeneración completa
- Ahorro: en re-renders del mismo proyecto, Fase 1 pasa de 10s a <1s

#### ✅ MEJORA-004: Reintentos TTS con backoff progresivo
- `REINTENTOS_MAXIMOS_TTS` aumentado de 1 a 3
- Añadido `RETARDO_REINTENTO_TTS_SEG = 2.0` en `configuracion.py`
- Backoff: intento 1 → espera 2s, intento 2 → espera 4s, intento 3 → falla
- Cubre rate-limit 429 de Edge TTS en proyectos grandes

#### ✅ MEJORA-005: Fix división por cero en mezclador
- Si `pista_voz` tiene duración 0ms → error controlado, no crash
- Si `musica` tiene duración 0ms → warning + exporta solo narración
- Si `duraciones` JSON está vacío → error descriptivo

#### ✅ MEJORA-006: Crossfade real con xfade (filter_complex)
- El antiguo "crossfade" era un dip-to-black (fade out + fade in). Mentía.
- Renombrado a `dip_to_black` para honestidad
- Nueva transición `crossfade` usa `xfade=transition=fade` de FFmpeg real
- El ensamblador detecta si hay crossfades y cambia de concat-demuxer a filter_complex encadenado
- Offset matemático calculado por duración acumulada

#### ✅ MEJORA-007: GOP fijo en clips procesados
- Añadido `-g {fps*2}` al comando ffmpeg de procesado individual
- Evita desincronización en concat-demuxer cuando hay diferencias de GOP entre clips

#### ✅ MEJORA-008: Subtítulos UTF-8 BOM + modo sidecar
- SRT escrito con `encoding='utf-8-sig'` (UTF-8 con BOM)
- FFmpeg en Windows lee tildes correctamente con BOM
- Nuevo campo `"sidecar": true` en JSON → genera SRT sin quemar en vídeo
- Nuevo campo `"incrustar": false` como alias alternativo
- Import de `whisper` movido dentro de la función (lazy import) con mensaje claro si no está instalado

#### ✅ MEJORA-009: CLI con argparse completo
- `main.py` reescrito con `argparse`
- Flags: `--skip-tts`, `--skip-subs`, `--no-cache`, `--keep-temp`, `--srt-sidecar`, `-v/--verbose`
- `--skip-tts`: usa narraciones existentes sin regenerar
- `--keep-temp`: no borra clips temporales tras renderizar (útil para debug)
- Código de salida 130 para Ctrl+C (estándar Unix)

#### ✅ MEJORA-010: Metadata del repositorio
- `pyproject.toml` creado con dependencias, classifiers y entry point
- `.gitignore` completo (outputs, logs, vídeos de usuario no se suben)
- `LICENSE` MIT
- `README.md` en raíz con badges, tabla de transiciones, ejemplo CLI

### Nuevo: Primera integración con Higgsfield AI MCP
- Conexión via MCP a https://mcp.higgsfield.ai/mcp
- Flujo probado: texto → imagen (nano_banana_2) → vídeo 5s (grok_video)
- Clip generado descargado e integrado en pipeline AEGS sin cambios de código
- Coste en plan free: 2 créditos/imagen + 7.5 créditos/vídeo 5s

### Demo de ciberseguridad completada
- 5 escenas: 1 clip IA (Higgsfield) + 4 clips Gemini reales
- Música ambient cyber generada con FFmpeg (acorde Em, tremolo + reverb + lowpass)
- Narración Edge TTS voz `es-ES-AlvaroNeural`
- Resultado: 53s, 1920×1080, xfade real entre todas las escenas
- Tiempo de render: ~80 segundos

---

## v0.1.0 — 2026-04-28 (Construcción Inicial)

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

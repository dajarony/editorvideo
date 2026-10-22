# 📝 Changelog

Historial de cambios, bugs corregidos y decisiones técnicas.

---

## Sin publicar — revisión del editor

- **Los tiempos de un contrato son los del vídeo original** (`"tiempos": "original"`, por defecto). Antes cada paso usaba los segundos del vídeo que le llegaba, así que «corta de 7 a 9 y pon un texto en el 12» ponía el texto 2 s más tarde de lo pedido. Ahora `corte` y `cortar_silencios` informan de los tramos que conservan (`SalidaPaso`) y el ejecutor traslada los segundos de los pasos siguientes (`modulos/tiempos.py`). Un momento que cae en un tramo ya quitado pasa al siguiente que queda, con un aviso; un corte de algo ya quitado se omite (`pasos_omitidos`). Con `"tiempos": "resultado"` se conserva el comportamiento anterior.

## Sin publicar — imagen y voz sincronizadas

- **Corregido: quitar silencios desincronizaba la voz.** `cortar_silencios` aplicaba `silenceremove` solo al audio y dejaba el vídeo entero: en una prueba de 6 s con 2 s de silencio, el vídeo seguía durando 6,0 s y el audio 4,04 s. Ahora detecta los silencios con `silencedetect` y corta los mismos tramos en la imagen y en el sonido (como ya hacía `eliminar_muletillas`), dejando 0,15 s de cada silencio a cada lado. Un vídeo sin audio o sin silencios largos se copia tal cual.
- **Corregido: el fundido cruzado acortaba el vídeo.** Cada `crossfade` solapaba 0,7 s las dos escenas, así que el vídeo quedaba 0,7 s más corto por fundido mientras el audio conservaba su duración; `-shortest` cortaba entonces el final de la última frase y la voz se iba retrasando respecto a la imagen (3 escenas: vídeo de 4,73 s para un timeline de 6,13 s). Ahora la escena que sale se alarga lo que dura el fundido y cada fundido empieza donde empieza la escena siguiente: el vídeo y el audio duran exactamente lo que el timeline. No se había visto porque el FFmpeg de los tests no tenía `xfade` (llegó en FFmpeg 4.3).
- **Tests:** `tests/test_sincronizacion.py` (9) comprueba las dos cosas con medios reales; los que necesitan `xfade` se omiten con su motivo si el FFmpeg no lo tiene.

## Sin publicar — integración con Aura Motion Studio (F3a: narración primero)

- **`--solo-narracion`:** valida y genera la narración (`output/narracion_duraciones.json`) y se detiene sin montar. Los clips **aún pueden no existir** (un clip ausente o ilegible es un aviso, no un error); el resto de la validación sigue siendo estricta. No se combina con `--skip-tts`.
- **Voz sintética offline:** `"narrador": {"motor": "sintetico"}` genera un WAV de prueba determinista (un tono por palabra, proporcional a sus caracteres, más 0,2 s de silencio final) sin red; la `voz` no se usa. La duración crece con cada carácter del texto y baja con la velocidad. Es para CI y para medir tiempos, no una narración real.
- **Duración estricta:** `--duracion-estricta` o `"montaje": {"duracion_estricta": true}`. Si un clip no dura lo que su escena (±1 fotograma), falla con la escena y las dos duraciones en vez de recortarlo o congelar su último fotograma. Una escena sin entrada en `narracion_duraciones.json` también es un error (sin el modo estricto se omite con un aviso, como antes). Solo admite transiciones `cut`. Las escenas se cortan con un número exacto de fotogramas sobre una rejilla acumulada (`round(fin × fps) − round(inicio × fps)`), así que el vídeo no se desfasa de la voz aunque haya muchas escenas: con 10 escenas de 1,48 s a 30 fps, cortar cada una por su cuenta perdía 0,123 s medidos con ffprobe (4 fotogramas en teoría) al final. Se mide la pista de vídeo de cada clip, no la del contenedor: un clip con el vídeo 1 s más corto y el audio hasta el final pasaba la comprobación y se congelaba. Además el relleno queda limitado a 1 fotograma y cada segmento se comprueba después de cortarlo. En cuanto se lee el proyecto borra el `video_final.mp4` (y el subtitulado) de una ejecución anterior, para que un fallo en cualquier fase no deje a la vista un vídeo viejo.
- **`narrador.motor` se valida:** solo `edge-tts` o `sintetico`; cualquier otro valor (también uno que no sea texto) es un error de validación.
- **Corregido (Windows):** la concatenación final fallaba con `Impossible to open '…\output/000_….mp4'` porque algunos FFmpeg de Windows resuelven la lista de concat por el último `/` (con `CARPETA_TEMP = "output/temp_clips"` buscaban los clips en `output/`). La lista se pasa ahora por su nombre con `cwd` en la carpeta de los clips, y el audio y el vídeo final por ruta absoluta (para que `montar_video_proyecto` siga funcionando con una ruta de proyecto relativa). Detectado al montar de verdad por primera vez en los tests de integración.
- **Instalable como dependencia fijada:** comprobado con una rueda del árbol de F3a en un venv limpio: `aegs --help` y `aegs <proyecto> --solo-narracion` funcionan fuera del repositorio. Salida literal en [AUDITORIA_2026-10.md](AUDITORIA_2026-10.md#evidencia-de-f3a--c7-instalación-desde-una-rueda). Para fijarlo desde Git: `pip install "aegs-automontaje @ git+https://github.com/dajarony/editorvideo@<commit>#subdirectory=automontaje"`.

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

# 🔧 API de Módulos — Referencia Técnica

Documentación de todas las funciones públicas de cada módulo.

---

## `utilidades.py` — Servicios Compartidos

### `configurar_logger() → logging.Logger`
Crea el logger base del sistema (`AEGS`) con salida a consola (nivel INFO). El FileHandler se añade después con `activar_log_archivo()`.

### `activar_log_archivo(ruta_proyecto, carpeta_logs, archivo_log)`
Añade un FileHandler al logger para guardar logs en disco.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `ruta_proyecto` | str | Ruta base del proyecto |
| `carpeta_logs` | str | Subcarpeta de logs (ej: `"logs"`) |
| `archivo_log` | str | Nombre del archivo (ej: `"proceso.log"`) |

### `obtener_info_media(ruta_archivo) → dict`
Extrae metadatos de un archivo multimedia usando FFprobe.

**Retorna**: `{"duracion": float, "resolucion": str, "codec": str}` o `{"error": str}`. Si hay pista de vídeo añade `"duracion_video"`: la de esa pista (la del contenedor, `duracion`, es la de la pista más larga), o la del contenedor si el formato no la da por pista.

### `limpiar_carpeta_temporal(ruta_proyecto, carpeta_temp)`
Elimina la carpeta de temporales. No falla si no existe.

---

## `validador.py` — Módulo 0

### `errores_duracion_estricta(datos) → list`
Errores del modo duración estricta: cualquier `transicion_entrada`/`transicion_salida` distinta de `cut`. Si `escenas` no es una lista devuelve `[]` (ese error lo da `inicializar_validador`). `inicializar_validador` la aplica si `montaje.duracion_estricta` es `true` o si recibe `duracion_estricta=True`.

### `inicializar_validador(ruta_proyecto, requiere_clips=True, duracion_estricta=False) → dict`
Valida la integridad completa de un proyecto.

- `requiere_clips=False` (lo usa `--solo-narracion`): un clip ausente o ilegible pasa de error a warning, porque en el flujo "narración primero" los clips se renderizan después de medir la voz. Lo demás se valida igual.
- `duracion_estricta=True` (lo usa `--duracion-estricta`): aplica `errores_duracion_estricta` aunque el JSON no tenga `montaje.duracion_estricta`.

**Validaciones bloqueantes** (errores):
- `proyecto.json` existe y es JSON válido
- Campos obligatorios: `titulo`, `idioma`, `narrador`, `escenas`
- Al menos 1 escena definida
- IDs de escena únicos
- Cada escena tiene texto de narración
- Clips de vídeo existen y son válidos
- Música referenciada existe

**Validaciones no bloqueantes** (warnings):
- Texto de narración muy corto (< 10 chars)
- Clips muy cortos (< 3s)
- Voz no reconocida
- Sin velocidad definida
- Sin música configurada

**Retorna**:
```python
{
    "exito": bool,
    "errores": list[str],
    "warnings": list[str],
    "datos": dict,           # JSON parseado
    "metadatos_clips": dict  # Info ffprobe por escena
}
```

---

## `narracion.py` — Módulo 1

### `generar_audio_escena(id_escena, texto, voz, velocidad, ruta_salida) → dict` (async)
Genera un MP3 de narración para una escena usando la API Python de Edge TTS.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `id_escena` | str | Identificador único de la escena |
| `texto` | str | Texto a narrar |
| `voz` | str | Voz Edge TTS (ej: `es-ES-AlvaroNeural`) |
| `velocidad` | str | Ajuste de velocidad (ej: `-5%`) |
| `ruta_salida` | str | Ruta absoluta para el MP3 |

**Reintentos**: Hasta `REINTENTOS_MAXIMOS_TTS` + 1 intentos.  
**Verificación**: Post-generación verifica existencia y duración mínima con ffprobe.

### `generar_audio_sintetico(texto, velocidad, ruta_salida) → float`
Voz de **prueba** offline y determinista: escribe un WAV mono de 16 bits con un tono por palabra, proporcional a sus caracteres (más uno por la pausa), y 0,2 s de silencio final, y devuelve su duración en segundos. La duración depende solo de la longitud del texto y de la velocidad, y crece con cada carácter. Lanza `ValueError` si la velocidad no tiene el formato `+0%`/`-5%`. No usa red ni FFmpeg.

### `ejecutar_narracion_concurrente(ruta_proyecto, datos_proyecto) → dict` (async)
Genera todas las narraciones del proyecto en paralelo con `asyncio.gather()`. Con `narrador.motor = "sintetico"` usa `generar_audio_sintetico` (archivos `.wav`) en lugar de Edge TTS; una velocidad mal formada se devuelve en `errores` por escena, sin excepción. Los dos motores escriben `narracion_duraciones.json` con el mismo formato y en el mismo sitio.

**Retorna**: `{"exito": bool, "errores": list, "duraciones": dict}`

**Genera**: `output/narracion_duraciones.json` con estructura:
```json
{
    "escena_01": {
        "archivo": "output/narracion/escena_01.mp3",
        "duracion_real_seg": 4.5
    }
}
```

---

## `mezclador_audio.py` — Módulo 2

### `lineal_a_db(volumen_lineal) → float`
Convierte un volumen lineal (0.0–1.0) a decibelios.  
- `1.0` → `0.0 dB`
- `0.5` → `-6.02 dB`
- `≤ 0.001` → `-120.0 dB` (silencio)

### `mezclar_audio_proyecto(ruta_proyecto, datos_proyecto) → dict`
Ensambla la mezcla final de narración + música con ducking suavizado.

**Proceso**:
1. Construye pista de voz con silencios dinámicos (pausas)
2. Carga música, aplica loop si es más corta, recorta si es más larga
3. Aplica fades globales (fade_in, fade_out)
4. Calcula segmentos de ducking con márgenes extendidos (±200ms)
5. Fusiona segmentos solapados
6. Aplica ducking por segmentos con fades suaves
7. Mezcla ambas pistas en overlay
8. Exporta en formato WAV sin pérdida

**Retorna**: `{"exito": bool, "archivo": str, "duracion_ms": int}`

---

## `montador_video.py` — Módulo 3

### `calcular_timeline(ruta_proyecto, datos_proyecto) → dict`
Calcula la duración exacta de cada escena.

**Fórmula**: `duracion_escena = pausa_antes + duracion_narracion + pausa_despues`

Con `montaje.duracion_estricta`, lanza `ValueError` ("Modo duración estricta: …") si el clip no dura lo que la escena (±1 fotograma) en lugar de marcarlo para recortar o congelar, y también si una escena no está en `narracion_duraciones.json` (sin el modo estricto se omite con un aviso). En ese modo cada escena del timeline lleva además `fotogramas = round(fin × fps) − round(inicio × fps)` (rejilla acumulada, .5 hacia arriba), se mide la pista de vídeo del clip (`duracion_video`; sin ella, error) y se compara con `fotogramas / fps`. `procesar_clips_individuales` corta con `-frames:v` en vez de `-t`, rellena como mucho 1 fotograma (`tpad`) y comprueba que cada segmento salga con exactamente sus fotogramas; si no, `ValueError` en vez de congelar.

**Retorna**:
```python
{
    "duracion_total_seg": 25.8,
    "escenas": [
        {
            "id": "intro",
            "inicio_seg": 0.0,
            "fin_seg": 6.5,
            "duracion_necesaria": 6.5,
            "clip_recortado": False,
            "clip_extendido": True,
            "transicion_entrada": "fade_from_black",
            "transicion_salida": "crossfade"
        }
    ]
}
```

### `procesar_clips_individuales(ruta_proyecto, timeline, resolucion, fps) → list`
Procesa cada clip con FFmpeg: escala, padding, FPS, freeze (tpad), transiciones.

### `ensamblar_y_sincronizar(ruta_proyecto, archivos_procesados) → str`
Concatena los clips (concat demuxer) y muxea con audio maestro (WAV→AAC).

### `montar_video_proyecto(ruta_proyecto, datos_proyecto) → dict`
Orquestador interno: timeline → procesamiento → ensamblaje.

---

## `subtitulos.py` — Módulo 4

### `segundos_a_srt(segundos) → str`
Convierte segundos a formato SRT (`HH:MM:SS,mmm`).

### `generar_srt_matematico(ruta_proyecto, datos_proyecto) → str`
Transcribe cada MP3 limpio (sin música) con Whisper y suma offsets del timeline.

**Proceso**:
1. Carga modelo Whisper (`base` por defecto)
2. Para cada escena, transcribe el MP3 individual
3. Calcula `offset_global = inicio_escena + pausa_antes`
4. Suma el offset a cada timestamp de Whisper
5. Genera SRT unificado

### `incrustar_subtitulos(ruta_proyecto, config_subs, ruta_srt) → str`
Quema los subtítulos en el vídeo con FFmpeg `force_style`.

### `procesar_subtitulos(ruta_proyecto, datos_proyecto) → dict`
Orquestador: comprueba si están activados, transcribe, incrusta.

---

## `main.py` — Módulo 5: Orquestador

### `orquestador(ruta_proyecto)` (async)
Ejecuta el pipeline completo en orden estricto.

**Flujo**: Fase 0 → 1 → 2 → 3 → 4 → Limpieza → Resumen.

**Uso**: `python main.py /ruta/a/mi_proyecto/`

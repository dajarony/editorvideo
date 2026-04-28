# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.0
═══════════════════════════════════════════════════════════
Archivo: configuracion.py
Tipo: Configuración Global del Sistema
Dependencias: 0

Propósito:
- Centralizar todas las constantes, rutas y parámetros
  del sistema para evitar valores mágicos dispersos.
═══════════════════════════════════════════════════════════
"""

# ─── Constantes de Generación TTS ────────────────────────
DURACION_MINIMA_AUDIO_SEG = 0.5
REINTENTOS_MAXIMOS_TTS = 3        # Reintentos por escena (rate-limit Edge TTS)
RETARDO_REINTENTO_TTS_SEG = 2.0   # Espera entre reintentos (backoff)
USAR_CACHE_TTS = True             # Si True, no regenera narraciones idénticas

# ─── Constantes de Vídeo ────────────────────────────────
RESOLUCION_DEFAULT = "1920x1080"
FPS_DEFAULT = 30

# ─── Constantes de Subtítulos ───────────────────────────
# Opciones: "tiny", "base", "small", "medium", "large"
# "base" ofrece buena precisión en español sin requerir mucha RAM.
MODELO_WHISPER = "base"

# ─── Constantes de Audio ────────────────────────────────
# Milisegundos de fade en las transiciones de ducking.
# Suaviza el cambio de volumen cuando entra/sale la voz.
FADE_DUCK_MS = 200

# ─── Constantes de Transiciones ─────────────────────────
# Duración del fade visual (en segundos) para transiciones
# de tipo fade_from_black, fade_to_black y dip-to-black (crossfade).
FADE_TRANSICION_SEG = 1.0

# ─── Voces Edge TTS Validadas ───────────────────────────
# Lista no exhaustiva. Edge TTS tiene +400 voces.
# Se usa como referencia de las voces más comunes en español e inglés.
# Si el usuario configura una voz fuera de esta lista,
# el validador emite un WARNING (no un error bloqueante).
VOCES_EDGE_CONOCIDAS = [
    # Español (España)
    "es-ES-AlvaroNeural", "es-ES-ElviraNeural",
    # Español (México)
    "es-MX-JorgeNeural", "es-MX-DaliaNeural",
    # Español (Argentina)
    "es-AR-ElenaNeural", "es-AR-TomasNeural",
    # Español (Colombia)
    "es-CO-GonzaloNeural", "es-CO-SalomeNeural",
    # Inglés (US)
    "en-US-AriaNeural", "en-US-GuyNeural",
    "en-US-JennyNeural", "en-US-ChristopherNeural",
    # Inglés (UK)
    "en-GB-SoniaNeural", "en-GB-RyanNeural",
    # Portugués (Brasil)
    "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural",
    # Francés
    "fr-FR-DeniseNeural", "fr-FR-HenriNeural",
]

# ─── Nombres de Archivos de Salida ──────────────────────
ARCHIVO_PROYECTO = "proyecto.json"
ARCHIVO_DURACIONES = "narracion_duraciones.json"
ARCHIVO_AUDIO_MEZCLADO = "audio_mezclado.wav"
ARCHIVO_TIMELINE = "timeline.json"
ARCHIVO_VIDEO_FINAL = "video_final.mp4"
ARCHIVO_SRT = "subtitulos.srt"
ARCHIVO_VIDEO_SUB = "video_final_subtitulado.mp4"

# ─── Nombres de Carpetas ────────────────────────────────
CARPETA_OUTPUT = "output"
CARPETA_NARRACION = "output/narracion"
CARPETA_TEMP = "output/temp_clips"
CARPETA_LOGS = "logs"
ARCHIVO_LOG = "proceso.log"
ARCHIVO_CACHE_TTS = "narracion_cache.json"

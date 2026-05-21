# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.0
═══════════════════════════════════════════════════════════
Archivo: modulos/mejoras.py
Tipo: Postproducción → Mejoras Automáticas (Módulo 5)
Dependencias: os, re, json, subprocess, whisper (opcional)

Entradas:
- Ruta a cualquier archivo de vídeo .mp4

Acciones:
1. Elimina silencios largos (FFmpeg silenceremove)
2. Elimina muletillas: umm, eh, este... (Whisper word timestamps)
3. Color grading cinematográfico (FFmpeg curves + eq)
4. Fades de audio en inicio/fin (30ms, FFmpeg afade)

Salidas:
- Vídeo procesado con todas las mejoras aplicadas
═══════════════════════════════════════════════════════════
"""

import os
import json
import shutil
import subprocess
from .utilidades import logger


# ─── Constantes ─────────────────────────────────────────

MULETILLAS = {
    "es": ["umm", "uhh", "eh", "este", "bueno", "mmm", "ahh", "pues", "o sea"],
    "en": ["umm", "uhh", "uh", "like", "you know", "basically", "literally"],
}

ESTILOS_COLOR = {
    "cinematico": (
        "curves=r='0/0.04 0.5/0.54 1/0.96':"
        "g='0/0.02 0.5/0.50 1/0.98':"
        "b='0/0.08 0.5/0.44 1/0.86',"
        "eq=saturation=1.15:contrast=1.08:brightness=0.02"
    ),
    "calido": (
        "curves=r='0/0.05 0.5/0.60 1/1.0':"
        "g='0/0.00 0.5/0.50 1/0.95':"
        "b='0/0.00 0.5/0.42 1/0.85',"
        "eq=saturation=1.20"
    ),
    "neutro": (
        "eq=saturation=1.10:contrast=1.05:brightness=0.01,"
        "unsharp=5:5:0.8:5:5:0"
    ),
}


# ─── Helpers ────────────────────────────────────────────

def _duracion_video(ruta: str) -> float:
    """Devuelve la duración en segundos de un vídeo."""
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", ruta]
    res = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(res.stdout)
    return float(info["format"]["duration"])


def _run_ffmpeg(cmd: list, descripcion: str):
    """Ejecuta FFmpeg y lanza excepción si falla."""
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"FFmpeg falló en '{descripcion}':\n{resultado.stderr[-800:]}")


# ─── Paso 1: Cortar silencios ────────────────────────────

def cortar_silencios(
    ruta_entrada: str,
    ruta_salida: str,
    umbral_db: float = -35.0,
    duracion_min: float = 0.6
) -> str:
    """Elimina silencios largos del vídeo con FFmpeg silenceremove."""
    logger.info(f"  ✂  Eliminando silencios (umbral={umbral_db}dB, min={duracion_min}s)...")
    filtro = (
        f"silenceremove=stop_periods=-1:"
        f"stop_duration={duracion_min}:"
        f"stop_threshold={umbral_db}dB"
    )
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", ruta_entrada,
        "-af", filtro,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        ruta_salida
    ], "cortar_silencios")
    logger.info(f"  ✅ Silencios eliminados → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── Paso 2: Eliminar muletillas ────────────────────────

def eliminar_muletillas(
    ruta_entrada: str,
    ruta_salida: str,
    idioma: str = "es"
) -> str:
    """Detecta y elimina muletillas usando Whisper word timestamps."""
    try:
        import whisper
    except ImportError:
        logger.warning("  ⚠  Whisper no instalado. Omitiendo muletillas.")
        shutil.copy2(ruta_entrada, ruta_salida)
        return ruta_salida

    palabras_filler = MULETILLAS.get(idioma, MULETILLAS["es"])
    logger.info(f"  🎙  Transcribiendo con Whisper para detectar muletillas...")

    modelo = whisper.load_model("base")
    resultado = modelo.transcribe(ruta_entrada, language=idioma, word_timestamps=True)

    cortes = []
    for seg in resultado.get("segments", []):
        for palabra in seg.get("words", []):
            texto = palabra["word"].strip().lower().rstrip(".,!?")
            if texto in palabras_filler:
                cortes.append((float(palabra["start"]), float(palabra["end"])))

    if not cortes:
        logger.info("  ✅ No se detectaron muletillas.")
        shutil.copy2(ruta_entrada, ruta_salida)
        return ruta_salida

    logger.info(f"  ✂  Eliminando {len(cortes)} muletillas...")
    duracion_total = _duracion_video(ruta_entrada)

    mantener = []
    ultimo_fin = 0.0
    for inicio, fin in sorted(cortes):
        if inicio > ultimo_fin + 0.05:
            mantener.append((ultimo_fin, inicio))
        ultimo_fin = max(ultimo_fin, fin)
    if ultimo_fin < duracion_total:
        mantener.append((ultimo_fin, duracion_total))

    if not mantener:
        shutil.copy2(ruta_entrada, ruta_salida)
        return ruta_salida

    expr = "+".join(f"between(t,{i:.3f},{f:.3f})" for i, f in mantener)
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", ruta_entrada,
        "-vf", f"select='{expr}',setpts=N/FRAME_RATE/TB",
        "-af", f"aselect='{expr}',asetpts=N/SR/TB",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        ruta_salida
    ], "eliminar_muletillas")
    logger.info(f"  ✅ Muletillas eliminadas → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── Paso 3: Color grading ───────────────────────────────

def aplicar_color_grading(
    ruta_entrada: str,
    ruta_salida: str,
    estilo: str = "cinematico"
) -> str:
    """Aplica color grading automático con FFmpeg curves + eq."""
    filtro = ESTILOS_COLOR.get(estilo, ESTILOS_COLOR["cinematico"])
    logger.info(f"  🎨 Aplicando color grading '{estilo}'...")
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", ruta_entrada,
        "-vf", filtro,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        ruta_salida
    ], "color_grading")
    logger.info(f"  ✅ Color grading aplicado → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── Paso 4: Audio fades ─────────────────────────────────

def anadir_audio_fades(
    ruta_entrada: str,
    ruta_salida: str,
    duracion_fade: float = 0.03
) -> str:
    """Añade fades de audio de 30ms al inicio y fin del vídeo."""
    duracion = _duracion_video(ruta_entrada)
    fade_out = max(0.0, duracion - duracion_fade)
    filtro = (
        f"afade=t=in:st=0:d={duracion_fade},"
        f"afade=t=out:st={fade_out:.3f}:d={duracion_fade}"
    )
    logger.info(f"  🔊 Añadiendo audio fades ({int(duracion_fade*1000)}ms)...")
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", ruta_entrada,
        "-af", filtro,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        ruta_salida
    ], "audio_fades")
    logger.info(f"  ✅ Audio fades aplicados → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── Mejora real (FFmpeg, sin IA) ───────────────────────

NIVELES_MEJORA = {
    "suave": (
        "hqdn3d=2:2:3:3,"                    # reduccion ruido suave
        "unsharp=3:3:0.8:3:3:0,"             # nitidez moderada
        "eq=saturation=1.1:contrast=1.05"    # color ligero
    ),
    "media": (
        "hqdn3d=3:3:6:6,"                    # reduccion ruido media
        "unsharp=5:5:1.2:5:5:0,"             # nitidez real
        "eq=saturation=1.15:contrast=1.10:brightness=0.02"
    ),
    "fuerte": (
        "hqdn3d=4:4:8:8,"                    # reduccion ruido fuerte
        "unsharp=7:7:1.8:7:7:0,"             # maxima nitidez
        "eq=saturation=1.2:contrast=1.15:brightness=0.03,"
        "curves=r='0/0 0.5/0.53 1/1':"
        "g='0/0 0.5/0.51 1/1':"
        "b='0/0 0.5/0.49 1/0.97'"           # tono ligeramente calido
    ),
}


def mejorar_imagen_real(
    ruta_entrada: str,
    ruta_salida: str,
    nivel: str = "media"
) -> str:
    """Mejora una imagen o video con FFmpeg puro, sin IA.

    Aplica: reduccion de ruido, nitidez real y correccion de color.
    NO plastifica ni suaviza como Real-ESRGAN — resultado natural.

    Args:
        ruta_entrada: Ruta al archivo original.
        ruta_salida:  Ruta de salida.
        nivel:        'suave' | 'media' | 'fuerte'

    Returns:
        Ruta al archivo mejorado.
    """
    filtro = NIVELES_MEJORA.get(nivel, NIVELES_MEJORA["media"])
    ext    = os.path.splitext(ruta_entrada)[1].lower()
    es_imagen = ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp")

    logger.info(f"  🔧 Mejora real FFmpeg nivel='{nivel}' ({'imagen' if es_imagen else 'video'})...")

    if es_imagen:
        cmd = [
            "ffmpeg", "-y", "-i", ruta_entrada,
            "-vf", filtro,
            "-q:v", "2",        # maxima calidad JPEG
            ruta_salida
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", ruta_entrada,
            "-vf", filtro,
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "copy",
            ruta_salida
        ]

    _run_ffmpeg(cmd, "mejorar_imagen_real")
    logger.info(f"  ✅ Mejora real aplicada → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── Orquestador principal ───────────────────────────────

def aplicar_todas_mejoras(
    ruta_entrada: str,
    ruta_salida: str,
    config: dict = None
) -> dict:
    """Aplica todas las mejoras en cadena sobre un vídeo.

    Pipeline:
        1. Cortar silencios (FFmpeg)
        2. Eliminar muletillas (Whisper, opcional)
        3. Color grading cinematográfico (FFmpeg)
        4. Fades de audio 30ms (FFmpeg)

    Args:
        ruta_entrada: Ruta al vídeo original.
        ruta_salida:  Ruta al vídeo final mejorado.
        config:       Diccionario de opciones (ver defaults).

    Returns:
        dict con exito (bool), archivo (str), pasos (list).
    """
    cfg = {
        "cortar_silencios":    True,
        "eliminar_muletillas": False,
        "color_grading":       True,
        "estilo_color":        "cinematico",
        "audio_fades":         True,
        "duracion_fade":       0.03,
        "idioma":              "es",
        "umbral_silencio_db":  -35.0,
        "duracion_silencio_s": 0.6,
        **(config or {}),
    }

    carpeta = os.path.dirname(ruta_salida) or "."
    base    = os.path.splitext(os.path.basename(ruta_entrada))[0]
    temps   = []
    pasos   = []

    def _temp(sufijo):
        p = os.path.join(carpeta, f"_tmp_{sufijo}_{base}.mp4")
        temps.append(p)
        return p

    try:
        actual = ruta_entrada
        logger.info("=" * 55)
        logger.info("MÓDULO 5 — Mejoras Automáticas de Vídeo")
        logger.info("=" * 55)

        if cfg["cortar_silencios"]:
            actual = cortar_silencios(
                actual, _temp("sil"),
                umbral_db=cfg["umbral_silencio_db"],
                duracion_min=cfg["duracion_silencio_s"]
            )
            pasos.append("silencios")

        if cfg["eliminar_muletillas"]:
            actual = eliminar_muletillas(actual, _temp("mul"), idioma=cfg["idioma"])
            pasos.append("muletillas")

        if cfg["color_grading"]:
            actual = aplicar_color_grading(actual, _temp("col"), estilo=cfg["estilo_color"])
            pasos.append("color_grading")

        if cfg["audio_fades"]:
            actual = anadir_audio_fades(actual, ruta_salida, duracion_fade=cfg["duracion_fade"])
            pasos.append("audio_fades")
        else:
            shutil.copy2(actual, ruta_salida)

        logger.info("=" * 55)
        logger.info(f"✅ Pipeline completado: {', '.join(pasos)}")
        logger.info(f"   Salida → {ruta_salida}")
        logger.info("=" * 55)
        return {"exito": True, "archivo": ruta_salida, "pasos": pasos}

    except Exception as e:
        logger.error(f"❌ Error en Módulo 5: {e}")
        return {"exito": False, "error": str(e), "pasos": pasos}

    finally:
        for t in temps:
            if os.path.exists(t):
                try:
                    os.remove(t)
                except OSError:
                    pass

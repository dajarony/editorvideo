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
1. Elimina silencios largos (FFmpeg silencedetect; mismos cortes en imagen y audio)
2. Elimina muletillas: umm, eh, este... (Whisper word timestamps)
3. Color grading cinematográfico (FFmpeg curves + eq)
4. Fades de audio en inicio/fin (30ms, FFmpeg afade)
5. Mejora visual real: resolucion x2, brillo, viveza y nitidez sin denoise agresivo

Salidas:
- Vídeo procesado con todas las mejoras aplicadas
═══════════════════════════════════════════════════════════
"""

import os
import json
import shutil
import subprocess
import tempfile
import importlib.util
from .utilidades import binario, logger


# ─── Constantes ─────────────────────────────────────────

MULETILLAS = {
    "es": ["umm", "uhh", "eh", "este", "bueno", "mmm", "ahh", "pues", "o sea"],
    "en": ["umm", "uhh", "uh", "like", "you know", "basically", "literally"],
}

ESTILOS_COLOR = {
    "natural_claro": (
        "curves=all='0/0.025 0.25/0.30 0.50/0.54 0.75/0.78 1/1',"
        "eq=saturation=1.08:contrast=1.03:brightness=0.01,"
        "unsharp=3:3:0.55:3:3:0"
    ),
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
        "eq=saturation=1.06:contrast=1.03:brightness=0.015,"
        "unsharp=3:3:0.65:3:3:0"
    ),
}


# ─── Helpers ────────────────────────────────────────────

def _duracion_video(ruta: str) -> float:
    """Devuelve la duración en segundos de un vídeo."""
    cmd = [binario("ffprobe"), "-v", "quiet", "-print_format", "json", "-show_format", ruta]
    res = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(res.stdout)
    return float(info["format"]["duration"])


def _run_ffmpeg(cmd: list, descripcion: str):
    """Ejecuta FFmpeg y lanza excepción si falla."""
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"FFmpeg falló en '{descripcion}':\n{resultado.stderr[-800:]}")


# ─── Paso 1: Cortar silencios ────────────────────────────

def _es_imagen(ruta: str) -> bool:
    return os.path.splitext(ruta)[1].lower() in (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def _brillo_medio(ruta: str) -> float | None:
    """Calcula brillo medio aproximado (YAVG 0-255) con una muestra de frames."""
    filtro = (
        "fps=1,scale=320:-1:force_original_aspect_ratio=decrease,"
        "signalstats,metadata=print:key=lavfi.signalstats.YAVG"
    )
    res = subprocess.run(
        [binario("ffmpeg"), "-i", ruta, "-vf", filtro, "-frames:v", "8", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    valores = []
    for linea in (res.stderr or res.stdout or "").splitlines():
        if "lavfi.signalstats.YAVG=" not in linea:
            continue
        try:
            valores.append(float(linea.rsplit("=", 1)[1]))
        except ValueError:
            pass
    if not valores:
        return None
    return sum(valores) / len(valores)


def _proteger_brillo_original(ruta_referencia: str, ruta_salida: str) -> None:
    """Evita que una mejora visual salga perceptiblemente mas oscura."""
    brillo_ref = _brillo_medio(ruta_referencia)
    brillo_out = _brillo_medio(ruta_salida)
    if brillo_ref is None or brillo_out is None:
        return

    diferencia = brillo_ref - brillo_out
    if diferencia <= 2.0:
        return

    ajuste = min(0.06, max(0.008, diferencia / 255.0))
    filtro = f"eq=brightness={ajuste:.4f}:gamma=1.025"
    base, ext = os.path.splitext(ruta_salida)
    tmp = f"{base}_brillo_tmp{ext}"

    logger.info(
        f"  Ajustando brillo automatico (+{ajuste:.3f}) "
        f"para evitar oscurecimiento ({brillo_out:.1f} -> {brillo_ref:.1f})."
    )

    try:
        if _es_imagen(ruta_salida):
            cmd = [binario("ffmpeg"), "-y", "-i", ruta_salida, "-vf", filtro, "-q:v", "2", tmp]
        else:
            cmd = [
                binario("ffmpeg"), "-y", "-i", ruta_salida,
                "-map", "0:v:0", "-map", "0:a?",
                "-vf", filtro,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
                "-movflags", "+faststart",
                "-c:a", "copy",
                tmp
            ]
        _run_ffmpeg(cmd, "proteccion_brillo")
        os.replace(tmp, ruta_salida)
    except Exception as e:
        logger.warning(f"  No se pudo aplicar proteccion de brillo: {e}")
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _silencios_detectados(registro: str, duracion_total: float) -> list:
    """Tramos (inicio, fin) que silencedetect anotó en su registro.

    Un silencio que llega hasta el final no tiene `silence_end`: termina en `duracion_total`.
    """
    silencios, inicio = [], None
    for linea in registro.splitlines():
        if "silence_start:" in linea:
            inicio = float(linea.split("silence_start:")[1].split()[0])
        elif "silence_end:" in linea and inicio is not None:
            silencios.append((inicio, float(linea.split("silence_end:")[1].split()[0])))
            inicio = None
    if inicio is not None:
        silencios.append((inicio, duracion_total))
    return silencios


def _tramos_sin_silencio(silencios: list, duracion_total: float, margen: float = 0.15) -> list:
    """Tramos a conservar: todo menos cada silencio, dejando `margen` s de él a cada lado
    para que la voz no empiece ni termine de golpe."""
    mantener, cursor = [], 0.0
    for inicio, fin in sorted(silencios):
        corte_inicio, corte_fin = max(inicio + margen, cursor), fin - margen
        if corte_fin <= corte_inicio:
            continue
        if corte_inicio > cursor:
            mantener.append((round(cursor, 4), round(corte_inicio, 4)))
        cursor = corte_fin
    if cursor < duracion_total:
        mantener.append((round(cursor, 4), round(duracion_total, 4)))
    return mantener


def _recortar_tramos(ruta_entrada: str, ruta_salida: str, mantener: list, descripcion: str) -> None:
    """Conserva solo `mantener` en la imagen Y en el sonido, con los mismos cortes, para que no se desincronicen."""
    expr = "+".join(f"between(t,{i:.3f},{f:.3f})" for i, f in mantener)
    _run_ffmpeg([
        binario("ffmpeg"), "-y", "-i", ruta_entrada,
        "-vf", f"select='{expr}',setpts=N/FRAME_RATE/TB",
        "-af", f"aselect='{expr}',asetpts=N/SR/TB",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        ruta_salida
    ], descripcion)


def cortar_silencios(
    ruta_entrada: str,
    ruta_salida: str,
    umbral_db: float = -35.0,
    duracion_min: float = 0.6
) -> str:
    """Elimina los silencios largos del vídeo, cortando los mismos tramos en la imagen y en el audio."""
    logger.info(f"  ✂  Eliminando silencios (umbral={umbral_db}dB, min={duracion_min}s)...")
    if not _tiene_audio(ruta_entrada):
        logger.info("  ✅ El vídeo no tiene audio: no hay silencios que quitar.")
        shutil.copy2(ruta_entrada, ruta_salida)
        return ruta_salida

    registro = subprocess.run(
        [binario("ffmpeg"), "-hide_banner", "-nostats", "-i", ruta_entrada,
         "-af", f"silencedetect=noise={umbral_db}dB:d={duracion_min}", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore"
    ).stderr
    duracion_total = _duracion_video(ruta_entrada)
    mantener = _tramos_sin_silencio(_silencios_detectados(registro, duracion_total), duracion_total)

    if not mantener or mantener == [(0.0, round(duracion_total, 4))]:
        logger.info("  ✅ No hay silencios largos que quitar.")
        shutil.copy2(ruta_entrada, ruta_salida)
        return ruta_salida

    _recortar_tramos(ruta_entrada, ruta_salida, mantener, "cortar_silencios")
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

    _recortar_tramos(ruta_entrada, ruta_salida, mantener, "eliminar_muletillas")
    logger.info(f"  ✅ Muletillas eliminadas → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── Paso 3: Color grading ───────────────────────────────

def aplicar_color_grading(
    ruta_entrada: str,
    ruta_salida: str,
    estilo: str = "natural_claro"
) -> str:
    """Aplica color grading automático con FFmpeg curves + eq."""
    filtro = ESTILOS_COLOR.get(estilo, ESTILOS_COLOR["natural_claro"])
    logger.info(f"  🎨 Aplicando color grading '{estilo}'...")
    _run_ffmpeg([
        binario("ffmpeg"), "-y", "-i", ruta_entrada,
        "-vf", filtro,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        ruta_salida
    ], "color_grading")
    _proteger_brillo_original(ruta_entrada, ruta_salida)
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
        binario("ffmpeg"), "-y", "-i", ruta_entrada,
        "-af", filtro,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        ruta_salida
    ], "audio_fades")
    logger.info(f"  ✅ Audio fades aplicados → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── Mejora real (FFmpeg, sin IA) ───────────────────────

def convertir_vertical_9_16(ruta_entrada: str, ruta_salida: str) -> str:
    """Convierte un video a formato vertical 1080x1920 con recorte centrado."""
    logger.info("  Convirtiendo a formato vertical 9:16...")
    filtro = (
        "scale='if(gt(a,9/16),-2,1080)':'if(gt(a,9/16),1920,-2)',"
        "crop=1080:1920:(iw-1080)/2:(ih-1920)/2,setsar=1"
    )
    _run_ffmpeg([
        binario("ffmpeg"), "-y", "-i", ruta_entrada,
        "-vf", filtro,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        ruta_salida
    ], "convertir_vertical_9_16")
    logger.info(f"  Video vertical generado -> {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── Subtitulos automaticos (Whisper) ───────────────────

def _segundos_a_srt(segundos: float) -> str:
    """Convierte segundos a formato SRT: HH:MM:SS,mmm."""
    total_ms = max(0, int(round(segundos * 1000)))
    horas, resto = divmod(total_ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segs, milisegs = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milisegs:03d}"


def _transcribir_segmentos(ruta: str, idioma: str, modelo_whisper: str) -> list:
    """Transcribe audio/video y devuelve lista de (inicio, fin, texto).

    Usa faster-whisper si esta disponible (ligero y rapido);
    si no, recurre a openai-whisper.
    """
    # faster-whisper — preferido (ligero, rapido, sin PyTorch)
    try:
        from faster_whisper import WhisperModel
        logger.info(f"  🎙  Transcribiendo con faster-whisper (modelo={modelo_whisper})...")
        modelo = WhisperModel(modelo_whisper, device="cpu", compute_type="int8")
        segmentos, _info = modelo.transcribe(ruta, language=idioma)
        return [
            (float(s.start), float(s.end), s.text.strip())
            for s in segmentos if s.text and s.text.strip()
        ]
    except ImportError:
        pass

    # openai-whisper — alternativa
    try:
        import whisper
        logger.info(f"  🎙  Transcribiendo con openai-whisper (modelo={modelo_whisper})...")
        modelo = whisper.load_model(modelo_whisper)
        resultado = modelo.transcribe(ruta, language=idioma)
        return [
            (float(s["start"]), float(s["end"]), s["text"].strip())
            for s in resultado.get("segments", [])
            if s.get("text", "").strip()
        ]
    except ImportError:
        pass

    raise RuntimeError(
        "No hay motor de transcripcion instalado.\n"
        "Instala uno con: pip install faster-whisper"
    )


def anadir_subtitulos_automaticos(
    ruta_entrada: str,
    ruta_salida: str,
    idioma: str = "es",
    modelo_whisper: str = "base"
) -> str:
    """Transcribe cualquier video y quema los subtitulos en el.

    Funciona con cualquier video, sin necesidad de la estructura de proyecto.

    Args:
        ruta_entrada:   Video original.
        ruta_salida:    Video de salida con subtitulos quemados.
        idioma:         Idioma de la voz ('es', 'en'...).
        modelo_whisper: Modelo de transcripcion ('tiny', 'base', 'small', 'medium').

    Returns:
        Ruta al video con subtitulos.
    """
    segmentos = _transcribir_segmentos(ruta_entrada, idioma, modelo_whisper)
    if not segmentos:
        logger.warning("  ⚠  No se detecto voz. Se copia el video sin subtitulos.")
        shutil.copy2(ruta_entrada, ruta_salida)
        return ruta_salida

    # Generar SRT (nombre simple junto a la salida, para el filtro de FFmpeg)
    carpeta = os.path.dirname(os.path.abspath(ruta_salida)) or "."
    ruta_srt = os.path.join(carpeta, "_tmp_subs_auto.srt")
    lineas = []
    for i, (inicio, fin, texto) in enumerate(segmentos, 1):
        lineas.append(str(i))
        lineas.append(f"{_segundos_a_srt(inicio)} --> {_segundos_a_srt(fin)}")
        lineas.append(texto)
        lineas.append("")
    with open(ruta_srt, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lineas))
    logger.info(f"  ✂  {len(segmentos)} subtitulos detectados. Quemando en el video...")

    # Estilo: texto blanco, borde negro, legible (BGR hex de ASS)
    estilo = (
        "FontName=Arial,FontSize=16,"
        "PrimaryColour=&H00FFFFFF,"     # blanco
        "OutlineColour=&H00000000,"     # borde negro
        "BorderStyle=1,Outline=2,Shadow=1,MarginV=35"
    )
    filtro = f"subtitles=_tmp_subs_auto.srt:force_style='{estilo}'"

    cmd = [
        binario("ffmpeg"), "-y", "-i", os.path.abspath(ruta_entrada),
        "-vf", filtro,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        os.path.abspath(ruta_salida)
    ]
    resultado_ff = subprocess.run(
        cmd, cwd=carpeta, capture_output=True, text=True,
        encoding="utf-8", errors="ignore"
    )
    try:
        os.remove(ruta_srt)
    except OSError:
        pass

    if resultado_ff.returncode != 0:
        detalle = (resultado_ff.stderr or resultado_ff.stdout or "").strip()[-700:]
        raise RuntimeError(f"FFmpeg fallo al incrustar subtitulos:\n{detalle}")

    logger.info(f"  ✅ Subtitulos incrustados → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── Limpiar voz / quitar ruido de fondo ────────────────

# Cadena de filtros FFmpeg para realzar la voz y reducir ruido ambiente.
# highpass/lowpass recortan fuera del rango de la voz humana;
# afftdn reduce ruido de banda ancha; dynaudnorm nivela y sube la voz.
FILTROS_LIMPIAR_VOZ = {
    "suave": (
        "highpass=f=90,"
        "afftdn=nr=10:nf=-25,"
        "dynaudnorm=f=250:g=5"
    ),
    "media": (
        "highpass=f=110,"
        "lowpass=f=9000,"
        "afftdn=nr=20:nf=-30,"
        "dynaudnorm=f=200:g=7"
    ),
    "fuerte": (
        "highpass=f=130,"
        "lowpass=f=8000,"
        "afftdn=nr=28:nf=-35,"
        "afftdn=nr=14:nf=-30,"
        "dynaudnorm=f=150:g=9"
    ),
}


def _tiene_audio(ruta: str) -> bool:
    """Indica si el archivo tiene al menos una pista de audio."""
    res = subprocess.run(
        [binario("ffprobe"), "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", ruta],
        capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    return "audio" in (res.stdout or "")


def separacion_voz_ia_disponible() -> bool:
    """Indica si Demucs esta instalado para separar voz/musica con IA."""
    return (
        importlib.util.find_spec("demucs") is not None and
        importlib.util.find_spec("torch") is not None
    )


def _extraer_audio_wav(ruta_entrada: str, ruta_audio: str) -> None:
    """Extrae el audio del video a WAV PCM para Demucs."""
    _run_ffmpeg([
        binario("ffmpeg"), "-y", "-i", ruta_entrada,
        "-vn", "-ac", "2", "-ar", "44100",
        "-c:a", "pcm_s16le",
        ruta_audio
    ], "extraer_audio_para_demucs")


def _limpiar_audio_wav(ruta_audio: str, ruta_salida: str, nivel: str) -> None:
    """Aplica limpieza suave a la pista vocal ya separada."""
    logger.info("  Ajustando ruido residual en la pista vocal separada...")

    filtro = FILTROS_LIMPIAR_VOZ.get(nivel, FILTROS_LIMPIAR_VOZ["media"])
    _run_ffmpeg([
        binario("ffmpeg"), "-y", "-i", ruta_audio,
        "-af", filtro,
        "-ac", "2", "-ar", "48000",
        "-c:a", "pcm_s16le",
        ruta_salida
    ], "limpiar_vocales_separadas")


def _unir_video_con_audio(ruta_video: str, ruta_audio: str, ruta_salida: str) -> None:
    """Conserva el video original y sustituye su audio por la voz aislada."""
    _run_ffmpeg([
        binario("ffmpeg"), "-y", "-i", ruta_video, "-i", ruta_audio,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        "-shortest",
        ruta_salida
    ], "unir_video_con_voz_aislada")


def _guardar_wav_tensor(audio, samplerate: int, ruta_salida: str) -> None:
    """Guarda un tensor Demucs como WAV sin depender del guardado de torchaudio."""
    import numpy as np
    from scipy.io import wavfile

    data = audio.detach().cpu().float().numpy()
    if data.ndim == 2:
        data = data.T  # Demucs usa canales x muestras; scipy usa muestras x canales.
    pico = float(np.max(np.abs(data))) if data.size else 0.0
    if pico > 1.0:
        data = data / pico
    data = (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16)
    wavfile.write(ruta_salida, samplerate, data)


def aislar_voz_con_ia(
    ruta_entrada: str,
    ruta_salida: str,
    nivel: str = "media"
) -> str:
    """Separa voz de musica/fondo con Demucs y recompone el video."""
    if not separacion_voz_ia_disponible():
        raise RuntimeError(
            "La separacion de voz por IA requiere Demucs y Torch instalados."
        )

    logger.info("  🎙️ Aislando voz con IA (Demucs: separa voz de musica/fondo)...")
    modelo = "htdemucs"
    with tempfile.TemporaryDirectory(prefix="aegs_voz_") as tmpdir:
        audio_wav = os.path.join(tmpdir, "audio.wav")
        salida_demucs = os.path.join(tmpdir, "demucs")
        voz_limpia = os.path.join(tmpdir, "vocals_clean.wav")

        _extraer_audio_wav(ruta_entrada, audio_wav)

        try:
            import torch
            from demucs.audio import AudioFile
            from demucs.apply import apply_model
            from demucs.pretrained import get_model

            model = get_model(modelo)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)
            model.eval()

            wav = AudioFile(audio_wav).read(
                streams=0,
                samplerate=model.samplerate,
                channels=model.audio_channels
            )
            ref = wav.mean(0)
            wav -= ref.mean()
            ref_std = ref.std()
            if float(ref_std) < 1e-8:
                ref_std = torch.tensor(1.0, device=wav.device)
            wav /= ref_std

            with torch.no_grad():
                sources = apply_model(
                    model, wav[None], device=device, shifts=1,
                    split=True, overlap=0.1, progress=False,
                    num_workers=0, segment=7
                )[0]
            sources *= ref_std
            sources += ref.mean()
            vocals = os.path.join(salida_demucs, modelo, "audio", "vocals.wav")
            os.makedirs(os.path.dirname(vocals), exist_ok=True)
            _guardar_wav_tensor(
                sources[model.sources.index("vocals")],
                model.samplerate,
                vocals
            )
        except Exception as exc:
            raise RuntimeError(
                "Demucs fallo al separar voz/musica.\n"
                "La primera vez puede necesitar descargar el modelo htdemucs.\n\n"
                f"Detalle:\n{exc}"
            ) from exc

        vocals = os.path.join(salida_demucs, modelo, "audio", "vocals.wav")
        if not os.path.exists(vocals):
            raise RuntimeError(
                f"Demucs no genero la pista vocal esperada:\n{vocals}"
            )

        _limpiar_audio_wav(vocals, voz_limpia, nivel)
        _unir_video_con_audio(ruta_entrada, voz_limpia, ruta_salida)

    logger.info(f"  ✅ Voz aislada con IA -> {os.path.basename(ruta_salida)}")
    return ruta_salida


def limpiar_voz(
    ruta_entrada: str,
    ruta_salida: str,
    nivel: str = "media"
) -> str:
    """Aisla la voz con IA cuando es posible; si no, aplica limpieza basica.

    Demucs separa voz/musica de verdad. Los filtros FFmpeg se mantienen como
    respaldo para equipos sin Demucs, pero esos filtros solo reducen ruido de
    banda ancha y no pueden eliminar una cancion mezclada con la voz.

    Args:
        ruta_entrada: Video original.
        ruta_salida:  Video con el audio limpiado.
        nivel:        'suave' | 'media' | 'fuerte'

    Returns:
        Ruta al video con la voz limpiada.
    """
    if not _tiene_audio(ruta_entrada):
        logger.warning("  ⚠  El video no tiene audio. Se copia sin cambios.")
        shutil.copy2(ruta_entrada, ruta_salida)
        return ruta_salida

    if separacion_voz_ia_disponible():
        return aislar_voz_con_ia(ruta_entrada, ruta_salida, nivel=nivel)

    logger.warning(
        "  ⚠  Demucs no esta instalado: aplico limpieza basica FFmpeg. "
        "Esto NO puede quitar musica de fondo mezclada con la voz."
    )

    filtro = FILTROS_LIMPIAR_VOZ.get(nivel, FILTROS_LIMPIAR_VOZ["media"])
    logger.info(f"  🔊 Limpiando voz / reduciendo ruido de fondo (nivel={nivel})...")
    _run_ffmpeg([
        binario("ffmpeg"), "-y", "-i", ruta_entrada,
        "-af", filtro,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        ruta_salida
    ], "limpiar_voz")
    logger.info(f"  ✅ Voz limpiada → {os.path.basename(ruta_salida)}")
    return ruta_salida


# Mejora orientada a brillo + viveza + nitidez (NO apaga, NO plastifica).
# Sube resolucion x2 (lanczos), enfoca, sube color y brillo.
# Sin hqdn3d: la reduccion de ruido es lo que dejaba la imagen plana/apagada.
NIVELES_MEJORA = {
    "suave": (
        "scale=iw*2:ih*2:flags=lanczos,"     # x2 resolucion = mas nitido
        "unsharp=5:5:0.5:5:5:0,"             # enfoque ligero
        "eq=saturation=1.12:brightness=0.03:contrast=1.03"
    ),
    "media": (
        "scale=iw*2:ih*2:flags=lanczos,"     # x2 resolucion
        "unsharp=5:5:0.85:5:5:0,"            # enfoque real
        "eq=saturation=1.20:brightness=0.04:contrast=1.05"
    ),
    "fuerte": (
        "scale=iw*2:ih*2:flags=lanczos,"     # x2 resolucion
        "unsharp=5:5:1.15:5:5:0,"            # enfoque alto
        "eq=saturation=1.28:brightness=0.05:contrast=1.06"
    ),
}


def mejorar_imagen_real(
    ruta_entrada: str,
    ruta_salida: str,
    nivel: str = "media"
) -> str:
    """Mejora una imagen o video con FFmpeg puro, sin IA.

    Aplica resolucion x2 con Lanczos, nitidez controlada, brillo y color.
    No usa denoise agresivo porque apaga textura y deja la imagen plana.

    Args:
        ruta_entrada: Ruta al archivo original.
        ruta_salida:  Ruta de salida.
        nivel:        'suave' | 'media' | 'fuerte'

    Returns:
        Ruta al archivo mejorado.
    """
    filtro = NIVELES_MEJORA.get(nivel, NIVELES_MEJORA["media"])
    es_imagen = _es_imagen(ruta_entrada)

    logger.info(f"  🔧 Mejora real FFmpeg nivel='{nivel}' ({'imagen' if es_imagen else 'video'})...")

    if es_imagen:
        cmd = [
            binario("ffmpeg"), "-y", "-i", ruta_entrada,
            "-vf", filtro,
            "-q:v", "2",        # maxima calidad JPEG
            ruta_salida
        ]
    else:
        cmd = [
            binario("ffmpeg"), "-y", "-i", ruta_entrada,
            "-vf", filtro,
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
            "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            ruta_salida
        ]

    _run_ffmpeg(cmd, "mejorar_imagen_real")
    _proteger_brillo_original(ruta_entrada, ruta_salida)
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
        "estilo_color":        "natural_claro",
        "mejora_real":         True,
        "nivel_mejora":        "media",
        "formato_vertical":    False,
        "limpiar_voz":         False,
        "nivel_voz":           "media",
        "subtitulos":          False,
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

        if cfg["mejora_real"]:
            actual = mejorar_imagen_real(actual, _temp("real"), nivel=cfg["nivel_mejora"])
            pasos.append("mejora_real")

        if cfg["formato_vertical"]:
            actual = convertir_vertical_9_16(actual, _temp("vertical"))
            pasos.append("vertical_9_16")

        if cfg["limpiar_voz"]:
            actual = limpiar_voz(actual, _temp("voz"), nivel=cfg["nivel_voz"])
            pasos.append("limpiar_voz")

        if cfg["subtitulos"]:
            actual = anadir_subtitulos_automaticos(
                actual, _temp("subs"), idioma=cfg["idioma"]
            )
            pasos.append("subtitulos")

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

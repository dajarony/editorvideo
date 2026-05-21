# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.0
═══════════════════════════════════════════════════════════
Archivo: modulos/subtitulos.py
Tipo: Lógica → Postproducción (Módulo 4)
Dependencias: 5 (os, json, subprocess, whisper, configuracion)

Entradas:
- timeline.json y narracion_duraciones.json.
- Pistas MP3 individuales de narración (sin música — Ajuste 4).

Acciones:
1. Transcribe cada pista limpia de voz usando Whisper.
2. Suma el offset temporal de la escena a cada frase detectada.
3. Exporta un SRT unificado con timestamps globales.
4. Quema el SRT en el vídeo final usando FFmpeg force_style.

Salidas:
- output/subtitulos.srt
- output/video_final_subtitulado.mp4
═══════════════════════════════════════════════════════════
"""

import os
import json
import subprocess
from configuracion import (
    CARPETA_OUTPUT, ARCHIVO_TIMELINE, ARCHIVO_DURACIONES,
    ARCHIVO_VIDEO_FINAL, ARCHIVO_SRT, ARCHIVO_VIDEO_SUB,
    MODELO_WHISPER
)
from .utilidades import logger, ruta_segura_proyecto, validar_fuente_subtitulos


def segundos_a_srt(segundos: float) -> str:
    """Convierte segundos (float) al formato SRT: HH:MM:SS,mmm.

    Args:
        segundos: Tiempo en segundos con decimales.

    Returns:
        String en formato '00:01:23,456'.
    """
    total_ms = max(0, int(round(segundos * 1000)))
    horas, resto = divmod(total_ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segs, milisegs = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milisegs:03d}"


def generar_srt_matematico(ruta_proyecto: str, datos_proyecto: dict) -> str:
    """Genera un archivo SRT con timestamps globales sincronizados.

    Para cada escena:
    1. Transcribe el MP3 limpio de narración (sin música) con Whisper.
    2. Calcula el offset global: inicio_escena + pausa_antes.
    3. Suma el offset a cada timestamp de Whisper para cuadrar
       con el vídeo final.

    Esto produce subtítulos perfectamente sincronizados porque
    Whisper trabaja sobre audio sin ruido y los offsets vienen
    del timeline matemático.

    Args:
        ruta_proyecto: Ruta base del proyecto.
        datos_proyecto: Diccionario del JSON del proyecto.

    Returns:
        Ruta absoluta al archivo SRT generado.
    """
    ruta_timeline = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_TIMELINE)
    ruta_duraciones = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_DURACIONES)
    ruta_srt = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_SRT)

    with open(ruta_timeline, 'r', encoding='utf-8') as f:
        timeline = json.load(f)
    with open(ruta_duraciones, 'r', encoding='utf-8') as f:
        duraciones = json.load(f)

    # Diccionario de escenas para acceso rápido a las pausas
    escenas_config = {e["id"]: e for e in datos_proyecto.get("escenas", [])}

    logger.info(f"Cargando modelo Whisper '{MODELO_WHISPER}' (puede tardar la primera vez)...")
    try:
        import whisper
    except ImportError:
        raise ImportError(
            "Whisper no está instalado. Ejecuta: pip install openai-whisper"
        )
    modelo = whisper.load_model(MODELO_WHISPER)

    lineas_srt = []
    indice_sub = 1
    total = len(timeline["escenas"])

    for idx, escena in enumerate(timeline["escenas"], 1):
        id_escena = escena["id"]
        if id_escena not in duraciones:
            continue

        archivo_mp3 = ruta_segura_proyecto(
            ruta_proyecto, duraciones[id_escena]["archivo"]
        )
        pausa_antes = float(escenas_config[id_escena].get("pausa_antes_seg", 0))

        # Offset global = momento exacto donde la voz empieza en el vídeo final
        offset_global = escena["inicio_seg"] + pausa_antes

        logger.info(f"  [{idx}/{total}] Transcribiendo '{id_escena}' con Whisper...")
        resultado = modelo.transcribe(
            archivo_mp3,
            language=datos_proyecto.get("idioma", "es")
        )

        for segmento in resultado["segments"]:
            inicio_real = offset_global + segmento["start"]
            fin_real = offset_global + segmento["end"]
            texto = segmento["text"].strip()

            if not texto:
                continue

            lineas_srt.append(str(indice_sub))
            lineas_srt.append(
                f"{segundos_a_srt(inicio_real)} --> {segundos_a_srt(fin_real)}"
            )
            lineas_srt.append(texto)
            lineas_srt.append("")  # Línea en blanco separadora SRT
            indice_sub += 1

    # FFmpeg en Windows lee mejor SRT con BOM UTF-8
    with open(ruta_srt, 'w', encoding='utf-8-sig') as f:
        f.write("\n".join(lineas_srt))

    logger.info(f"SRT generado: {indice_sub - 1} subtítulos → {ruta_srt}")
    return ruta_srt


def incrustar_subtitulos(
    ruta_proyecto: str,
    config_subs: dict,
    ruta_srt: str
) -> str:
    """Quema los subtítulos en el vídeo usando FFmpeg.

    Ejecuta FFmpeg desde la carpeta output/ para evitar problemas
    con rutas absolutas de Windows en el filtro 'subtitles'.

    Args:
        ruta_proyecto: Ruta base del proyecto.
        config_subs: Diccionario con la configuración de subtítulos del JSON.
        ruta_srt: Ruta absoluta al archivo SRT.

    Returns:
        Ruta absoluta al vídeo con subtítulos incrustados.
    """
    ruta_video_out = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_VIDEO_SUB)

    # FFmpeg se ejecuta desde output/ para usar rutas relativas
    # (las absolutas de Windows rompen el filtro 'subtitles').
    ruta_trabajo = os.path.join(ruta_proyecto, CARPETA_OUTPUT)
    nombre_in = ARCHIVO_VIDEO_FINAL
    nombre_out = ARCHIVO_VIDEO_SUB
    nombre_srt = ARCHIVO_SRT

    fuente = config_subs.get("fuente", "Arial")
    tamano = config_subs.get("tamano", 24)
    if not validar_fuente_subtitulos(fuente):
        raise ValueError("Fuente de subtitulos invalida.")
    if isinstance(tamano, bool) or not isinstance(tamano, (int, float)):
        raise ValueError("Tamano de subtitulos invalido.")
    tamano = int(tamano)
    if tamano < 8 or tamano > 96:
        raise ValueError("Tamano de subtitulos fuera de rango.")

    # Estilo forzado para FFmpeg (colores en formato BGR hex de ASS)
    estilo = (
        f"FontName={fuente},"
        f"FontSize={tamano},"
        f"PrimaryColour=&H00FFFFFF,"    # Blanco
        f"OutlineColour=&H00000000,"    # Borde negro
        f"BorderStyle=1"                 # Borde + sombra
    )
    filtro_sub = f"subtitles={nombre_srt}:force_style='{estilo}'"

    comando = [
        "ffmpeg", "-y", "-v", "error",
        "-i", nombre_in,
        "-vf", filtro_sub,
        "-c:a", "copy",     # Audio ya está listo, no recodificar
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-movflags", "+faststart",
        nombre_out
    ]

    logger.info("Incrustando subtítulos en el vídeo (renderizado final)...")
    resultado = subprocess.run(
        comando, cwd=ruta_trabajo, capture_output=True, text=True
    )

    if resultado.returncode != 0:
        logger.error(f"FFmpeg error al incrustar subtítulos: {resultado.stderr}")
        raise RuntimeError("FFmpeg falló al incrustar subtítulos.")

    logger.info(f"Vídeo con subtítulos exportado → {ruta_video_out}")
    return ruta_video_out


def procesar_subtitulos(ruta_proyecto: str, datos_proyecto: dict) -> dict:
    """Orquestador interno del Módulo 4 — Subtítulos.

    Comprueba si los subtítulos están activados en el JSON.
    Si lo están, transcribe con Whisper y quema el SRT en el vídeo.

    Args:
        ruta_proyecto: Ruta base del proyecto.
        datos_proyecto: Diccionario del JSON del proyecto.

    Returns:
        dict con exito (bool), omitido (bool) y archivo (str).
    """
    try:
        config_subs = datos_proyecto.get("subtitulos", {})
        if not config_subs.get("generar", False):
            logger.info("Subtítulos desactivados en el JSON. Omitiendo Módulo 4.")
            return {"exito": True, "omitido": True}

        logger.info("Fase 4.1: Transcripción aislada con Whisper (sin música)...")
        ruta_srt = generar_srt_matematico(ruta_proyecto, datos_proyecto)

        # Modo sidecar: solo SRT, sin quemarlos en el vídeo.
        if config_subs.get("sidecar", False) or not config_subs.get("incrustar", True):
            logger.info("Modo sidecar activo: SRT generado sin quemar en el vídeo.")
            return {
                "exito": True, "omitido": False,
                "archivo": None, "srt": ruta_srt, "sidecar": True
            }

        logger.info("Fase 4.2: Renderizado de subtítulos sobre vídeo...")
        ruta_video_final = incrustar_subtitulos(ruta_proyecto, config_subs, ruta_srt)

        return {
            "exito": True, "omitido": False,
            "archivo": ruta_video_final, "srt": ruta_srt
        }

    except Exception as e:
        logger.error(f"Error en Módulo de Subtítulos: {e}")
        return {"exito": False, "error": str(e)}

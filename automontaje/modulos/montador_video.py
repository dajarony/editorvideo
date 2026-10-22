# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.1
═══════════════════════════════════════════════════════════
Archivo: modulos/montador_video.py
Tipo: Lógica → Montador de Vídeo (Módulo 3)

Entradas:
- proyecto.json, narracion_duraciones.json, audio_mezclado.wav.
- Clips de vídeo originales.

Acciones:
1. Calcular timeline matemático con duraciones exactas por escena.
2. Procesar clips: escalar, recortar, congelar último frame (tpad).
3. Aplicar transiciones:
   - cut             → corte seco
   - fade_from_black → fundido desde negro al inicio
   - fade_to_black   → fundido a negro al final
   - dip_to_black    → micro fade out + in en bordes (sin solapar)
   - crossfade       → xfade REAL entre clips (filter_complex)
4. Concatenar y sincronizar con la pista de audio maestra.

Salidas:
- output/timeline.json
- output/video_final.mp4
═══════════════════════════════════════════════════════════
"""

import os
import json
import math
import subprocess
from configuracion import (
    CARPETA_OUTPUT, CARPETA_TEMP, ARCHIVO_DURACIONES,
    ARCHIVO_TIMELINE, ARCHIVO_AUDIO_MEZCLADO, ARCHIVO_VIDEO_FINAL,
    RESOLUCION_DEFAULT, FPS_DEFAULT, FADE_TRANSICION_SEG
)
from .utilidades import (
    binario,
    logger, obtener_info_media, ruta_segura_proyecto, validar_id_escena,
    validar_resolucion, normalizar_fps
)


# Transiciones que NO solapan clips (se aplican intra-clip)
TRANSICIONES_INTRA = {"cut", "fade_from_black", "fade_to_black", "dip_to_black"}
# Transiciones que SÍ solapan clips (necesitan xfade)
TRANSICIONES_INTER = {"crossfade"}


def _normalizar_transicion(valor: str) -> str:
    """Normaliza nombres legacy de transiciones.

    'crossfade' antiguo (en realidad dip-to-black) sigue valiendo,
    pero ahora el verdadero crossfade usa xfade. Para mantener
    compat, si el usuario pone 'crossfade' lo dejamos pasar y
    se interpreta como xfade real entre clips adyacentes.
    """
    return (valor or "cut").strip().lower()


def _fotograma(segundos: float, fps: int) -> int:
    """Fotograma de la rejilla en `segundos`, redondeando .5 hacia arriba (como Math.round de JS)."""
    return math.floor(segundos * fps + 0.5)


def calcular_timeline(ruta_proyecto: str, datos_proyecto: dict) -> dict:
    """Calcula la duración exacta de cada escena y genera el timeline."""
    ruta_duraciones = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_DURACIONES)
    if not os.path.exists(ruta_duraciones):
        raise FileNotFoundError("Falta narracion_duraciones.json. Ejecuta la Fase 1.")

    with open(ruta_duraciones, 'r', encoding='utf-8') as f:
        duraciones = json.load(f)

    timeline = {"duracion_total_seg": 0.0, "escenas": []}
    cursor_seg = 0.0
    # Con duración estricta, el clip ya viene renderizado a la medida de su escena (Aura Motion Studio).
    estricta = bool(datos_proyecto.get("montaje", {}).get("duracion_estricta", False))
    fps = normalizar_fps(datos_proyecto.get("fps", FPS_DEFAULT))

    for escena in datos_proyecto.get("escenas", []):
        id_escena = escena["id"]
        if not validar_id_escena(id_escena):
            raise ValueError(f"ID de escena inseguro: {id_escena}")
        if id_escena not in duraciones:
            if estricta:
                raise ValueError(
                    f"Modo duración estricta: la escena '{id_escena}' no está en "
                    f"{ARCHIVO_DURACIONES}. Genera su narración (sin --skip-tts) antes de montar."
                )
            logger.warning(f"Escena '{id_escena}' sin audio. Omitida del timeline.")
            continue

        pausa_antes = float(escena.get("pausa_antes_seg", 0))
        pausa_despues = float(escena.get("pausa_despues_seg", 0))
        dur_voz = float(duraciones[id_escena]["duracion_real_seg"])
        duracion_escena = pausa_antes + dur_voz + pausa_despues

        ruta_clip = ruta_segura_proyecto(ruta_proyecto, escena["clip"])
        info_clip = obtener_info_media(ruta_clip)
        duracion_disponible = float(info_clip.get("duracion", 0))
        if estricta:
            # La duración del contenedor es la de su pista más larga: un clip con el vídeo corto y
            # el audio largo la "cumpliría" y se congelaría. Aquí cuenta solo la imagen.
            if "duracion_video" not in info_clip:
                raise ValueError(
                    f"Modo duración estricta: el clip de la escena '{id_escena}' no tiene pista de vídeo "
                    f"legible ({info_clip.get('error', 'sin pista de vídeo')})."
                )
            duracion_disponible = float(info_clip["duracion_video"])

        inicio_clip = float(escena.get("clip_inicio_seg", 0))
        fin_clip = escena.get("clip_fin_seg")
        if fin_clip is None or fin_clip > duracion_disponible:
            fin_clip = duracion_disponible

        dur_segmento_clip = max(0.0, fin_clip - inicio_clip)
        if estricta:
            # Límites sobre una rejilla de fotogramas acumulada: el redondeo de cada escena no se
            # suma al de las anteriores y el total queda a menos de medio fotograma del audio.
            fotogramas = _fotograma(cursor_seg + duracion_escena, fps) - _fotograma(cursor_seg, fps)
            if fotogramas < 1 or abs(dur_segmento_clip - fotogramas / fps) > 1.0 / fps + 1e-6:
                raise ValueError(
                    f"Modo duración estricta: la escena '{id_escena}' necesita {fotogramas / fps:.3f} s "
                    f"({fotogramas} fotogramas) y su clip dura {dur_segmento_clip:.3f} s "
                    f"(tolerancia ±1 fotograma a {fps} fps). "
                    "No se recorta ni se congela: vuelve a renderizar el clip a esa duración."
                )
        clip_recortado = dur_segmento_clip > duracion_escena
        clip_extendido = dur_segmento_clip < duracion_escena

        if clip_extendido and (duracion_escena - dur_segmento_clip) > 5.0:
            logger.warning(
                f"Clip '{id_escena}' necesita extensión de "
                f"{duracion_escena - dur_segmento_clip:.1f}s (>5s). "
                f"Puede verse congelado."
            )

        timeline["escenas"].append({
            "id": id_escena,
            "inicio_seg": round(cursor_seg, 3),
            "fin_seg": round(cursor_seg + duracion_escena, 3),
            "duracion_necesaria": round(duracion_escena, 3),
            "clip_usado": escena["clip"],
            "clip_recortado": clip_recortado,
            "clip_extendido": clip_extendido,
            "inicio_trim": round(inicio_clip, 3),
            "transicion_entrada": _normalizar_transicion(
                escena.get("transicion_entrada", "cut")
            ),
            "transicion_salida": _normalizar_transicion(
                escena.get("transicion_salida", "cut")
            )
        })
        if estricta:
            timeline["escenas"][-1]["fotogramas"] = fotogramas
        cursor_seg += duracion_escena

    timeline["duracion_total_seg"] = round(cursor_seg, 3)

    ruta_salida = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_TIMELINE)
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Timeline generado: {len(timeline['escenas'])} escenas, "
        f"{timeline['duracion_total_seg']:.2f}s totales."
    )
    return timeline


def _construir_filtro_video(escena: dict, resolucion: str, fps: int) -> str:
    """Construye filtros FFmpeg INTRA-clip (sin xfade)."""
    if not validar_resolucion(resolucion):
        raise ValueError(f"Resolucion invalida: {resolucion}")
    fps = normalizar_fps(fps)
    dur = escena["duracion_necesaria"]
    # Duración estricta: como mucho se repite 1 fotograma (la tolerancia), nunca una congelación.
    # Sin modo estricto se congela lo que falte, incluida la cola de un fundido cruzado (_duracion_procesada).
    relleno = 1.0 / fps if "fotogramas" in escena else max(0, dur) + FADE_TRANSICION_SEG
    fade_seg = FADE_TRANSICION_SEG
    trans_in = escena.get("transicion_entrada", "cut")
    trans_out = escena.get("transicion_salida", "cut")

    res_x_y = resolucion.replace('x', ':')
    filtros = [
        f"scale={res_x_y}:force_original_aspect_ratio=decrease",
        f"pad={res_x_y}:(ow-iw)/2:(oh-ih)/2:color=black",
        f"setsar=1",
        f"fps={fps}",
        f"tpad=stop_mode=clone:stop_duration={relleno}",
    ]

    # ── Entrada ──
    if trans_in == "fade_from_black":
        filtros.append(f"fade=t=in:st=0:d={fade_seg}")
    elif trans_in == "dip_to_black":
        fade_corto = min(fade_seg * 0.5, dur * 0.15)
        filtros.append(f"fade=t=in:st=0:d={fade_corto:.3f}")

    # ── Salida ──
    if trans_out == "fade_to_black":
        inicio_fade = max(0, dur - fade_seg)
        filtros.append(f"fade=t=out:st={inicio_fade:.3f}:d={fade_seg}")
    elif trans_out == "dip_to_black":
        fade_corto = min(fade_seg * 0.5, dur * 0.15)
        inicio_fade = max(0, dur - fade_corto)
        filtros.append(f"fade=t=out:st={inicio_fade:.3f}:d={fade_corto:.3f}")

    return ",".join(filtros)


def procesar_clips_individuales(
    ruta_proyecto: str, timeline: dict, resolucion: str, fps: int
) -> list:
    """Normaliza cada clip a un MP4 con resolución/FPS uniformes."""
    ruta_temp = os.path.join(ruta_proyecto, CARPETA_TEMP)
    os.makedirs(ruta_temp, exist_ok=True)
    archivos_procesados = []
    total = len(timeline["escenas"])

    for idx, escena in enumerate(timeline["escenas"]):
        id_escena = escena["id"]
        if not validar_id_escena(id_escena):
            raise ValueError(f"ID de escena inseguro: {id_escena}")
        ruta_origen = ruta_segura_proyecto(ruta_proyecto, escena["clip_usado"])
        ruta_destino = os.path.join(ruta_temp, f"{idx:03d}_{id_escena}.mp4")

        dur_necesaria = escena["duracion_necesaria"]
        inicio_trim = escena["inicio_trim"]
        vf_filters = _construir_filtro_video(escena, resolucion, fps)

        # Duración estricta: número exacto de fotogramas de la rejilla acumulada (ver calcular_timeline).
        if "fotogramas" in escena:
            limite = ["-frames:v", str(escena["fotogramas"])]
        else:
            limite = ["-t", str(_duracion_procesada(timeline["escenas"], idx, FADE_TRANSICION_SEG))]
        comando = [
            binario("ffmpeg"), "-y", "-v", "error",
            "-ss", str(inicio_trim),
            "-i", ruta_origen,
            *limite,
            "-vf", vf_filters,
            "-an",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-g", str(fps * 2),  # GOP fijo para que concat copy funcione bien
            ruta_destino
        ]

        logger.info(f"  [{idx + 1}/{total}] Procesando clip '{id_escena}'...")
        resultado = subprocess.run(comando, capture_output=True, text=True)
        if resultado.returncode != 0:
            logger.error(f"FFmpeg error en '{id_escena}': {resultado.stderr}")
            raise RuntimeError(f"FFmpeg falló procesando '{id_escena}'")
        if "fotogramas" in escena:
            # Red de seguridad: el segmento debe tener exactamente los fotogramas de su escena.
            obtenida = float(obtener_info_media(ruta_destino).get("duracion_video", 0))
            if abs(obtenida - escena["fotogramas"] / fps) > 0.5 / fps:
                raise ValueError(
                    f"Modo duración estricta: el segmento de la escena '{id_escena}' salió con "
                    f"{obtenida:.3f} s y necesita {escena['fotogramas'] / fps:.3f} s "
                    f"({escena['fotogramas']} fotogramas). No se congela para completarlo."
                )

        archivos_procesados.append(ruta_destino)

    logger.info(f"Todos los clips procesados ({total}/{total}).")
    return archivos_procesados


def _cruces(escenas: list) -> list:
    """Para cada frontera i → i+1: ¿se cruzan las dos escenas con xfade?"""
    return [
        escenas[i]["transicion_salida"] in TRANSICIONES_INTER
        or escenas[i + 1]["transicion_entrada"] in TRANSICIONES_INTER
        for i in range(len(escenas) - 1)
    ]


def _duracion_procesada(escenas: list, idx: int, fade: float) -> float:
    """Duración del clip procesado de la escena `idx`.

    Si sale con fundido cruzado, se alarga `fade` segundos: esa cola es la que se funde con el
    principio de la escena siguiente, que así empieza en su segundo exacto del timeline y el
    vídeo dura lo mismo que el audio (la suma de las escenas).
    """
    cruces = _cruces(escenas)
    extra = fade if idx < len(cruces) and cruces[idx] else 0.0
    return escenas[idx]["duracion_necesaria"] + extra


def _grafo_transiciones(escenas: list, fade: float) -> str:
    """filter_complex que encadena los clips: xfade donde hay fundido cruzado, concat donde no.

    Cada xfade empieza justo donde empieza la escena siguiente en el timeline (no `fade` antes):
    la escena que sale aporta su cola alargada (_duracion_procesada), así que nada se acorta.
    """
    if len(escenas) == 1:
        return "[0:v]copy[vout]"
    partes = []
    anterior = "[0:v]"
    inicio_siguiente = 0.0
    for i, cruza in enumerate(_cruces(escenas)):
        inicio_siguiente += escenas[i]["duracion_necesaria"]
        salida = f"[v{i}]" if i < len(escenas) - 2 else "[vout]"
        if cruza:
            partes.append(
                f"{anterior}[{i + 1}:v]xfade=transition=fade:"
                f"duration={fade}:offset={inicio_siguiente:.3f}{salida}"
            )
        else:
            partes.append(f"{anterior}[{i + 1}:v]concat=n=2:v=1:a=0{salida}")
        anterior = salida
    return ";".join(partes)


def _hay_crossfade_real(timeline: dict) -> bool:
    """¿Hay alguna transición que requiera xfade entre clips adyacentes?"""
    return any(_cruces(timeline["escenas"]))


def _ensamblar_concat_demuxer(
    ruta_proyecto: str, archivos_procesados: list
) -> str:
    """Concatenación rápida con demuxer (sin recodificar vídeo)."""
    ruta_temp = os.path.join(ruta_proyecto, CARPETA_TEMP)
    lista_concat = os.path.join(ruta_temp, "concat_list.txt")

    with open(lista_concat, 'w', encoding='utf-8') as f:
        for arch in archivos_procesados:
            f.write(f"file '{os.path.basename(arch)}'\n")

    # Absolutas: FFmpeg se ejecuta con cwd=ruta_temp y una ruta de proyecto relativa fallaría.
    ruta_audio = os.path.abspath(os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_AUDIO_MEZCLADO))
    ruta_video_final = os.path.abspath(os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_VIDEO_FINAL))

    comando = [
        binario("ffmpeg"), "-y", "-v", "error",
        "-f", "concat", "-safe", "0",
        # Por nombre, no por ruta: se ejecuta con cwd=ruta_temp. Algunos FFmpeg de Windows buscan
        # los clips de la lista en la carpeta del último '/' e ignoran '\' (con CARPETA_TEMP =
        # "output/temp_clips" los buscaban en output/), y tampoco aceptan 'C:/...' como absoluta.
        "-i", os.path.basename(lista_concat),
        "-i", ruta_audio,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        ruta_video_final
    ]

    logger.info("Concatenando clips (demuxer, sin re-encode)...")
    resultado = subprocess.run(comando, cwd=ruta_temp, capture_output=True, text=True)
    if resultado.returncode != 0:
        logger.error(f"FFmpeg concat: {resultado.stderr}")
        raise RuntimeError("FFmpeg falló en concatenación final")

    return ruta_video_final


def _ensamblar_xfade(
    ruta_proyecto: str, archivos_procesados: list, timeline: dict, fps: int
) -> str:
    """Concatena con xfade real entre clips marcados como crossfade.

    Construye un filter_complex donde cada par (i, i+1) se cruza con
    xfade si la transición de salida o entrada lo pide. Si no, usa concat.
    """
    ruta_audio = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_AUDIO_MEZCLADO)
    ruta_video_final = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_VIDEO_FINAL)

    inputs = []
    for arch in archivos_procesados:
        inputs.extend(["-i", arch])
    inputs.extend(["-i", ruta_audio])
    indice_audio = len(archivos_procesados)

    filter_complex = _grafo_transiciones(timeline["escenas"], FADE_TRANSICION_SEG)

    comando = [
        binario("ffmpeg"), "-y", "-v", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", f"{indice_audio}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        ruta_video_final
    ]

    logger.info(f"Concatenando con xfade real ({len(timeline['escenas'])} clips)...")
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        logger.error(f"FFmpeg xfade: {resultado.stderr}")
        raise RuntimeError("FFmpeg falló en concatenación con xfade")

    return ruta_video_final


def ensamblar_y_sincronizar(
    ruta_proyecto: str,
    archivos_procesados: list,
    timeline: dict,
    fps: int
) -> str:
    """Elige estrategia de concatenación según las transiciones del timeline."""
    if _hay_crossfade_real(timeline) and len(archivos_procesados) > 1:
        ruta = _ensamblar_xfade(ruta_proyecto, archivos_procesados, timeline, fps)
    else:
        ruta = _ensamblar_concat_demuxer(ruta_proyecto, archivos_procesados)

    info = obtener_info_media(ruta)
    if "error" in info:
        raise RuntimeError(f"Vídeo final inválido: {info['error']}")

    logger.info(
        f"Vídeo ensamblado: {info['duracion']:.2f}s, "
        f"{info['resolucion']}, {info['codec']}"
    )
    return ruta


def montar_video_proyecto(ruta_proyecto: str, datos_proyecto: dict) -> dict:
    """Orquestador interno del Módulo 3 — Montaje de Vídeo."""
    try:
        resolucion = datos_proyecto.get("resolucion", RESOLUCION_DEFAULT)
        if not validar_resolucion(resolucion):
            raise ValueError(f"Resolucion invalida: {resolucion}")
        fps = normalizar_fps(datos_proyecto.get("fps", FPS_DEFAULT))

        logger.info("Fase 3.1: Calculando timeline matemático...")
        timeline = calcular_timeline(ruta_proyecto, datos_proyecto)

        if not timeline["escenas"]:
            return {"exito": False, "error": "Timeline vacío. No hay escenas que montar."}

        logger.info(
            f"Fase 3.2: Procesando clips (Res: {resolucion}, FPS: {fps})..."
        )
        archivos = procesar_clips_individuales(
            ruta_proyecto, timeline, resolucion, fps
        )

        logger.info("Fase 3.3: Ensamblaje final y sincronización de audio...")
        ruta_final = ensamblar_y_sincronizar(
            ruta_proyecto, archivos, timeline, fps
        )

        return {"exito": True, "archivo": ruta_final, "timeline": timeline}

    except Exception as e:
        logger.error(f"Error en Módulo de Montaje: {e}")
        return {"exito": False, "error": str(e)}

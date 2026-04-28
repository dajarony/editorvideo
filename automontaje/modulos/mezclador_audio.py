# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.0
═══════════════════════════════════════════════════════════
Archivo: modulos/mezclador_audio.py
Tipo: Lógica → Ensamblador de Audio (Módulo 2)
Dependencias: 5 (os, json, math, pydub, configuracion)

Entradas:
- Ruta del proyecto y datos validados del JSON.
- narracion_duraciones.json generado por Módulo 1.
- Archivos MP3 de narración por escena.

Acciones:
1. Construye pista de voz completa con silencios dinámicos.
2. Carga y ajusta la música de fondo (loop/recorte + fades).
3. Aplica ducking suavizado: baja la música donde hay voz
   con transiciones graduales de ~200ms.
4. Mezcla ambas pistas en overlay.

Salidas:
- output/audio_mezclado.wav (formato WAV sin pérdida — Ajuste 2).
═══════════════════════════════════════════════════════════
"""

import os
import json
import math
from pydub import AudioSegment
from configuracion import (
    CARPETA_OUTPUT,
    ARCHIVO_DURACIONES,
    ARCHIVO_AUDIO_MEZCLADO,
    FADE_DUCK_MS
)
from .utilidades import logger


def lineal_a_db(volumen_lineal: float) -> float:
    """Convierte un volumen lineal (0.0 a 1.0) a decibelios para PyDub.

    Args:
        volumen_lineal: Valor entre 0.0 (silencio) y 1.0 (máximo).

    Returns:
        Valor en decibelios. Mínimo -120 dB (silencio práctico).
    """
    if volumen_lineal <= 0.001:
        return -120.0
    return 20 * math.log10(volumen_lineal)


def mezclar_audio_proyecto(ruta_proyecto: str, datos_proyecto: dict) -> dict:
    """Ensambla la mezcla final de narración y música con ducking.

    Construye la pista de voz completa concatenando los MP3 de narración
    con los silencios definidos (pausa_antes + pausa_despues). Luego
    mezcla con la música de fondo aplicando ducking suavizado.

    El ducking usa transiciones de FADE_DUCK_MS milisegundos en los
    bordes de cada segmento de voz para evitar cortes bruscos de volumen.

    Args:
        ruta_proyecto: Ruta base del proyecto.
        datos_proyecto: Diccionario del JSON del proyecto validado.

    Returns:
        dict con exito (bool), archivo (str) y duracion_ms (int).
    """
    try:
        # ─── Cargar Duraciones ──────────────────────────
        ruta_duraciones = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_DURACIONES)
        if not os.path.exists(ruta_duraciones):
            return {
                "exito": False,
                "error": "Falta narracion_duraciones.json. Ejecuta la Fase 1 primero."
            }

        with open(ruta_duraciones, 'r', encoding='utf-8') as f:
            duraciones = json.load(f)

        if not duraciones:
            return {
                "exito": False,
                "error": "narracion_duraciones.json está vacío. No hay nada que mezclar."
            }

        # ─── Construir Pista de Voz ─────────────────────
        pista_voz = AudioSegment.silent(duration=0)
        segmentos_ducking = []  # Tuplas (inicio_ms, fin_ms) donde hay voz activa
        cursor_ms = 0

        escenas = datos_proyecto.get("escenas", [])
        total = len(escenas)
        logger.info(f"Construyendo pista de voz ({total} escenas con silencios dinámicos)...")

        for idx, escena in enumerate(escenas, 1):
            id_escena = escena["id"]
            if id_escena not in duraciones:
                logger.warning(f"Escena '{id_escena}' no tiene audio generado. Saltando.")
                continue

            pausa_antes_ms = int(escena.get("pausa_antes_seg", 0) * 1000)
            pausa_despues_ms = int(escena.get("pausa_despues_seg", 0) * 1000)

            ruta_audio_voz = os.path.join(ruta_proyecto, duraciones[id_escena]["archivo"])
            audio_escena = AudioSegment.from_file(ruta_audio_voz)
            duracion_real_ms = len(audio_escena)

            # 1. Silencio previo
            pista_voz += AudioSegment.silent(duration=pausa_antes_ms)
            cursor_ms += pausa_antes_ms

            # 2. Registrar segmento de ducking (voz activa)
            segmentos_ducking.append((cursor_ms, cursor_ms + duracion_real_ms))

            # 3. Audio de la voz
            pista_voz += audio_escena
            cursor_ms += duracion_real_ms

            # 4. Silencio posterior
            pista_voz += AudioSegment.silent(duration=pausa_despues_ms)
            cursor_ms += pausa_despues_ms

            logger.info(f"  [{idx}/{total}] '{id_escena}' — {duracion_real_ms / 1000:.2f}s de voz")

        if len(pista_voz) == 0:
            return {
                "exito": False,
                "error": "Pista de voz vacía. ¿Las narraciones se generaron?"
            }

        logger.info(f"Pista de voz ensamblada: {len(pista_voz) / 1000:.2f}s totales.")

        # ─── Procesar Música de Fondo ───────────────────
        datos_musica = datos_proyecto.get("musica", {})
        tiene_musica = (
            datos_musica
            and datos_musica.get("fuente") == "archivo"
        )

        if tiene_musica:
            ruta_musica = os.path.join(
                ruta_proyecto, datos_musica.get("archivo", "")
            )

            if not os.path.exists(ruta_musica):
                logger.warning(
                    "Archivo de música no encontrado. Exportando solo narración."
                )
                pista_final = pista_voz
            else:
                logger.info("Procesando pista de música (loop, fades, ducking)...")
                musica = AudioSegment.from_file(ruta_musica)

                if len(musica) == 0:
                    logger.warning(
                        "Archivo de música cargado pero con duración 0. "
                        "Exportando solo narración."
                    )
                    pista_final = pista_voz
                    ruta_salida = os.path.join(
                        ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_AUDIO_MEZCLADO
                    )
                    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
                    pista_final.export(ruta_salida, format="wav")
                    return {
                        "exito": True,
                        "archivo": ruta_salida,
                        "duracion_ms": len(pista_final)
                    }

                # Loop si la música es más corta que la narración
                if len(musica) < len(pista_voz):
                    repeticiones = (len(pista_voz) // len(musica)) + 1
                    musica = musica * repeticiones
                    logger.info(
                        f"  Música en loop ({repeticiones}x) para cubrir "
                        f"{len(pista_voz) / 1000:.1f}s de narración."
                    )

                # Recortar a la longitud exacta de la narración
                musica = musica[:len(pista_voz)]

                # Fades globales
                fade_in_ms = int(datos_musica.get("fade_in_segundos", 2.0) * 1000)
                fade_out_ms = int(datos_musica.get("fade_out_segundos", 2.0) * 1000)
                musica = musica.fade_in(fade_in_ms).fade_out(fade_out_ms)

                # ── Ducking Suavizado ───────────────────
                vol_base_db = lineal_a_db(datos_musica.get("volumen_base", 0.30))
                vol_duck_db = lineal_a_db(datos_musica.get("volumen_durante_voz", 0.08))
                fade_ms = FADE_DUCK_MS

                logger.info(
                    f"  Ducking: base={vol_base_db:.1f}dB, "
                    f"voz={vol_duck_db:.1f}dB, fade={fade_ms}ms"
                )

                # Precalcular márgenes de ducking extendidos
                # La música empieza a bajar un poco ANTES de que hable
                # y sube un poco DESPUÉS de que termina.
                segmentos_extendidos = []
                for inicio_voz, fin_voz in segmentos_ducking:
                    inicio_duck = max(0, inicio_voz - fade_ms)
                    fin_duck = min(len(musica), fin_voz + fade_ms)
                    segmentos_extendidos.append((inicio_duck, fin_duck))

                # Fusionar segmentos solapados
                segmentos_fusionados = []
                for seg in sorted(segmentos_extendidos):
                    if segmentos_fusionados and seg[0] <= segmentos_fusionados[-1][1]:
                        segmentos_fusionados[-1] = (
                            segmentos_fusionados[-1][0],
                            max(segmentos_fusionados[-1][1], seg[1])
                        )
                    else:
                        segmentos_fusionados.append(seg)

                # Construir música duckeada por segmentos
                musica_duckeada = AudioSegment.silent(duration=0)
                puntero = 0

                for inicio_duck, fin_duck in segmentos_fusionados:
                    # Segmento a volumen base (sin voz)
                    if inicio_duck > puntero:
                        chunk_base = musica[puntero:inicio_duck] + vol_base_db
                        musica_duckeada += chunk_base

                    # Segmento duckeado (con voz)
                    chunk_duck = musica[inicio_duck:fin_duck] + vol_duck_db

                    # Suavizar bordes con fade in/out
                    duracion_chunk = len(chunk_duck)
                    fade_aplicable = min(fade_ms, duracion_chunk // 3)
                    if fade_aplicable > 50:
                        chunk_duck = chunk_duck.fade_in(fade_aplicable).fade_out(fade_aplicable)

                    musica_duckeada += chunk_duck
                    puntero = fin_duck

                # Segmento final a volumen base
                if puntero < len(musica):
                    chunk_final = musica[puntero:] + vol_base_db
                    musica_duckeada += chunk_final

                # Mezclar ambas pistas (overlay)
                pista_final = musica_duckeada.overlay(pista_voz)
                logger.info("  Mezcla voz + música completada.")
        else:
            logger.info("Proyecto sin música. Exportando solo narración.")
            pista_final = pista_voz

        # ─── Exportación WAV (Ajuste 2) ─────────────────
        ruta_salida = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_AUDIO_MEZCLADO)
        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
        pista_final.export(ruta_salida, format="wav")

        duracion_total = len(pista_final) / 1000.0
        logger.info(f"Audio maestro exportado: {duracion_total:.2f}s → {ruta_salida}")

        return {
            "exito": True,
            "archivo": ruta_salida,
            "duracion_ms": len(pista_final)
        }

    except Exception as e:
        logger.error(f"Error crítico en ensamblaje de audio: {e}")
        return {"exito": False, "error": str(e)}

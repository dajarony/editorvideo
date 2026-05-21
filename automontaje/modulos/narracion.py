# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.1
═══════════════════════════════════════════════════════════
Archivo: modulos/narracion.py
Tipo: Lógica → Generador de Voz (Módulo 1)
Dependencias: edge_tts, asyncio, json, os, sys

Entradas:
- Ruta del proyecto y datos validados del JSON.

Acciones:
- Genera un MP3 por escena usando la API Python de Edge TTS.
- Caché por hash (texto + voz + velocidad) — evita regenerar audios idénticos.
- Verifica integridad post-creación (duración real con ffprobe).
- Reintenta hasta REINTENTOS_MAXIMOS_TTS con backoff si falla.

Salidas:
- Archivos MP3 en output/narracion/
- output/narracion_duraciones.json
- output/narracion_cache.json (hash → archivo, para reusos futuros)
═══════════════════════════════════════════════════════════
"""

import os
import json
import asyncio
import sys
import edge_tts

# Fix para Windows: aiodns requiere SelectorEventLoop
if sys.platform == "win32":
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .utilidades import (
    obtener_info_media, logger, hash_tts, validar_id_escena,
    validar_velocidad_tts, ruta_segura_proyecto
)
from configuracion import (
    DURACION_MINIMA_AUDIO_SEG,
    REINTENTOS_MAXIMOS_TTS,
    RETARDO_REINTENTO_TTS_SEG,
    USAR_CACHE_TTS,
    CARPETA_NARRACION,
    CARPETA_OUTPUT,
    ARCHIVO_DURACIONES,
    ARCHIVO_CACHE_TTS
)


MAX_CONCURRENCIA_TTS = 4


def _cargar_cache(ruta_cache: str) -> dict:
    """Carga el archivo de caché TTS si existe."""
    if not USAR_CACHE_TTS or not os.path.exists(ruta_cache):
        return {}
    try:
        with open(ruta_cache, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Caché TTS corrupta. Ignorada.")
        return {}


def _guardar_cache(ruta_cache: str, cache: dict):
    """Persiste el archivo de caché TTS."""
    if not USAR_CACHE_TTS:
        return
    os.makedirs(os.path.dirname(ruta_cache), exist_ok=True)
    with open(ruta_cache, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


async def generar_audio_escena(
    id_escena: str,
    texto: str,
    voz: str,
    velocidad: str,
    ruta_salida: str
) -> dict:
    """Genera un MP3 de narración con verificación + reintentos.

    Args:
        id_escena: Identificador único de la escena.
        texto: Texto que el narrador debe decir.
        voz: Nombre de la voz de Edge TTS (ej. 'es-ES-AlvaroNeural').
        velocidad: Ajuste de velocidad ('+0%', '-5%', etc.).
        ruta_salida: Ruta absoluta donde guardar el MP3.

    Returns:
        dict con id, archivo, duracion_real_seg y exito (bool).
    """
    if not validar_id_escena(id_escena):
        return {
            "id": id_escena,
            "exito": False,
            "error": "ID de escena inseguro."
        }
    if not validar_velocidad_tts(velocidad):
        return {
            "id": id_escena,
            "exito": False,
            "error": "Velocidad TTS invalida."
        }

    ultimo_error = "desconocido"

    for intento in range(REINTENTOS_MAXIMOS_TTS + 1):
        try:
            comunicador = edge_tts.Communicate(
                text=texto, voice=voz, rate=velocidad
            )
            await comunicador.save(ruta_salida)

            if not os.path.exists(ruta_salida):
                ultimo_error = "archivo no se creó"
                logger.warning(
                    f"[Intento {intento + 1}] Archivo no generado para '{id_escena}'."
                )
            else:
                info = obtener_info_media(ruta_salida)
                if "error" in info:
                    ultimo_error = info["error"]
                    logger.warning(
                        f"[Intento {intento + 1}] '{id_escena}': {info['error']}"
                    )
                else:
                    duracion = info.get("duracion", 0.0)
                    if duracion < DURACION_MINIMA_AUDIO_SEG:
                        ultimo_error = f"audio demasiado corto ({duracion:.2f}s)"
                        logger.warning(
                            f"[Intento {intento + 1}] '{id_escena}' muy corto "
                            f"({duracion:.2f}s)."
                        )
                        if os.path.exists(ruta_salida):
                            os.remove(ruta_salida)
                    else:
                        logger.info(
                            f"  ✓ Narración '{id_escena}' generada ({duracion:.2f}s)"
                        )
                        return {
                            "id": id_escena,
                            "archivo": ruta_salida,
                            "duracion_real_seg": duracion,
                            "exito": True
                        }
        except Exception as e:
            ultimo_error = str(e)
            logger.error(
                f"[Intento {intento + 1}] Excepción en TTS '{id_escena}': {e}"
            )

        # Backoff antes del siguiente intento (excepto en el último)
        if intento < REINTENTOS_MAXIMOS_TTS:
            await asyncio.sleep(RETARDO_REINTENTO_TTS_SEG * (intento + 1))

    logger.error(
        f"  ✗ Narración '{id_escena}' falló tras "
        f"{REINTENTOS_MAXIMOS_TTS + 1} intentos: {ultimo_error}"
    )
    return {
        "id": id_escena,
        "exito": False,
        "error": f"Falló tras {REINTENTOS_MAXIMOS_TTS + 1} intentos: {ultimo_error}"
    }


async def ejecutar_narracion_concurrente(
    ruta_proyecto: str,
    datos_proyecto: dict
) -> dict:
    """Genera todas las narraciones del proyecto de forma concurrente, con caché.

    Reutiliza MP3s ya generados si el hash (texto+voz+velocidad) coincide.

    Args:
        ruta_proyecto: Ruta base del proyecto.
        datos_proyecto: Diccionario del JSON validado.

    Returns:
        dict con exito (bool), errores (list) y duraciones (dict).
    """
    ruta_output_narracion = os.path.join(ruta_proyecto, CARPETA_NARRACION)
    os.makedirs(ruta_output_narracion, exist_ok=True)

    ruta_cache = os.path.join(ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_CACHE_TTS)
    cache = _cargar_cache(ruta_cache)

    narrador = datos_proyecto.get("narrador", {})
    voz = narrador.get("voz", "es-ES-AlvaroNeural")
    velocidad = narrador.get("velocidad", "+0%")

    escenas = datos_proyecto.get("escenas", [])
    total = len(escenas)
    logger.info(
        f"Generando {total} narraciones — voz='{voz}' rate='{velocidad}' "
        f"cache={'on' if USAR_CACHE_TTS else 'off'}..."
    )

    duraciones_json = {}
    errores = []
    tareas = []
    indices = []  # Para mapear cada tarea a su escena
    nuevo_cache = dict(cache)
    semaforo = asyncio.Semaphore(MAX_CONCURRENCIA_TTS)

    async def _generar_limitado(*args):
        async with semaforo:
            return await generar_audio_escena(*args)

    for escena in escenas:
        id_escena = escena["id"]
        if not validar_id_escena(id_escena):
            errores.append({"id": id_escena, "error": "ID de escena inseguro."})
            continue
        texto = escena["texto_narracion"]
        ruta_mp3 = os.path.join(ruta_output_narracion, f"{id_escena}.mp3")

        firma = hash_tts(texto, voz, velocidad)
        entrada = cache.get(firma)

        # ── Cache hit ──
        if entrada:
            try:
                ruta_cache_mp3 = ruta_segura_proyecto(ruta_proyecto, entrada["archivo"])
            except (KeyError, ValueError):
                ruta_cache_mp3 = None
            if ruta_cache_mp3 and os.path.exists(ruta_cache_mp3):
                # Si el archivo cacheado no es el destino esperado, copiar
                if os.path.abspath(ruta_cache_mp3) != os.path.abspath(ruta_mp3):
                    import shutil
                    shutil.copy2(ruta_cache_mp3, ruta_mp3)
                duraciones_json[id_escena] = {
                    "archivo": os.path.relpath(ruta_mp3, ruta_proyecto).replace("\\", "/"),
                    "duracion_real_seg": entrada["duracion_real_seg"]
                }
                logger.info(
                    f"  ⟲ Cache hit '{id_escena}' "
                    f"({entrada['duracion_real_seg']:.2f}s)"
                )
                continue

        # ── Cache miss → generar ──
        tareas.append(
            _generar_limitado(id_escena, texto, voz, velocidad, ruta_mp3)
        )
        indices.append((id_escena, firma))

    # ── Ejecutar lo no-cacheado ──
    if tareas:
        resultados = await asyncio.gather(*tareas)
        for res, (id_escena, firma) in zip(resultados, indices):
            if res["exito"]:
                path_relativo = os.path.relpath(
                    res["archivo"], ruta_proyecto
                ).replace("\\", "/")
                duraciones_json[id_escena] = {
                    "archivo": path_relativo,
                    "duracion_real_seg": res["duracion_real_seg"]
                }
                nuevo_cache[firma] = {
                    "archivo": path_relativo,
                    "duracion_real_seg": res["duracion_real_seg"]
                }
            else:
                errores.append(res)

    # ── Guardar JSON de duraciones ──
    if duraciones_json:
        ruta_json_salida = os.path.join(
            ruta_proyecto, CARPETA_OUTPUT, ARCHIVO_DURACIONES
        )
        os.makedirs(os.path.dirname(ruta_json_salida), exist_ok=True)
        with open(ruta_json_salida, 'w', encoding='utf-8') as f:
            json.dump(duraciones_json, f, indent=2, ensure_ascii=False)
        logger.info(f"Duraciones guardadas en {ARCHIVO_DURACIONES}")

    # ── Persistir caché ──
    _guardar_cache(ruta_cache, nuevo_cache)

    exito = len(errores) == 0
    if exito:
        logger.info(
            f"Todas las narraciones disponibles ({total}/{total}) — "
            f"{len(tareas)} generadas, {total - len(tareas)} de caché."
        )
    else:
        logger.error(f"{len(errores)}/{total} narraciones fallaron.")

    return {"exito": exito, "errores": errores, "duraciones": duraciones_json}

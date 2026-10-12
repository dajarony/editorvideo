# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.1
═══════════════════════════════════════════════════════════
Archivo: main.py
Tipo: Orquestador Principal

Propósito:
- Punto de entrada único del sistema AEGS.
- Ejecuta el pipeline completo de automontaje:
  Validar → Narrar → Mezclar → Montar → Subtitular.
- CLI con argparse y flags útiles (--skip-tts, --skip-subs, etc.).

Uso:
    python main.py /ruta/a/mi_proyecto/
    python main.py /ruta/a/proyecto/ --skip-subs --keep-temp
═══════════════════════════════════════════════════════════
"""

import sys
import os
import time
import asyncio
import shutil
import argparse

from modulos.utilidades import (
    logger, activar_log_archivo, limpiar_carpeta_temporal, verificar_ffmpeg
)
from modulos.validador import inicializar_validador
from modulos.narracion import ejecutar_narracion_concurrente
from modulos.mezclador_audio import mezclar_audio_proyecto
from modulos.montador_video import montar_video_proyecto
from modulos.subtitulos import procesar_subtitulos
from configuracion import (
    CARPETA_LOGS, ARCHIVO_LOG, CARPETA_NARRACION, CARPETA_TEMP, CARPETA_OUTPUT,
    ARCHIVO_VIDEO_FINAL, ARCHIVO_VIDEO_SUB, MOTOR_NARRACION_DEFAULT
)


def parse_args(argv=None):
    """Define la CLI del sistema AEGS."""
    parser = argparse.ArgumentParser(
        prog="aegs",
        description=(
            "AEGS — Sistema de Automontaje de Vídeo. "
            "Convierte un proyecto.json en un vídeo final con narración, "
            "música y subtítulos."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python main.py ./mi_video/\n"
            "  python main.py ./mi_video/ --skip-subs\n"
            "  python main.py ./mi_video/ --no-cache --keep-temp\n"
        )
    )
    parser.add_argument(
        "ruta_proyecto",
        help="Ruta a la carpeta que contiene proyecto.json"
    )
    parser.add_argument(
        "--skip-subs", action="store_true",
        help="Omite la fase de subtítulos aunque el JSON los pida."
    )
    parser.add_argument(
        "--skip-tts", action="store_true",
        help="No regenera narraciones; usa solo lo que ya hay en disco."
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Ignora la caché TTS y fuerza regenerar todas las voces."
    )
    parser.add_argument(
        "--keep-temp", action="store_true",
        help="Conserva la carpeta de clips temporales tras renderizar."
    )
    parser.add_argument(
        "--srt-sidecar", action="store_true",
        help="Genera SRT pero NO lo quema en el vídeo (modo sidecar)."
    )
    parser.add_argument(
        "--solo-narracion", action="store_true",
        help=(
            "Valida y genera la narración (narracion_duraciones.json) y se detiene, sin montar "
            "vídeo. Los clips aún pueden no existir."
        ),
    )
    parser.add_argument(
        "--duracion-estricta", action="store_true",
        help=(
            "Cada clip debe durar lo que su escena (±1 fotograma): si no, falla en vez de "
            "recortarlo o congelarlo. Solo admite transiciones 'cut'."
        ),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Logging detallado en consola."
    )
    args = parser.parse_args(argv)
    if args.solo_narracion and args.skip_tts:
        parser.error("--solo-narracion genera la narración: no se puede combinar con --skip-tts.")
    return args


def mostrar_resumen(ruta_video, timeline, warnings, tiempo_total, srt=None):
    """Resumen final por consola."""
    num_escenas = len(timeline.get("escenas", []))
    duracion = timeline.get("duracion_total_seg", 0)

    logger.info("╔═══════════════════════════════════════════════════════╗")
    logger.info("║           PROYECTO RENDERIZADO CON ÉXITO             ║")
    logger.info("╠═══════════════════════════════════════════════════════╣")
    logger.info(f"║  Escenas procesadas : {num_escenas}")
    logger.info(f"║  Duración del vídeo : {duracion:.2f} segundos")
    logger.info(f"║  Warnings           : {len(warnings)}")
    logger.info(f"║  Tiempo de proceso  : {tiempo_total:.1f} segundos")
    if ruta_video:
        logger.info(f"║  Vídeo final        : {ruta_video}")
    if srt:
        logger.info(f"║  Subtítulos (SRT)   : {srt}")
    logger.info("╚═══════════════════════════════════════════════════════╝")


def aplicar_overrides_cli(datos: dict, args) -> dict:
    """Modifica el dict de proyecto según los flags de CLI."""
    if args.skip_subs:
        datos.setdefault("subtitulos", {})["generar"] = False
    if args.srt_sidecar:
        datos.setdefault("subtitulos", {})["sidecar"] = True
    if args.duracion_estricta:
        datos.setdefault("montaje", {})["duracion_estricta"] = True
    return datos


async def orquestador(ruta_proyecto: str, args):
    """Pipeline completo de automontaje."""
    inicio = time.time()

    logger.info("╔═══════════════════════════════════════════════════════╗")
    logger.info("║     AEGS — SISTEMA DE AUTOMONTAJE DE VÍDEO          ║")
    logger.info(f"║  Proyecto: {os.path.basename(ruta_proyecto):<42}║")
    logger.info("╚═══════════════════════════════════════════════════════╝")

    # ═══ PRECHEQUEO: FFmpeg ═════════════════════════════
    chk = verificar_ffmpeg()
    if not chk["exito"]:
        for err in chk["errores"]:
            logger.error(f"  ✗ {err}")
        sys.exit(2)
    logger.info(f"  ✓ FFmpeg detectado: {chk['versiones'].get('ffmpeg', '')[:60]}")

    # ═══ FASE 0: VALIDACIÓN ═════════════════════════════
    logger.info("")
    logger.info("━━━ FASE 0: Verificando integridad del proyecto ━━━")
    res_val = inicializar_validador(
        ruta_proyecto,
        requiere_clips=not args.solo_narracion,
        duracion_estricta=args.duracion_estricta,
    )

    warnings_proyecto = res_val.get("warnings", [])
    for warn in warnings_proyecto:
        logger.warning(f"  ⚠ {warn}")

    montaje = res_val.get("datos", {}).get("montaje")
    if args.duracion_estricta or (isinstance(montaje, dict) and montaje.get("duracion_estricta") is True):
        # Si esta ejecución falla en cualquier fase, no debe quedar a la vista el vídeo de una anterior.
        for nombre in (ARCHIVO_VIDEO_FINAL, ARCHIVO_VIDEO_SUB):
            ruta_previa = os.path.join(ruta_proyecto, CARPETA_OUTPUT, nombre)
            if os.path.isfile(ruta_previa):
                os.remove(ruta_previa)
                logger.info(f"  Duración estricta: eliminado {nombre} de una ejecución anterior.")

    if not res_val.get("exito"):
        logger.error("FALLO EN FASE 0 — VALIDACIÓN. ABORTANDO.")
        for err in res_val.get("errores", []):
            logger.error(f"  ✗ {err}")
        sys.exit(1)

    datos = aplicar_overrides_cli(res_val["datos"], args)
    logger.info("  ✓ Proyecto validado correctamente.")

    # ═══ FASE 1: NARRACIÓN TTS ══════════════════════════
    logger.info("")
    motor = datos.get("narrador", {}).get("motor", MOTOR_NARRACION_DEFAULT)
    logger.info(f"━━━ FASE 1: Generando narración ({motor}) ━━━")

    if args.skip_tts:
        logger.info("  ⏭ --skip-tts: usando narraciones existentes.")
    else:
        if args.no_cache:
            # Borra cache y narraciones previas para regenerar todo
            ruta_narracion = os.path.join(ruta_proyecto, CARPETA_NARRACION)
            if os.path.isdir(ruta_narracion):
                shutil.rmtree(ruta_narracion)
                logger.info("  Narración previa eliminada (--no-cache).")
            ruta_cache = os.path.join(ruta_proyecto, "output", "narracion_cache.json")
            if os.path.isfile(ruta_cache):
                os.remove(ruta_cache)

        res_nar = await ejecutar_narracion_concurrente(ruta_proyecto, datos)
        if not res_nar["exito"]:
            logger.error("FALLO EN FASE 1 — NARRACIÓN. ABORTANDO.")
            for err in res_nar.get("errores", []):
                logger.error(f"  ✗ {err}")
            sys.exit(1)

    if args.solo_narracion:
        logger.info("")
        logger.info("  --solo-narracion: duraciones en output/narracion_duraciones.json. Sin montaje.")
        return

    # ═══ FASE 2: MEZCLA DE AUDIO ════════════════════════
    logger.info("")
    logger.info("━━━ FASE 2: Ensamblando audio maestro con ducking ━━━")
    res_mix = mezclar_audio_proyecto(ruta_proyecto, datos)
    if not res_mix["exito"]:
        logger.error(f"FALLO EN FASE 2 — AUDIO: {res_mix.get('error')}")
        sys.exit(1)

    # ═══ FASE 3: MONTAJE DE VÍDEO ═══════════════════════
    logger.info("")
    logger.info("━━━ FASE 3: Montando vídeo con transiciones ━━━")
    res_vid = montar_video_proyecto(ruta_proyecto, datos)
    if not res_vid["exito"]:
        logger.error(f"FALLO EN FASE 3 — VÍDEO: {res_vid.get('error')}")
        sys.exit(1)

    video_generado = res_vid.get("archivo")
    timeline = res_vid.get("timeline", {})

    # ═══ FASE 4: SUBTÍTULOS (OPCIONAL) ══════════════════
    logger.info("")
    logger.info("━━━ FASE 4: Postproducción y subtítulos ━━━")
    res_sub = procesar_subtitulos(ruta_proyecto, datos)

    if not res_sub["exito"]:
        logger.error(f"FALLO EN FASE 4 — SUBTÍTULOS: {res_sub.get('error')}")
        sys.exit(1)

    srt_path = res_sub.get("srt")
    if not res_sub.get("omitido") and res_sub.get("archivo"):
        video_generado = res_sub["archivo"]

    # ═══ LIMPIEZA Y CIERRE ══════════════════════════════
    logger.info("")
    if not args.keep_temp:
        limpiar_carpeta_temporal(ruta_proyecto, CARPETA_TEMP)
    else:
        logger.info("  --keep-temp: conservando clips temporales.")

    mostrar_resumen(
        video_generado, timeline, warnings_proyecto,
        time.time() - inicio, srt_path
    )


def main_cli(argv=None):
    """Punto de entrada instalable para el comando `aegs`."""
    args = parse_args(argv)
    ruta_input = os.path.abspath(args.ruta_proyecto)
    if not os.path.isdir(ruta_input):
        logger.error(f"El directorio especificado no existe: {ruta_input}")
        return 1

    if args.verbose:
        import logging
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler):
                h.setLevel(logging.DEBUG)

    activar_log_archivo(ruta_input, CARPETA_LOGS, ARCHIVO_LOG)

    try:
        asyncio.run(orquestador(ruta_input, args))
    except KeyboardInterrupt:
        logger.warning("\nProceso abortado por el usuario (Ctrl+C).")
        return 130
    except SystemExit:
        raise
    except Exception as e:
        logger.critical(f"Error fatal no capturado: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())

# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.0
═══════════════════════════════════════════════════════════
Archivo: modulos/validador.py
Tipo: Entrada → Validador (Módulo 0)
Dependencias: 4 (os, json, utilidades, configuracion)

Entradas:
- Ruta base del proyecto (carpeta con proyecto.json y clips/).

Acciones:
- Parsear y validar proyecto.json.
- Verificar integridad estructural (campos, IDs, lógica de tiempos).
- Verificar integridad física (clips existen y son vídeo válido).

Salidas:
- dict: { exito: bool, errores: list, warnings: list,
          datos: dict, metadatos_clips: dict }
═══════════════════════════════════════════════════════════
"""

import os
import json
from .utilidades import obtener_info_media, logger
from configuracion import ARCHIVO_PROYECTO, VOCES_EDGE_CONOCIDAS


def inicializar_validador(ruta_proyecto: str) -> dict:
    """Valida la integridad total de un proyecto antes de procesarlo.

    Ejecuta validaciones obligatorias (bloquean el proceso si fallan)
    y validaciones de warning (avisan pero permiten continuar).

    Args:
        ruta_proyecto: Ruta absoluta a la carpeta del proyecto.

    Returns:
        dict con exito (bool), errores (list), warnings (list),
        datos (dict del JSON), y metadatos_clips (dict con info ffprobe).
    """
    errores = []
    warnings = []
    metadatos_clips = {}

    ruta_json = os.path.join(ruta_proyecto, ARCHIVO_PROYECTO)

    # ─── Existencia del JSON ────────────────────────────
    if not os.path.exists(ruta_json):
        return {
            "exito": False,
            "errores": [f"No se encontró {ARCHIVO_PROYECTO} en {ruta_proyecto}"],
            "warnings": [],
            "datos": {},
            "metadatos_clips": {}
        }

    # ─── Parseo del JSON ────────────────────────────────
    try:
        with open(ruta_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "exito": False,
            "errores": [f"JSON inválido (error de sintaxis): {str(e)}"],
            "warnings": [],
            "datos": {},
            "metadatos_clips": {}
        }

    # ─── Campos Obligatorios ────────────────────────────
    campos_requeridos = ["titulo", "idioma", "narrador", "escenas"]
    for campo in campos_requeridos:
        if campo not in datos:
            errores.append(f"Falta campo obligatorio: '{campo}'")

    # ─── Validación del Narrador ────────────────────────
    if "narrador" in datos:
        narrador = datos["narrador"]
        if not isinstance(narrador, dict):
            errores.append(
                f"El campo 'narrador' debe ser un objeto JSON, no {type(narrador).__name__}."
            )
        else:
            voz = narrador.get("voz", "")
            if not voz:
                errores.append("El narrador no tiene 'voz' definida.")
            elif voz not in VOCES_EDGE_CONOCIDAS:
                warnings.append(
                    f"Voz '{voz}' no está en la lista conocida. "
                    f"Podría funcionar si es válida en Edge TTS, pero no ha sido verificada."
                )

            if "velocidad" not in narrador:
                warnings.append("No se definió 'velocidad' para el narrador. Se usará +0%.")

    # ─── Validación de Escenas ──────────────────────────
    escenas = datos.get("escenas", [])
    if not isinstance(escenas, list):
        errores.append(
            f"El campo 'escenas' debe ser una lista, no {type(escenas).__name__}."
        )
        escenas = []
    if not escenas:
        errores.append("El proyecto no tiene escenas definidas.")

    ids_escenas = set()
    for indice, escena in enumerate(escenas):
        id_escena = escena.get("id", f"escena_sin_id_{indice}")

        # IDs duplicados
        if id_escena in ids_escenas:
            errores.append(f"ID de escena duplicado: '{id_escena}'")
        ids_escenas.add(id_escena)

        # Texto de narración
        texto = escena.get("texto_narracion", "")
        if not isinstance(texto, str):
            errores.append(
                f"Escena '{id_escena}': 'texto_narracion' debe ser string."
            )
            continue
        if not texto.strip():
            errores.append(f"Escena '{id_escena}' no tiene texto de narración.")
        elif len(texto.strip()) < 10:
            warnings.append(f"Texto muy corto en escena '{id_escena}' ({len(texto)} chars).")

        # Clip de vídeo
        clip_ref = escena.get("clip", "")
        if not clip_ref:
            errores.append(f"Escena '{id_escena}' no tiene clip de vídeo definido.")
            continue

        ruta_clip = os.path.join(ruta_proyecto, clip_ref)
        info_clip = obtener_info_media(ruta_clip)

        if "error" in info_clip:
            errores.append(
                f"Clip inválido o ausente en '{id_escena}': {info_clip['error']}"
            )
        else:
            duracion = info_clip.get("duracion", 0)
            metadatos_clips[id_escena] = info_clip

            if duracion < 3.0:
                warnings.append(
                    f"Clip '{id_escena}' dura menos de 3 segundos ({duracion:.2f}s)."
                )

            # Lógica de tiempos clip_inicio / clip_fin
            fin_seg = escena.get("clip_fin_seg")
            inicio_seg = escena.get("clip_inicio_seg", 0)

            if inicio_seg < 0:
                errores.append(
                    f"clip_inicio_seg negativo en '{id_escena}': {inicio_seg}s."
                )
            if inicio_seg >= duracion:
                errores.append(
                    f"clip_inicio_seg ({inicio_seg}s) en '{id_escena}' "
                    f"es >= duración del clip ({duracion:.2f}s)."
                )
            if fin_seg is not None:
                if fin_seg <= inicio_seg:
                    errores.append(
                        f"Error lógico de tiempo en clip '{id_escena}': "
                        f"fin ({fin_seg}s) <= inicio ({inicio_seg}s)."
                    )
                if fin_seg > duracion + 0.05:
                    warnings.append(
                        f"clip_fin_seg ({fin_seg}s) en '{id_escena}' excede "
                        f"la duración del clip ({duracion:.2f}s). Se truncará."
                    )

    # ─── Validación de Música ───────────────────────────
    if "musica" in datos:
        musica = datos["musica"]
        if musica.get("fuente") == "archivo":
            archivo_musica = musica.get("archivo", "")
            if archivo_musica:
                ruta_musica = os.path.join(ruta_proyecto, archivo_musica)
                if not os.path.exists(ruta_musica):
                    errores.append(f"Archivo de música no encontrado: {ruta_musica}")
            else:
                errores.append("Música con fuente 'archivo' pero sin ruta definida.")
    else:
        warnings.append(
            "No se definió sección 'musica'. El vídeo se montará solo con narración."
        )

    # ─── Resultado Final ────────────────────────────────
    exito = len(errores) == 0

    if exito:
        logger.info(
            f"Validación completada: {len(escenas)} escenas, "
            f"{len(warnings)} warnings, 0 errores."
        )
    else:
        logger.error(f"Validación fallida: {len(errores)} errores encontrados.")

    return {
        "exito": exito,
        "errores": errores,
        "warnings": warnings,
        "datos": datos,
        "metadatos_clips": metadatos_clips
    }

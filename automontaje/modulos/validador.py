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
from .utilidades import (
    obtener_info_media, logger, ruta_segura_proyecto, validar_id_escena,
    validar_resolucion, normalizar_fps, validar_velocidad_tts,
    validar_fuente_subtitulos
)
from configuracion import (
    ARCHIVO_PROYECTO, VOCES_EDGE_CONOCIDAS, RESOLUCION_DEFAULT, FPS_DEFAULT
)


TRANSICIONES_VALIDAS = {
    "cut", "fade_from_black", "fade_to_black", "dip_to_black", "crossfade"
}

MOTORES_NARRACION = {"edge-tts", "sintetico"}


def errores_duracion_estricta(datos: dict) -> list:
    """Errores del modo duración estricta: solo se admiten cortes secos.

    Un fundido solaparía escenas o alteraría sus fotogramas, y la duración total dejaría de ser
    la suma exacta de las escenas que ya se renderizaron a medida.
    """
    errores = []
    for escena in datos.get("escenas", []):
        if not isinstance(escena, dict):
            continue
        for campo in ("transicion_entrada", "transicion_salida"):
            transicion = escena.get(campo, "cut")
            if isinstance(transicion, str) and transicion.strip().lower() != "cut":
                errores.append(
                    f"Escena '{escena.get('id')}': con montaje.duracion_estricta solo se admite "
                    f"'{campo}': 'cut' (tiene '{transicion}')."
                )
    return errores


def _es_numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


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

    resolucion = datos.get("resolucion", RESOLUCION_DEFAULT)
    if not validar_resolucion(resolucion):
        errores.append(
            "El campo 'resolucion' debe tener formato seguro como '1920x1080'."
        )

    try:
        normalizar_fps(datos.get("fps", FPS_DEFAULT))
    except (TypeError, ValueError) as e:
        errores.append(f"El campo 'fps' es invalido: {e}")

    # ─── Validación del Narrador ────────────────────────
    if "narrador" in datos:
        narrador = datos["narrador"]
        if not isinstance(narrador, dict):
            errores.append(
                f"El campo 'narrador' debe ser un objeto JSON, no {type(narrador).__name__}."
            )
        else:
            motor = narrador.get("motor", "edge-tts")
            voz = narrador.get("voz", "")
            if motor not in MOTORES_NARRACION:
                errores.append(
                    f"'narrador.motor' no válido: {motor!r}. Usa 'edge-tts' o 'sintetico' (voz de prueba sin red)."
                )
            elif motor == "sintetico":
                pass  # la voz sintética no usa 'voz'
            elif not voz:
                errores.append("El narrador no tiene 'voz' definida.")
            elif voz not in VOCES_EDGE_CONOCIDAS:
                warnings.append(
                    f"Voz '{voz}' no está en la lista conocida. "
                    f"Podría funcionar si es válida en Edge TTS, pero no ha sido verificada."
                )

            if "velocidad" not in narrador:
                warnings.append("No se definió 'velocidad' para el narrador. Se usará +0%.")
            elif not validar_velocidad_tts(narrador["velocidad"]):
                errores.append(
                    "El campo 'narrador.velocidad' debe tener formato '+0%', '-5%', etc."
                )

    # ─── Validación del Montaje ─────────────────────────
    montaje = datos.get("montaje", {})
    if not isinstance(montaje, dict) or not isinstance(montaje.get("duracion_estricta", False), bool):
        errores.append("'montaje' debe ser un objeto y 'montaje.duracion_estricta' un booleano.")
    elif montaje.get("duracion_estricta"):
        errores.extend(errores_duracion_estricta(datos))

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
        if not isinstance(escena, dict):
            errores.append(f"La escena #{indice + 1} debe ser un objeto JSON.")
            continue

        id_escena = escena.get("id")
        if not validar_id_escena(id_escena):
            errores.append(
                f"Escena #{indice + 1}: 'id' obligatorio y solo puede usar letras, "
                "numeros, guion y guion bajo."
            )
            id_escena = f"escena_invalida_{indice}"

        # IDs duplicados
        if id_escena in ids_escenas:
            errores.append(f"ID de escena duplicado: '{id_escena}'")
        ids_escenas.add(id_escena)

        for campo_trans in ("transicion_entrada", "transicion_salida"):
            transicion = escena.get(campo_trans, "cut")
            if (
                not isinstance(transicion, str)
                or transicion.strip().lower() not in TRANSICIONES_VALIDAS
            ):
                errores.append(
                    f"Escena '{id_escena}': '{campo_trans}' no es una transicion valida."
                )

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
        if not isinstance(clip_ref, str) or not clip_ref:
            errores.append(f"Escena '{id_escena}' no tiene clip de vídeo definido.")
            continue

        try:
            ruta_clip = ruta_segura_proyecto(ruta_proyecto, clip_ref)
        except ValueError as e:
            errores.append(f"Escena '{id_escena}': ruta de clip invalida: {e}")
            continue
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

            if not _es_numero(inicio_seg):
                errores.append(
                    f"clip_inicio_seg en '{id_escena}' debe ser numerico."
                )
                continue
            if fin_seg is not None and not _es_numero(fin_seg):
                errores.append(
                    f"clip_fin_seg en '{id_escena}' debe ser numerico o null."
                )
                continue

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
        if not isinstance(musica, dict):
            errores.append("El campo 'musica' debe ser un objeto JSON.")
        elif musica.get("fuente") == "archivo":
            archivo_musica = musica.get("archivo", "")
            if isinstance(archivo_musica, str) and archivo_musica:
                try:
                    ruta_musica = ruta_segura_proyecto(ruta_proyecto, archivo_musica)
                except ValueError as e:
                    errores.append(f"Ruta de musica invalida: {e}")
                    ruta_musica = None
                if ruta_musica and not os.path.exists(ruta_musica):
                    errores.append(f"Archivo de música no encontrado: {ruta_musica}")
            else:
                errores.append("Música con fuente 'archivo' pero sin ruta definida.")
        elif musica.get("fuente") not in (None, "ninguna"):
            errores.append("El campo 'musica.fuente' solo admite 'archivo' o 'ninguna'.")
    else:
        warnings.append(
            "No se definió sección 'musica'. El vídeo se montará solo con narración."
        )

    # ─── Validación de Subtítulos ───────────────────────
    if "subtitulos" in datos:
        subtitulos = datos["subtitulos"]
        if not isinstance(subtitulos, dict):
            errores.append("El campo 'subtitulos' debe ser un objeto JSON.")
        else:
            fuente = subtitulos.get("fuente", "Arial")
            tamano = subtitulos.get("tamano", 24)
            if not validar_fuente_subtitulos(fuente):
                errores.append(
                    "El campo 'subtitulos.fuente' contiene caracteres no permitidos."
                )
            if isinstance(tamano, bool) or not isinstance(tamano, (int, float)):
                errores.append("El campo 'subtitulos.tamano' debe ser numerico.")
            elif tamano < 8 or tamano > 96:
                errores.append("El campo 'subtitulos.tamano' debe estar entre 8 y 96.")

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

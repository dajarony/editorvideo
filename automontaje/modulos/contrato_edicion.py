# -*- coding: utf-8 -*-
"""Contratos de edicion basados en herramientas seguras.

La IA no ejecuta FFmpeg ni comandos crudos. Solo puede pedir herramientas
registradas con parametros validados. El validador maestro normaliza el
contrato antes de que el ejecutor toque el video.

Tiempos: por defecto ("tiempos": "original") todos los segundos de un contrato se
refieren al video ORIGINAL. Si un paso quita tiempo (un corte, quitar silencios), los
pasos siguientes se trasladan al resultado con modulos/tiempos.py. Con
"tiempos": "resultado" cada paso usa los segundos del video que le llega.
"""

from __future__ import annotations

import copy
import math
import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any, Callable

from .tiempos import MapaTiempos


ParametroSpec = dict[str, Any]
ValidadorExtra = Callable[[dict[str, Any]], list[str]]
TIEMPOS_VALIDOS = ("original", "resultado")


@dataclass(frozen=True)
class SalidaPaso:
    """Resultado de una herramienta que quita tiempo: su salida y los tramos que conserva
    (en segundos de SU entrada), para trasladar los tiempos de los pasos siguientes."""

    ruta: str
    conservados: list | None = None


EjecutorHerramienta = Callable[[str, str, dict[str, Any]], "str | SalidaPaso"]


@dataclass(frozen=True)
class HerramientaEdicion:
    """Definicion publica y ejecutable de una herramienta.

    `tiempos` nombra los parametros que son segundos del video: ("inicio", "fin") es un
    tramo y ("inicio",) un momento. El ejecutor los traslada del original al resultado.
    """

    nombre: str
    descripcion: str
    parametros: dict[str, ParametroSpec]
    ejecutar: EjecutorHerramienta
    validar_extra: ValidadorExtra | None = None
    tiempos: tuple = ()


def _validar_tipo(nombre: str, valor: Any, tipo: str) -> str | None:
    if tipo == "bool" and not isinstance(valor, bool):
        return f"'{nombre}' debe ser booleano."
    if tipo == "str" and not isinstance(valor, str):
        return f"'{nombre}' debe ser texto."
    if tipo == "int" and not isinstance(valor, int):
        return f"'{nombre}' debe ser entero."
    if tipo == "float" and not isinstance(valor, (int, float)):
        return f"'{nombre}' debe ser numero."
    return None


def _normalizar_parametros(
    herramienta: HerramientaEdicion,
    parametros: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Valida parametros contra el esquema simple de la herramienta."""
    errores: list[str] = []
    normalizados: dict[str, Any] = {}

    if not isinstance(parametros, dict):
        return {}, ["'parametros' debe ser un objeto."]

    permitidos = set(herramienta.parametros)
    for clave in parametros:
        if clave not in permitidos:
            errores.append(
                f"Parametro desconocido para '{herramienta.nombre}': {clave!r}."
            )

    for nombre, spec in herramienta.parametros.items():
        requerido = bool(spec.get("required", False))
        if nombre not in parametros:
            if requerido:
                errores.append(f"Falta parametro requerido '{nombre}'.")
            elif "default" in spec:
                normalizados[nombre] = copy.deepcopy(spec["default"])
            continue

        valor = parametros[nombre]
        tipo = spec.get("type")
        if tipo:
            err = _validar_tipo(nombre, valor, tipo)
            if err:
                errores.append(err)
                continue

        if "choices" in spec and valor not in spec["choices"]:
            errores.append(
                f"'{nombre}' debe ser uno de: {', '.join(map(str, spec['choices']))}."
            )
            continue

        if isinstance(valor, (int, float)):
            if "min" in spec and valor < spec["min"]:
                errores.append(f"'{nombre}' debe ser >= {spec['min']}.")
                continue
            if "max" in spec and valor > spec["max"]:
                errores.append(f"'{nombre}' debe ser <= {spec['max']}.")
                continue

        if tipo == "str" and spec.get("max_length") and len(valor) > spec["max_length"]:
            errores.append(f"'{nombre}' excede {spec['max_length']} caracteres.")
            continue

        normalizados[nombre] = valor

    if herramienta.validar_extra:
        errores.extend(herramienta.validar_extra(normalizados))

    return normalizados, errores


def _ejecutar_cortar_silencios(entrada: str, salida: str, params: dict[str, Any]) -> SalidaPaso:
    from .mejoras import recortar_silencios

    ruta, conservados = recortar_silencios(
        entrada,
        salida,
        umbral_db=params["umbral_db"],
        duracion_min=params["duracion_min"],
    )
    return SalidaPaso(ruta, conservados)


def _ejecutar_color_grading(entrada: str, salida: str, params: dict[str, Any]) -> str:
    from .mejoras import aplicar_color_grading

    return aplicar_color_grading(entrada, salida, estilo=params["estilo"])


def _ejecutar_mejora_real(entrada: str, salida: str, params: dict[str, Any]) -> str:
    from .mejoras import mejorar_imagen_real

    return mejorar_imagen_real(entrada, salida, nivel=params["nivel"])


def _ejecutar_vertical(entrada: str, salida: str, params: dict[str, Any]) -> str:
    from .mejoras import convertir_vertical_9_16

    return convertir_vertical_9_16(entrada, salida)


def _ejecutar_subtitulos(entrada: str, salida: str, params: dict[str, Any]) -> str:
    from .mejoras import anadir_subtitulos_automaticos

    return anadir_subtitulos_automaticos(
        entrada,
        salida,
        idioma=params["idioma"],
        modelo_whisper=params["modelo"],
    )


def _ejecutar_limpiar_voz(entrada: str, salida: str, params: dict[str, Any]) -> str:
    from .mejoras import limpiar_voz

    return limpiar_voz(entrada, salida, nivel=params["nivel"])


def _ejecutar_fades_audio(entrada: str, salida: str, params: dict[str, Any]) -> str:
    from .mejoras import anadir_audio_fades

    # El contrato usa milisegundos; la funcion espera segundos.
    return anadir_audio_fades(
        entrada, salida, duracion_fade=params["duracion_ms"] / 1000.0
    )


# ─── Efectos por momento concreto ───────────────────────

def _ejecutar_corte(entrada: str, salida: str, params: dict[str, Any]) -> SalidaPaso:
    from .efectos import _info_video, cortar_fragmento, tramos_conservados_tras_corte

    duracion = _info_video(entrada)[0]
    ruta = cortar_fragmento(entrada, salida, inicio=params["inicio"], fin=params["fin"])
    return SalidaPaso(ruta, tramos_conservados_tras_corte(duracion, params["inicio"], params["fin"]))


def _ejecutar_texto(entrada: str, salida: str, params: dict[str, Any]) -> str:
    from .efectos import superponer_texto

    return superponer_texto(
        entrada, salida,
        texto=params["texto"],
        inicio=params["inicio"],
        duracion=params["duracion"],
        posicion=params["posicion"],
    )


def _ejecutar_imagen(entrada: str, salida: str, params: dict[str, Any]) -> str:
    from .efectos import superponer_imagen

    return superponer_imagen(
        entrada, salida,
        archivo=params["archivo"],
        inicio=params["inicio"],
        duracion=params["duracion"],
        posicion=params["posicion"],
        escala=params["escala"],
    )


def _ejecutar_zoom(entrada: str, salida: str, params: dict[str, Any]) -> str:
    from .efectos import aplicar_zoom

    return aplicar_zoom(
        entrada, salida,
        inicio=params["inicio"],
        duracion=params["duracion"],
        intensidad=params["intensidad"],
    )


def _validar_corte(params: dict[str, Any]) -> list[str]:
    if "inicio" in params and "fin" in params and params["fin"] <= params["inicio"]:
        return ["'fin' debe ser mayor que 'inicio'."]
    return []


def _validar_imagen(params: dict[str, Any]) -> list[str]:
    archivo = params.get("archivo", "")
    if archivo and not os.path.exists(archivo):
        return [f"no existe la imagen: {archivo}"]
    return []


REGISTRO_HERRAMIENTAS: dict[str, HerramientaEdicion] = {
    "cortar_silencios": HerramientaEdicion(
        nombre="cortar_silencios",
        descripcion="Elimina silencios largos del audio/video.",
        parametros={
            "umbral_db": {"type": "float", "default": -35.0, "min": -80.0, "max": -5.0},
            "duracion_min": {"type": "float", "default": 0.45, "min": 0.1, "max": 5.0},
        },
        ejecutar=_ejecutar_cortar_silencios,
    ),
    "color_grading": HerramientaEdicion(
        nombre="color_grading",
        descripcion="Aplica color grading seguro y protegido contra oscurecimiento.",
        parametros={
            "estilo": {
                "type": "str",
                "default": "natural_claro",
                "choices": ["natural_claro", "neutro", "calido", "cinematico"],
            },
        },
        ejecutar=_ejecutar_color_grading,
    ),
    "mejora_real": HerramientaEdicion(
        nombre="mejora_real",
        descripcion="Mejora nitidez, brillo, color y resolucion x2 con FFmpeg.",
        parametros={
            "nivel": {
                "type": "str",
                "default": "media",
                "choices": ["suave", "media", "fuerte"],
            },
        },
        ejecutar=_ejecutar_mejora_real,
    ),
    "vertical_9_16": HerramientaEdicion(
        nombre="vertical_9_16",
        descripcion="Convierte el video a formato vertical 9:16.",
        parametros={},
        ejecutar=_ejecutar_vertical,
    ),
    "subtitulos": HerramientaEdicion(
        nombre="subtitulos",
        descripcion="Transcribe y quema subtitulos automaticos.",
        parametros={
            "idioma": {"type": "str", "default": "es", "max_length": 8},
            "modelo": {
                "type": "str",
                "default": "base",
                "choices": ["tiny", "base", "small", "medium"],
            },
        },
        ejecutar=_ejecutar_subtitulos,
    ),
    "limpiar_voz": HerramientaEdicion(
        nombre="limpiar_voz",
        descripcion="Aisla voz/quita musica o aplica limpieza basica si no hay IA.",
        parametros={
            "nivel": {
                "type": "str",
                "default": "media",
                "choices": ["suave", "media", "fuerte"],
            },
        },
        ejecutar=_ejecutar_limpiar_voz,
    ),
    "fades_audio": HerramientaEdicion(
        nombre="fades_audio",
        descripcion="Anade fades cortos al inicio y final del audio.",
        parametros={
            "duracion_ms": {"type": "int", "default": 30, "min": 5, "max": 2000},
        },
        ejecutar=_ejecutar_fades_audio,
    ),
    "corte": HerramientaEdicion(
        nombre="corte",
        descripcion="Quita un tramo del video entre 'inicio' y 'fin' (segundos).",
        parametros={
            "inicio": {"type": "float", "required": True, "min": 0.0, "max": 86400.0},
            "fin": {"type": "float", "required": True, "min": 0.0, "max": 86400.0},
        },
        ejecutar=_ejecutar_corte,
        validar_extra=_validar_corte,
        tiempos=("inicio", "fin"),
    ),
    "texto": HerramientaEdicion(
        nombre="texto",
        descripcion="Muestra un texto en pantalla en un momento concreto (segundos).",
        parametros={
            "texto": {"type": "str", "required": True, "max_length": 120},
            "inicio": {"type": "float", "required": True, "min": 0.0, "max": 86400.0},
            "duracion": {"type": "float", "default": 3.0, "min": 0.3, "max": 60.0},
            "posicion": {
                "type": "str", "default": "abajo",
                "choices": ["arriba", "centro", "abajo"],
            },
        },
        ejecutar=_ejecutar_texto,
        tiempos=("inicio",),
    ),
    "imagen": HerramientaEdicion(
        nombre="imagen",
        descripcion="Superpone una imagen/logo en un momento concreto (segundos).",
        parametros={
            "archivo": {"type": "str", "required": True, "max_length": 500},
            "inicio": {"type": "float", "required": True, "min": 0.0, "max": 86400.0},
            "duracion": {"type": "float", "default": 4.0, "min": 0.3, "max": 60.0},
            "posicion": {
                "type": "str", "default": "arriba_der",
                "choices": ["arriba_izq", "arriba_der", "centro",
                            "abajo_izq", "abajo_der"],
            },
            "escala": {"type": "float", "default": 0.28, "min": 0.05, "max": 1.0},
        },
        ejecutar=_ejecutar_imagen,
        validar_extra=_validar_imagen,
        tiempos=("inicio",),
    ),
    "zoom": HerramientaEdicion(
        nombre="zoom",
        descripcion="Aplica un zoom suave (punch-in) en un momento del video.",
        parametros={
            "inicio": {"type": "float", "required": True, "min": 0.0, "max": 86400.0},
            "duracion": {"type": "float", "default": 2.0, "min": 0.3, "max": 60.0},
            "intensidad": {
                "type": "str", "default": "media",
                "choices": ["suave", "media", "fuerte"],
            },
        },
        ejecutar=_ejecutar_zoom,
        tiempos=("inicio",),
    ),
}


def listar_herramientas() -> list[dict[str, Any]]:
    """Devuelve el catalogo publico que puede ver la IA o la interfaz."""
    return [
        {
            "nombre": h.nombre,
            "descripcion": h.descripcion,
            "parametros": copy.deepcopy(h.parametros),
        }
        for h in REGISTRO_HERRAMIENTAS.values()
    ]


def validar_contrato_herramientas(contrato: dict[str, Any]) -> dict[str, Any]:
    """Valida el contrato maestro sin ejecutar nada."""
    errores: list[str] = []
    avisos: list[str] = []

    if not isinstance(contrato, dict):
        return {
            "valido": False,
            "errores": ["El contrato debe ser un objeto."],
            "avisos": [],
            "contrato": None,
        }

    pasos_raw = contrato.get("herramientas", contrato.get("acciones"))
    if not isinstance(pasos_raw, list):
        errores.append("El contrato debe tener una lista 'herramientas'.")
        pasos_raw = []

    pasos = []
    for idx, paso in enumerate(pasos_raw):
        if not isinstance(paso, dict):
            errores.append(f"herramientas[{idx}] debe ser un objeto.")
            continue

        nombre = str(paso.get("herramienta", paso.get("tool", ""))).strip()
        if not nombre:
            errores.append(f"herramientas[{idx}] no tiene 'herramienta'.")
            continue
        herramienta = REGISTRO_HERRAMIENTAS.get(nombre)
        if herramienta is None:
            errores.append(f"herramientas[{idx}] herramienta desconocida: {nombre!r}.")
            continue

        params, errores_params = _normalizar_parametros(
            herramienta,
            paso.get("parametros", paso.get("params", {})),
        )
        for error in errores_params:
            errores.append(f"{nombre}: {error}")
        if errores_params:
            continue

        pasos.append({
            "herramienta": nombre,
            "parametros": params,
        })

    if len(pasos) > 30:
        avisos.append("El contrato tiene mas de 30 pasos; revisa si es necesario.")

    tiempos = contrato.get("tiempos", "original")
    if tiempos not in TIEMPOS_VALIDOS:
        errores.append(f"'tiempos' debe ser uno de: {', '.join(TIEMPOS_VALIDOS)}.")

    normalizado = None
    if not errores:
        normalizado = {
            "version": str(contrato.get("version", "1.0")),
            "tiempos": tiempos,
            "herramientas": pasos,
        }

    return {
        "valido": not errores,
        "errores": errores,
        "avisos": avisos,
        "contrato": normalizado,
    }


def _segundos_legibles(t: float) -> str:
    return f"{t:g}" if abs(t - round(t)) < 1e-9 else f"{t:.2f}"


def _trasladar_tiempos(
    herramienta: HerramientaEdicion, params: dict[str, Any], mapa: MapaTiempos, avisos: list[str]
) -> dict[str, Any] | None:
    """Parametros con los segundos del original trasladados al video que llega a este paso.

    Devuelve None si el paso ya no tiene sentido (corta un tramo que otro paso quito entero).
    """
    if not herramienta.tiempos:
        return params
    nuevos = dict(params)
    if herramienta.tiempos == ("inicio", "fin"):
        tramo = mapa.llevar_tramo(params["inicio"], params["fin"])
        if tramo is None:
            avisos.append(
                f"{herramienta.nombre}: el tramo {_segundos_legibles(params['inicio'])}–"
                f"{_segundos_legibles(params['fin'])} s del original ya se habia quitado; se omite."
            )
            return None
        nuevos["inicio"], nuevos["fin"] = round(tramo[0], 3), round(tramo[1], 3)
        return nuevos
    for clave in herramienta.tiempos:
        t, quitado = mapa.llevar(params[clave])
        if quitado:
            avisos.append(
                f"{herramienta.nombre}: el segundo {_segundos_legibles(params[clave])} del original "
                f"se habia quitado; se usa el siguiente momento que queda."
            )
        nuevos[clave] = round(t, 3)
    return nuevos


def ejecutar_contrato_herramientas(
    ruta_entrada: str,
    ruta_salida: str,
    contrato: dict[str, Any],
    al_progresar: Callable[[float, str], None] | None = None,
    mapa_inicial: MapaTiempos | None = None,
) -> dict[str, Any]:
    """Valida y ejecuta un contrato herramienta por herramienta.

    `al_progresar(fraccion, texto)` informa del avance (0..1). `mapa_inicial` sirve para
    ejecutar el contrato sobre un extracto del original (la previsualizacion): sus tiempos
    siguen siendo los del original completo.
    """
    if not os.path.exists(ruta_entrada):
        return {
            "exito": False,
            "errores": [f"No existe el archivo de entrada: {ruta_entrada}"],
            "avisos": [],
        }

    validacion = validar_contrato_herramientas(contrato)
    if not validacion["valido"]:
        return {
            "exito": False,
            "errores": validacion["errores"],
            "avisos": validacion["avisos"],
        }

    contrato_ok = validacion["contrato"]
    pasos = contrato_ok["herramientas"]
    avisos = list(validacion["avisos"])
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)) or ".", exist_ok=True)
    progresar = al_progresar or (lambda fraccion, texto: None)

    _, ext = os.path.splitext(ruta_salida)
    ext = ext or os.path.splitext(ruta_entrada)[1] or ".mp4"

    # Sin una duracion conocida basta un mapa sin final: lo que cuenta son los tramos quitados.
    mapa = None
    if contrato_ok["tiempos"] == "original":
        mapa = mapa_inicial or MapaTiempos.identidad(math.inf)

    actual = ruta_entrada
    ejecutados: list[str] = []
    omitidos: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aegs_tools_") as tmpdir:
        for idx, paso in enumerate(pasos, 1):
            nombre = paso["herramienta"]
            herramienta = REGISTRO_HERRAMIENTAS[nombre]
            params = paso["parametros"]
            if mapa is not None:
                params = _trasladar_tiempos(herramienta, params, mapa, avisos)
                if params is None:
                    omitidos.append(nombre)
                    continue
            progresar((idx - 1) / len(pasos), f"Paso {idx}/{len(pasos)}: {herramienta.descripcion}")
            salida_paso = os.path.join(tmpdir, f"paso_{idx:03d}_{nombre}{ext}")
            try:
                resultado = herramienta.ejecutar(actual, salida_paso, params)
            except Exception as exc:
                return {
                    "exito": False,
                    "errores": [f"{nombre} fallo: {exc}"],
                    "avisos": avisos,
                    "pasos_ejecutados": ejecutados,
                }

            conservados = None
            if isinstance(resultado, SalidaPaso):
                resultado, conservados = resultado.ruta, resultado.conservados
            if not os.path.exists(resultado):
                return {
                    "exito": False,
                    "errores": [f"{nombre} no genero salida: {resultado}"],
                    "avisos": avisos,
                    "pasos_ejecutados": ejecutados,
                }

            if mapa is not None and conservados is not None:
                mapa = mapa.tras_conservar(conservados)
            actual = resultado
            ejecutados.append(nombre)

        shutil.copy2(actual, ruta_salida)

    progresar(1.0, "Listo")
    return {
        "exito": True,
        "archivo": ruta_salida,
        "contrato": contrato_ok,
        "avisos": avisos,
        "pasos_ejecutados": ejecutados,
        "pasos_omitidos": omitidos,
    }


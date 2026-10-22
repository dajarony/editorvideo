# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.0
═══════════════════════════════════════════════════════════
Archivo: modulos/servicio_edicion.py
Tipo: Lógica → Servicio único de edición
Dependencias: contrato_edicion

Entradas:
- Las opciones de mejora de la interfaz o de la CLI (el diccionario de ConfigEdicion).

Acciones:
1. Convierte las opciones en un contrato de herramientas, siempre en el mismo orden.
2. Lo ejecuta con el mismo ejecutor que los contratos escritos a mano.

Salidas:
- El resultado del ejecutor de contratos.

Antes la ventana tenía su propia cadena de pasos (en otro orden que la CLI) y su propia
copia de Real-ESRGAN; ahora todas las formas de editar pasan por aquí, así que una
corrección en una herramienta vale para la ventana, la CLI y los contratos.
═══════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Callable

from .contrato_edicion import ejecutar_contrato_herramientas

# Valores por defecto de cada opción: nada se aplica si no se pide, salvo los fades de 30 ms.
POR_DEFECTO: dict[str, Any] = {
    "tipo": "video",
    "cortar_silencios": False,
    "umbral_silencio_db": -35.0,
    "duracion_silencio_s": 0.6,
    "eliminar_muletillas": False,
    "color_grading": False,
    "estilo_color": "natural_claro",
    "mejora_real": False,
    "nivel_mejora": "media",
    "formato_vertical": False,
    "encuadre_vertical": "centro",
    "limpiar_voz": False,
    "nivel_voz": "media",
    "subtitulos": False,
    "audio_fades": True,
    "duracion_fade": 0.03,
    "esrgan": False,
    "modelo_esrgan": "realesrgan-x4plus",
    "idioma": "es",
}


def contrato_desde_config(config: dict[str, Any]) -> dict[str, Any]:
    """Contrato de herramientas equivalente a las opciones marcadas, en orden fijo.

    Orden: primero lo que quita tiempo (silencios, muletillas), luego imagen y formato,
    después el audio (voz, subtítulos sobre el formato final, fades al final del audio)
    y por último la super resolución, la más lenta, sobre el resultado ya recortado.
    Una imagen solo recibe la mejora real y la super resolución.
    """
    cfg = {**POR_DEFECTO, **{k: v for k, v in (config or {}).items() if v is not None}}
    video = cfg["tipo"] != "imagen"
    pasos: list[dict[str, Any]] = []

    def paso(nombre: str, **parametros: Any) -> None:
        pasos.append({"herramienta": nombre, "parametros": parametros})

    if video and cfg["cortar_silencios"]:
        paso("cortar_silencios", umbral_db=float(cfg["umbral_silencio_db"]),
             duracion_min=float(cfg["duracion_silencio_s"]))
    if video and cfg["eliminar_muletillas"]:
        paso("eliminar_muletillas", idioma=cfg["idioma"])
    if video and cfg["color_grading"]:
        paso("color_grading", estilo=cfg["estilo_color"])
    if cfg["mejora_real"]:
        paso("mejora_real", nivel=cfg["nivel_mejora"])
    if video and cfg["formato_vertical"]:
        paso("vertical_9_16", encuadre=cfg["encuadre_vertical"])
    if video and cfg["limpiar_voz"]:
        paso("limpiar_voz", nivel=cfg["nivel_voz"])
    if video and cfg["subtitulos"]:
        paso("subtitulos", idioma=cfg["idioma"])
    if video and cfg["audio_fades"]:
        paso("fades_audio", duracion_ms=max(5, int(round(float(cfg["duracion_fade"]) * 1000))))
    if cfg["esrgan"]:
        paso("superresolucion_ia", modelo=cfg["modelo_esrgan"])
    return {"herramientas": pasos}


def procesar(
    ruta_entrada: str,
    ruta_salida: str,
    config: dict[str, Any],
    al_progresar: Callable[[float, str], None] | None = None,
) -> dict[str, Any]:
    """Aplica las opciones marcadas a un vídeo o una imagen con el ejecutor de contratos."""
    return ejecutar_contrato_herramientas(
        ruta_entrada, ruta_salida, contrato_desde_config(config), al_progresar=al_progresar
    )

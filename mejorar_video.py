# -*- coding: utf-8 -*-
"""
mejorar_video.py — Aplica todas las mejoras automáticas a un vídeo.

Uso:
    python mejorar_video.py <ruta_video>
    python mejorar_video.py <ruta_video> --estilo calido
    python mejorar_video.py <ruta_video> --sin-silencios --sin-color
    python mejorar_video.py <ruta_video> --muletillas --idioma en

Ejemplos:
    python mejorar_video.py "video londres/5780528936735743517.mp4"
    python mejorar_video.py "video londres/otro mercado en londres.mp4" --estilo calido
"""

import sys
import os
import argparse

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.dirname(__file__))

from automontaje.modulos.mejoras import aplicar_todas_mejoras


def main():
    parser = argparse.ArgumentParser(
        description="Mejoras automáticas de vídeo: silencios, color grading y audio fades."
    )
    parser.add_argument("video", help="Ruta al vídeo de entrada")
    parser.add_argument(
        "--estilo", default="cinematico",
        choices=["cinematico", "calido", "neutro"],
        help="Estilo de color grading (default: cinematico)"
    )
    parser.add_argument("--sin-silencios", action="store_true", help="No cortar silencios")
    parser.add_argument("--sin-color",     action="store_true", help="No aplicar color grading")
    parser.add_argument("--sin-fades",     action="store_true", help="No añadir audio fades")
    parser.add_argument("--muletillas",    action="store_true", help="Eliminar muletillas (requiere Whisper)")
    parser.add_argument("--idioma",        default="es",        help="Idioma para muletillas: es | en")
    parser.add_argument("--salida",        default=None,        help="Ruta de salida (default: <nombre>_mejorado.mp4)")

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"❌ No se encontró el vídeo: {args.video}")
        sys.exit(1)

    # Calcular ruta de salida
    if args.salida:
        ruta_salida = args.salida
    else:
        base, ext = os.path.splitext(args.video)
        ruta_salida = f"{base}_mejorado{ext}"

    config = {
        "cortar_silencios":    not args.sin_silencios,
        "eliminar_muletillas": args.muletillas,
        "color_grading":       not args.sin_color,
        "estilo_color":        args.estilo,
        "audio_fades":         not args.sin_fades,
        "idioma":              args.idioma,
    }

    print(f"\nVideo entrada : {args.video}")
    print(f"Video salida  : {ruta_salida}")
    print("Mejoras activas:")
    print(f"   Silencios    : {'Si' if config['cortar_silencios'] else 'No'}")
    print(f"   Muletillas   : {'Si' if config['eliminar_muletillas'] else 'No'}")
    print(f"   Color grading: {'Si - ' + config['estilo_color'] if config['color_grading'] else 'No'}")
    print(f"   Audio fades  : {'Si' if config['audio_fades'] else 'No'}")
    print()

    resultado = aplicar_todas_mejoras(args.video, ruta_salida, config)

    if resultado["exito"]:
        print(f"\nListo! Video mejorado guardado en:\n   {resultado['archivo']}")
    else:
        print(f"\nError: {resultado.get('error', 'desconocido')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

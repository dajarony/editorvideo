# -*- coding: utf-8 -*-
"""CLI para aplicar mejoras y comandos de edicion a un video."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from automontaje.modulos.editor_comandos import parsear_comando_edicion
from automontaje.modulos.mejoras import aplicar_todas_mejoras


def main():
    parser = argparse.ArgumentParser(
        description="Editor automatico: mejoras, cortes, formato vertical y comandos."
    )
    parser.add_argument("video", help="Ruta al video de entrada")
    parser.add_argument(
        "--estilo", default="natural_claro",
        choices=["natural_claro", "neutro", "calido", "cinematico"],
        help="Estilo de color grading"
    )
    parser.add_argument("--sin-silencios", action="store_true", help="No cortar silencios")
    parser.add_argument("--sin-color", action="store_true", help="No aplicar color grading")
    parser.add_argument("--sin-fades", action="store_true", help="No anadir audio fades")
    parser.add_argument("--sin-mejora-real", action="store_true", help="No aplicar mejora visual real")
    parser.add_argument("--nivel", default="media", choices=["suave", "media", "fuerte"], help="Nivel de mejora real")
    parser.add_argument("--vertical", action="store_true", help="Exportar en formato vertical 9:16")
    parser.add_argument("--subtitulos", action="store_true", help="Generar y quemar subtitulos automaticos")
    parser.add_argument("--muletillas", action="store_true", help="Eliminar muletillas con Whisper")
    parser.add_argument("--idioma", default="es", help="Idioma para muletillas: es | en")
    parser.add_argument("--comando", default=None, help="Orden en lenguaje natural para configurar la edicion")
    parser.add_argument("--salida", default=None, help="Ruta de salida")

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"No se encontro el video: {args.video}")
        sys.exit(1)

    if args.salida:
        ruta_salida = args.salida
    else:
        base, ext = os.path.splitext(args.video)
        ruta_salida = f"{base}_mejorado{ext}"

    if args.comando:
        plan = parsear_comando_edicion(args.comando)
        config = plan["config"]
        config["idioma"] = args.idioma
        print("Comando interpretado:")
        print(f"   Acciones: {', '.join(plan['acciones'])}")
        if plan["avisos"]:
            print(f"   Avisos  : {' | '.join(plan['avisos'])}")
    else:
        config = {
            "cortar_silencios": not args.sin_silencios,
            "eliminar_muletillas": args.muletillas,
            "color_grading": not args.sin_color,
            "estilo_color": args.estilo,
            "audio_fades": not args.sin_fades,
            "mejora_real": not args.sin_mejora_real,
            "nivel_mejora": args.nivel,
            "formato_vertical": args.vertical,
            "subtitulos": args.subtitulos,
            "idioma": args.idioma,
        }

    print(f"\nVideo entrada : {args.video}")
    print(f"Video salida  : {ruta_salida}")
    print("Mejoras activas:")
    print(f"   Silencios    : {'Si' if config['cortar_silencios'] else 'No'}")
    print(f"   Muletillas   : {'Si' if config['eliminar_muletillas'] else 'No'}")
    print(f"   Color grading: {'Si - ' + config['estilo_color'] if config['color_grading'] else 'No'}")
    print(f"   Mejora real  : {'Si - ' + config['nivel_mejora'] if config['mejora_real'] else 'No'}")
    print(f"   Vertical 9:16: {'Si' if config['formato_vertical'] else 'No'}")
    print(f"   Subtitulos   : {'Si' if config.get('subtitulos') else 'No'}")
    print(f"   Audio fades  : {'Si' if config['audio_fades'] else 'No'}")
    print()

    resultado = aplicar_todas_mejoras(args.video, ruta_salida, config)

    if resultado["exito"]:
        print(f"\nListo. Video guardado en:\n   {resultado['archivo']}")
    else:
        print(f"\nError: {resultado.get('error', 'desconocido')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
superresolucion_video.py - Mejora la calidad de video con Real-ESRGAN (IA)

Uso:
    python superresolucion_video.py <ruta_video>
    python superresolucion_video.py <ruta_video> --escala 2
    python superresolucion_video.py <ruta_video> --modelo realesrgan-x4plus-anime

Modelos disponibles:
    realesrgan-x4plus         (general, fotos reales)       - recomendado
    realesrgan-x4plus-anime   (animacion, dibujos)
    realesrnet-x4plus         (mas rapido, menos calidad)

Usa la misma implementacion que la interfaz y los contratos
(automontaje/modulos/superresolucion.py): lotes de fotogramas, deteccion de lotes en
negro y audio original. Real-ESRGAN se busca en realesrgan/ o en AEGS_REALESRGAN.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from automontaje.modulos.superresolucion import MODELOS, ampliar_con_ia  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Mejora la calidad de video con Real-ESRGAN (IA)")
    parser.add_argument("video", help="Ruta al video (o imagen) de entrada")
    parser.add_argument("--escala", type=int, default=4, choices=[2, 4],
                        help="Factor de escala: 2 o 4 (default: 4)")
    parser.add_argument("--modelo", default="realesrgan-x4plus", choices=list(MODELOS),
                        help="Modelo a usar (default: realesrgan-x4plus)")
    parser.add_argument("--salida", default=None, help="Ruta de salida (default: <nombre>_4K<ext>)")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"ERROR: No se encontro el video: {args.video}")
        sys.exit(1)

    base, ext = os.path.splitext(args.video)
    ruta_salida = args.salida or f"{base}_4K{ext or '.mp4'}"
    print("=" * 55)
    print("SUPER RESOLUCION CON REAL-ESRGAN (IA)")
    print("=" * 55)
    print(f"Entrada : {args.video}")
    print(f"Salida  : {ruta_salida}")
    print(f"Modelo  : {args.modelo}")
    print(f"Escala  : x{args.escala}")
    print()
    try:
        ampliar_con_ia(args.video, ruta_salida, modelo=args.modelo, escala=args.escala, al_estado=print)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    print()
    print(f"Listo! Guardado en:\n   {ruta_salida}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
superresolucion_video.py - Mejora la calidad de video con Real-ESRGAN (IA)

Uso:
    python superresolucion_video.py <ruta_video>
    python superresolucion_video.py <ruta_video> --escala 4
    python superresolucion_video.py <ruta_video> --modelo realesrgan-x4plus-anime

Modelos disponibles:
    realesrgan-x4plus         (general, fotos reales)       - recomendado
    realesrgan-x4plus-anime   (animacion, dibujos)
    realesrnet-x4plus         (mas rapido, menos calidad)
"""

import os
import sys
import subprocess
import argparse
import shutil

# Rutas
BASE = os.path.dirname(os.path.abspath(__file__))
ESRGAN_EXE = os.path.join(BASE, "realesrgan", "realesrgan-ncnn-vulkan.exe")
MODELOS_DIR = os.path.join(BASE, "realesrgan", "models")


def extraer_frames(ruta_video: str, carpeta_frames: str, fps: float = None):
    """Extrae todos los frames del video como imagenes PNG."""
    os.makedirs(carpeta_frames, exist_ok=True)

    # Obtener FPS original
    cmd_fps = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", ruta_video
    ]
    import json
    res = subprocess.run(cmd_fps, capture_output=True, text=True)
    info = json.loads(res.stdout)
    for stream in info["streams"]:
        if stream["codec_type"] == "video":
            num, den = stream["r_frame_rate"].split("/")
            fps = float(num) / float(den)
            break

    print(f"FPS del video: {fps:.2f}")
    print("Extrayendo frames...")

    cmd = [
        "ffmpeg", "-y", "-i", ruta_video,
        os.path.join(carpeta_frames, "frame_%08d.png")
    ]
    subprocess.run(cmd, capture_output=True)
    total = len([f for f in os.listdir(carpeta_frames) if f.endswith(".png")])
    print(f"Extraidos {total} frames.")
    return fps, total


def mejorar_frames(carpeta_entrada: str, carpeta_salida: str,
                   escala: int = 4, modelo: str = "realesrgan-x4plus"):
    """Aplica Real-ESRGAN a todos los frames."""
    os.makedirs(carpeta_salida, exist_ok=True)
    print(f"Aplicando Real-ESRGAN (modelo={modelo}, escala=x{escala})...")
    print("Esto puede tardar varios minutos segun el numero de frames...")

    cmd = [
        ESRGAN_EXE,
        "-i", carpeta_entrada,
        "-o", carpeta_salida,
        "-n", modelo,
        "-s", str(escala),
        "-f", "png"
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"Real-ESRGAN fallo:\n{resultado.stderr}")
    print("Frames mejorados correctamente.")


def reensamblar_video(carpeta_frames: str, ruta_audio_original: str,
                      ruta_salida: str, fps: float):
    """Reensambla los frames mejorados en un video con audio original."""
    print("Reensamblando video con frames mejorados...")

    # Primero crear video sin audio
    temp_sin_audio = ruta_salida.replace(".mp4", "_sin_audio.mp4")
    cmd_video = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(carpeta_frames, "frame_%08d.png"),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p",
        temp_sin_audio
    ]
    subprocess.run(cmd_video, capture_output=True)

    # Luego añadir audio original
    cmd_audio = [
        "ffmpeg", "-y",
        "-i", temp_sin_audio,
        "-i", ruta_audio_original,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        ruta_salida
    ]
    subprocess.run(cmd_audio, capture_output=True)

    # Limpiar video sin audio
    if os.path.exists(temp_sin_audio):
        os.remove(temp_sin_audio)

    print(f"Video final guardado en: {ruta_salida}")


def main():
    parser = argparse.ArgumentParser(
        description="Mejora la calidad de video con Real-ESRGAN (IA)"
    )
    parser.add_argument("video", help="Ruta al video de entrada")
    parser.add_argument("--escala", type=int, default=4, choices=[2, 4],
                        help="Factor de escala: 2 o 4 (default: 4)")
    parser.add_argument("--modelo", default="realesrgan-x4plus",
                        choices=["realesrgan-x4plus",
                                 "realesrgan-x4plus-anime",
                                 "realesrnet-x4plus"],
                        help="Modelo a usar (default: realesrgan-x4plus)")
    parser.add_argument("--salida", default=None,
                        help="Ruta de salida (default: <nombre>_4K.mp4)")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"ERROR: No se encontro el video: {args.video}")
        sys.exit(1)

    if not os.path.exists(ESRGAN_EXE):
        print(f"ERROR: No se encontro Real-ESRGAN en: {ESRGAN_EXE}")
        sys.exit(1)

    # Rutas
    base_name = os.path.splitext(args.video)[0]
    ruta_salida = args.salida or f"{base_name}_4K.mp4"
    carpeta_base = base_name + "_esrgan_tmp"
    carpeta_frames_orig = os.path.join(carpeta_base, "frames_original")
    carpeta_frames_mejor = os.path.join(carpeta_base, "frames_mejorados")

    print("=" * 55)
    print("SUPER RESOLUCION CON REAL-ESRGAN (IA)")
    print("=" * 55)
    print(f"Video entrada : {args.video}")
    print(f"Video salida  : {ruta_salida}")
    print(f"Modelo        : {args.modelo}")
    print(f"Escala        : x{args.escala}")
    print()

    try:
        # Paso 1: Extraer frames
        fps, total_frames = extraer_frames(args.video, carpeta_frames_orig)

        # Paso 2: Mejorar con IA
        mejorar_frames(carpeta_frames_orig, carpeta_frames_mejor,
                       escala=args.escala, modelo=args.modelo)

        # Paso 3: Reensamblar con audio
        reensamblar_video(carpeta_frames_mejor, args.video,
                          ruta_salida, fps)

        print()
        print("=" * 55)
        print("Listo! Video en super resolucion guardado en:")
        print(f"   {ruta_salida}")
        print("=" * 55)

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    finally:
        # Limpiar temporales
        if os.path.exists(carpeta_base):
            print("Limpiando archivos temporales...")
            shutil.rmtree(carpeta_base)


if __name__ == "__main__":
    main()

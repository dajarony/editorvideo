# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.0
═══════════════════════════════════════════════════════════
Archivo: modulos/superresolucion.py
Tipo: Postproducción → Super resolución con IA (Real-ESRGAN)
Dependencias: os, json, shutil, subprocess, Real-ESRGAN ncnn (ejecutable aparte)

Entradas:
- Una imagen o un vídeo.

Acciones:
1. Imagen: la amplía ×4 con Real-ESRGAN.
2. Vídeo: extrae los fotogramas, los amplía por lotes (un proceso por lote, para que un
   microcorte de la GPU no ennegrezca el resto), comprueba que ningún lote salga en negro,
   reensambla a los mismos fps y le devuelve el audio original.

Salidas:
- La imagen o el vídeo ampliados.

Es la única implementación: la usan la interfaz, la CLI superresolucion_video.py y la
herramienta de contrato `superresolucion_ia`.
═══════════════════════════════════════════════════════════
"""

import json
import os
import shutil
import subprocess
from .proceso import ejecutar_proceso
import sys
import tempfile

from .utilidades import binario, logger

MODELOS = ("realesrgan-x4plus", "realesrgan-x4plus-anime", "realesrnet-x4plus")
EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
_LOTE = 50
_NEGRO = 20  # brillo medio (0–255) por debajo del cual un fotograma se considera negro


def ejecutable_esrgan() -> str:
    """Ruta del ejecutable de Real-ESRGAN: AEGS_REALESRGAN o realesrgan/ en la raíz del repositorio."""
    ruta = os.environ.get("AEGS_REALESRGAN")
    if not ruta:
        raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        nombre = "realesrgan-ncnn-vulkan.exe" if sys.platform == "win32" else "realesrgan-ncnn-vulkan"
        ruta = os.path.join(raiz, "realesrgan", nombre)
    if not os.path.isfile(ruta):
        raise RuntimeError(
            f"No se encontró Real-ESRGAN en:\n{ruta}\n\n"
            "Descárgalo (realesrgan-ncnn-vulkan) en la carpeta realesrgan/ de la raíz del "
            "repositorio, o indica su ruta con la variable AEGS_REALESRGAN."
        )
    return ruta


def _comprobar_modelo(ejecutable: str, modelo: str) -> None:
    if modelo not in MODELOS:
        raise RuntimeError(f"Modelo desconocido: {modelo}. Modelos: {', '.join(MODELOS)}")
    carpeta = os.path.join(os.path.dirname(ejecutable), "models")
    if os.path.isdir(carpeta) and not all(
        os.path.exists(os.path.join(carpeta, modelo + ext)) for ext in (".param", ".bin")
    ):
        raise RuntimeError(f"El modelo '{modelo}' no está en {carpeta}.")


def _run(cmd: list, descripcion: str) -> None:
    r = ejecutar_proceso(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        detalle = (r.stderr or r.stdout or "").strip()[-700:]
        raise RuntimeError(f"{descripcion} falló:\n{detalle}")


def _ejecutar_esrgan(carpeta_entrada: str, carpeta_salida: str, modelo: str, escala: int = 4) -> None:
    """Amplía con Real-ESRGAN todas las imágenes de una carpeta (mismo nombre en la salida)."""
    _run([ejecutable_esrgan(), "-i", carpeta_entrada, "-o", carpeta_salida, "-n", modelo,
          "-s", str(escala), "-f", "png"], "Real-ESRGAN")


def _brillo(imagen: str) -> float | None:
    r = ejecutar_proceso(
        [binario("ffmpeg"), "-i", imagen, "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    for token in (r.stderr or "").split():
        if token.startswith("lavfi.signalstats.YAVG="):
            try:
                return float(token.split("=")[1])
            except ValueError:
                return None
    return None


def _fps(ruta: str) -> float:
    r = ejecutar_proceso(
        [binario("ffprobe"), "-v", "quiet", "-print_format", "json", "-show_streams", ruta],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    for stream in json.loads(r.stdout or "{}").get("streams", []):
        if stream.get("codec_type") == "video":
            n, d = stream.get("r_frame_rate", "30/1").split("/")
            return float(n) / float(d) if float(d) else 30.0
    return 30.0


def ampliar_con_ia(
    ruta_entrada: str,
    ruta_salida: str,
    modelo: str = "realesrgan-x4plus",
    al_estado=None,
    escala: int = 4,
) -> str:
    """Amplía (×4 por defecto, o ×2) una imagen o un vídeo con Real-ESRGAN.

    `al_estado(texto)` informa del avance.
    """
    estado = al_estado or (lambda texto: logger.info(f"  {texto}"))
    if escala not in (2, 4):
        raise RuntimeError(f"Escala no válida: x{escala}. Usa 2 o 4.")
    ejecutable = ejecutable_esrgan()
    _comprobar_modelo(ejecutable, modelo)

    if os.path.splitext(ruta_entrada)[1].lower() in EXTENSIONES_IMAGEN:
        with tempfile.TemporaryDirectory(prefix="aegs_esrgan_") as tmp:
            entrada, salida = os.path.join(tmp, "in"), os.path.join(tmp, "out")
            os.makedirs(entrada)
            os.makedirs(salida)
            nombre = "imagen.png"
            _run([binario("ffmpeg"), "-y", "-i", ruta_entrada, os.path.join(entrada, nombre)], "Preparar imagen")
            estado("Real-ESRGAN: ampliando la imagen…")
            _ejecutar_esrgan(entrada, salida, modelo, escala)
            _run([binario("ffmpeg"), "-y", "-i", os.path.join(salida, nombre), ruta_salida], "Guardar imagen")
        return ruta_salida

    with tempfile.TemporaryDirectory(prefix="aegs_esrgan_") as tmp:
        originales, mejorados, lote_dir = (os.path.join(tmp, n) for n in ("orig", "mejor", "lote"))
        os.makedirs(originales)
        os.makedirs(mejorados)
        fps = _fps(ruta_entrada)
        estado("Real-ESRGAN: extrayendo fotogramas del vídeo…")
        _run([binario("ffmpeg"), "-y", "-i", ruta_entrada, os.path.join(originales, "frame_%08d.png")],
             "Extracción de fotogramas")
        lista = sorted(f for f in os.listdir(originales) if f.lower().endswith(".png"))
        if not lista:
            raise RuntimeError("No se extrajo ningún fotograma del vídeo.")

        for inicio in range(0, len(lista), _LOTE):
            lote = lista[inicio:inicio + _LOTE]
            estado(f"Real-ESRGAN: mejorando con IA… {min(inicio + _LOTE, len(lista))}/{len(lista)} fotogramas")
            for _intento in range(2):
                shutil.rmtree(lote_dir, ignore_errors=True)
                os.makedirs(lote_dir)
                for nombre in lote:
                    shutil.copy2(os.path.join(originales, nombre), os.path.join(lote_dir, nombre))
                _ejecutar_esrgan(lote_dir, mejorados, modelo, escala)
                b_out = _brillo(os.path.join(mejorados, lote[0]))
                b_in = _brillo(os.path.join(originales, lote[0]))
                if b_out is None or b_out >= _NEGRO or (b_in is not None and b_in < _NEGRO):
                    break
            else:
                raise RuntimeError(
                    "Real-ESRGAN devolvió fotogramas en negro (microcorte de la GPU).\n\n"
                    "Cierra otros programas que usen la tarjeta gráfica, prueba con un vídeo más corto "
                    "o vuelve a intentarlo."
                )

        estado(f"Real-ESRGAN: reensamblando el vídeo ({len(lista)} fotogramas)…")
        solo_video = os.path.join(tmp, "solo_video.mp4")
        _run([binario("ffmpeg"), "-y", "-framerate", f"{fps:.6f}", "-i", os.path.join(mejorados, "frame_%08d.png"),
              "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
              "-profile:v", "high", solo_video], "Reensamblado del vídeo")
        estado("Real-ESRGAN: devolviendo el audio original…")
        _run([binario("ffmpeg"), "-y", "-i", solo_video, "-i", ruta_entrada, "-map", "0:v:0", "-map", "1:a:0?",
              "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart",
              "-shortest", ruta_salida], "Unión del audio")
    if not os.path.exists(ruta_salida):
        raise RuntimeError("El vídeo ampliado no se generó.")
    return ruta_salida

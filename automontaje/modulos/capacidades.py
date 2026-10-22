"""SUME DOCBLOCK: inspeccion local de dependencias, sin descargar modelos ni usar red."""
import importlib.util
import json
import os
import shutil
from .utilidades import verificar_ffmpeg
from .superresolucion import ejecutable_esrgan


def _instalado(nombre):
    try:
        return importlib.util.find_spec(nombre) is not None
    except (ImportError, ValueError):
        return False


def informe_capacidades():
    media = verificar_ffmpeg()
    motor = "faster-whisper" if _instalado("faster_whisper") else "openai-whisper" if _instalado("whisper") else None
    try:
        esrgan = ejecutable_esrgan()
        modelos = os.path.join(os.path.dirname(esrgan), "models")
        modelos_disponibles = [n[:-4] for n in os.listdir(modelos)
                              if n.endswith(".bin") and os.path.isfile(os.path.join(modelos, n[:-4] + ".param"))]
    except (OSError, RuntimeError):
        esrgan, modelos_disponibles = None, []
    return {
        "ffmpeg": media,
        "edicion_basica": media["exito"],
        "interfaz": _instalado("customtkinter") and _instalado("tkinter"),
        "transcripcion": motor,
        "subtitulos_del_guion": True,
        "separacion_voz": _instalado("demucs") and _instalado("torch"),
        "real_esrgan": {"ejecutable": esrgan, "modelos": modelos_disponibles},
        "narracion_edge_tts": _instalado("edge_tts"),
        "modelo_ordenes": os.environ.get("AEGS_MODELO", ""),
        "nota": "Dependencias detectadas; GPU, pesos de IA y servicios externos no comprobados.",
    }


def main():
    print(json.dumps(informe_capacidades(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

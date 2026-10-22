# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.0
═══════════════════════════════════════════════════════════
Archivo: modulos/transcripcion.py
Tipo: Lógica → Transcripción de voz (un solo motor para todo el editor)
Dependencias: faster-whisper (preferido) u openai-whisper, ambos opcionales

Entradas:
- Un archivo de audio o vídeo, el idioma y el modelo.

Acciones:
1. Usa faster-whisper si está instalado (ligero, sin PyTorch); si no, openai-whisper.
2. Devuelve los segmentos con sus tiempos y, si se piden, las palabras.

Salidas:
- Lista de Segmento(inicio, fin, texto, palabras).

Antes los subtítulos de un vídeo aceptaban faster-whisper, pero las muletillas y los
subtítulos del automontaje solo openai-whisper; ahora todos pasan por aquí.
═══════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .utilidades import logger

INSTALAR = (
    "No hay motor de transcripción instalado. Instala uno:\n"
    "  pip install faster-whisper            (recomendado: ligero, sin PyTorch)\n"
    '  pip install "aegs-automontaje[subtitulos]"   (openai-whisper; en Python 3.15 no se instala, usa 3.12)'
)


@dataclass
class Segmento:
    inicio: float
    fin: float
    texto: str
    palabras: list = field(default_factory=list)  # [(inicio, fin, palabra)]


def motor_disponible() -> str | None:
    """'faster-whisper', 'openai-whisper' o None."""
    try:
        import faster_whisper  # noqa: F401
        return "faster-whisper"
    except ImportError:
        pass
    try:
        import whisper  # noqa: F401
        return "openai-whisper"
    except ImportError:
        return None


def transcribir(ruta: str, idioma: str = "es", modelo: str = "base", palabras: bool = False) -> list:
    """Transcribe `ruta` con el motor disponible. `palabras=True` añade el tiempo de cada palabra."""
    motor = motor_disponible()
    if motor == "faster-whisper":
        from faster_whisper import WhisperModel

        logger.info(f"  🎙  Transcribiendo con faster-whisper (modelo={modelo})...")
        segmentos, _info = WhisperModel(modelo, device="cpu", compute_type="int8").transcribe(
            ruta, language=idioma, word_timestamps=palabras
        )
        return [
            Segmento(
                float(s.start), float(s.end), s.text.strip(),
                [(float(p.start), float(p.end), p.word.strip()) for p in (s.words or [])] if palabras else [],
            )
            for s in segmentos if s.text and s.text.strip()
        ]
    if motor == "openai-whisper":
        import whisper

        logger.info(f"  🎙  Transcribiendo con openai-whisper (modelo={modelo})...")
        resultado = whisper.load_model(modelo).transcribe(ruta, language=idioma, word_timestamps=palabras)
        return [
            Segmento(
                float(s["start"]), float(s["end"]), s["text"].strip(),
                [(float(p["start"]), float(p["end"]), p["word"].strip()) for p in s.get("words", [])] if palabras else [],
            )
            for s in resultado.get("segments", []) if s.get("text", "").strip()
        ]
    raise RuntimeError(INSTALAR)

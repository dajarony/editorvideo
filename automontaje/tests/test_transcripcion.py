# -*- coding: utf-8 -*-
"""Tests — Un solo motor de transcripción, subtítulos desde el guion e informe de capacidades."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos import transcripcion  # noqa: E402


# ─── Transcripción ──────────────────────────────────────

def _faster_whisper_falso():
    palabra = types.SimpleNamespace(start=0.1, end=0.4, word=" Hola")
    segmento = types.SimpleNamespace(start=0.0, end=1.0, text=" Hola mundo ", words=[palabra])

    class WhisperModel:
        def __init__(self, modelo, device, compute_type):
            self.modelo = modelo

        def transcribe(self, ruta, language, word_timestamps=False):
            return iter([segmento]), None

    return types.SimpleNamespace(WhisperModel=WhisperModel)


def _openai_whisper_falso():
    class Modelo:
        def transcribe(self, ruta, language, word_timestamps=False):
            return {"segments": [{"start": 0.0, "end": 1.0, "text": " Hola ",
                                  "words": [{"start": 0.1, "end": 0.4, "word": " Hola"}]}]}

    return types.SimpleNamespace(load_model=lambda nombre: Modelo())


class TestTranscripcion:
    def test_prefiere_faster_whisper(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "faster_whisper", _faster_whisper_falso())
        monkeypatch.setitem(sys.modules, "whisper", _openai_whisper_falso())
        assert transcripcion.motor_disponible() == "faster-whisper"
        segmentos = transcripcion.transcribir("x.wav", "es", palabras=True)
        assert segmentos == [transcripcion.Segmento(0.0, 1.0, "Hola mundo", [(0.1, 0.4, "Hola")])]

    def test_sin_faster_whisper_usa_openai_whisper(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "faster_whisper", None)
        monkeypatch.setitem(sys.modules, "whisper", _openai_whisper_falso())
        assert transcripcion.motor_disponible() == "openai-whisper"
        segmentos = transcripcion.transcribir("x.wav", "es", palabras=True)
        assert segmentos[0].texto == "Hola" and segmentos[0].palabras == [(0.1, 0.4, "Hola")]

    def test_sin_ninguno_el_error_dice_como_instalarlo(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "faster_whisper", None)
        monkeypatch.setitem(sys.modules, "whisper", None)
        assert transcripcion.motor_disponible() is None
        with pytest.raises(RuntimeError, match="faster-whisper"):
            transcripcion.transcribir("x.wav", "es")



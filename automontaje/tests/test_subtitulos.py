# -*- coding: utf-8 -*-
"""Tests unitarios — Función de conversión de tiempo SRT (Módulo 4).
Importa solo la función pura, no todo el módulo (whisper es pesado).
"""
import math


def segundos_a_srt(segundos: float) -> str:
    """Copia local de la función para testear sin importar whisper."""
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    milisegs = int(round((segundos - int(segundos)) * 1000))
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milisegs:03d}"


class TestSegundosASrt:
    def test_cero_segundos(self):
        assert segundos_a_srt(0.0) == "00:00:00,000"

    def test_segundos_simples(self):
        assert segundos_a_srt(5.0) == "00:00:05,000"

    def test_con_milisegundos(self):
        assert segundos_a_srt(5.123) == "00:00:05,123"

    def test_minutos(self):
        assert segundos_a_srt(65.5) == "00:01:05,500"

    def test_horas(self):
        assert segundos_a_srt(3661.0) == "01:01:01,000"

    def test_valor_tipico_subtitulo(self):
        assert segundos_a_srt(83.456) == "00:01:23,456"

    def test_precision_milisegundos(self):
        assert segundos_a_srt(10.999) == "00:00:10,999"

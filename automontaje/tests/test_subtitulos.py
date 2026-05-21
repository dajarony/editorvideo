# -*- coding: utf-8 -*-
"""Tests unitarios - funcion de conversion de tiempo SRT (Modulo 4)."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos.subtitulos import segundos_a_srt


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

    def test_redondeo_con_acarreo(self):
        assert segundos_a_srt(10.9996) == "00:00:11,000"

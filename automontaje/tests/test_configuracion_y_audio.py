# -*- coding: utf-8 -*-
"""Tests unitarios — Módulo de Configuración y Módulo 2: Mezclador."""
import os
import sys
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from configuracion import (
    VOCES_EDGE_CONOCIDAS, ARCHIVO_PROYECTO, CARPETA_OUTPUT,
    FADE_DUCK_MS, FADE_TRANSICION_SEG
)
from modulos.mezclador_audio import lineal_a_db


class TestConfiguracion:
    def test_voces_no_vacia(self):
        assert len(VOCES_EDGE_CONOCIDAS) > 0

    def test_voz_alvaro_existe(self):
        assert "es-ES-AlvaroNeural" in VOCES_EDGE_CONOCIDAS

    def test_archivo_proyecto_es_json(self):
        assert ARCHIVO_PROYECTO.endswith(".json")

    def test_carpeta_output_definida(self):
        assert CARPETA_OUTPUT == "output"

    def test_fade_duck_positivo(self):
        assert FADE_DUCK_MS > 0

    def test_fade_transicion_positivo(self):
        assert FADE_TRANSICION_SEG > 0


class TestLinealADb:
    def test_volumen_maximo(self):
        assert lineal_a_db(1.0) == 0.0

    def test_volumen_medio(self):
        resultado = lineal_a_db(0.5)
        esperado = 20 * math.log10(0.5)
        assert abs(resultado - esperado) < 0.01

    def test_volumen_cero_es_silencio(self):
        assert lineal_a_db(0.0) == -120.0

    def test_volumen_muy_bajo_es_silencio(self):
        assert lineal_a_db(0.001) == -120.0

    def test_volumen_base_tipico(self):
        # 0.30 → aprox -10.46 dB
        resultado = lineal_a_db(0.30)
        assert -11 < resultado < -10

    def test_volumen_duck_tipico(self):
        # 0.08 → aprox -21.94 dB
        resultado = lineal_a_db(0.08)
        assert -23 < resultado < -21

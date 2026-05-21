# -*- coding: utf-8 -*-
"""Tests unitarios - Modulo de mejoras visuales."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos.mejoras import (
    NIVELES_MEJORA,
    ESTILOS_COLOR,
    convertir_vertical_9_16,
    separacion_voz_ia_disponible,
    aislar_voz_con_ia,
)


class TestMejoraReal:
    def test_mejora_real_no_usa_denoise_agresivo(self):
        filtros = ",".join(NIVELES_MEJORA.values()).lower()
        assert "hqdn3d" not in filtros

    def test_mejora_real_escala_x2_con_lanczos(self):
        for filtro in NIVELES_MEJORA.values():
            assert "scale=iw*2:ih*2:flags=lanczos" in filtro

    def test_estilo_natural_claro_existe(self):
        assert "natural_claro" in ESTILOS_COLOR

    def test_convertir_vertical_funcion_disponible(self):
        assert callable(convertir_vertical_9_16)

    def test_separacion_voz_ia_funciones_disponibles(self):
        assert callable(separacion_voz_ia_disponible)
        assert callable(aislar_voz_con_ia)

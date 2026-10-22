# -*- coding: utf-8 -*-
"""Tests — Mapa de tiempos: dónde acaba cada segundo del vídeo original tras los cortes."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos.tiempos import MapaTiempos  # noqa: E402


class TestMapaTiempos:
    def test_sin_cortes_cada_segundo_queda_igual(self):
        mapa = MapaTiempos.identidad(20.0)
        assert mapa.llevar(12.0) == (12.0, False)

    def test_tras_quitar_un_tramo_lo_de_despues_se_adelanta(self):
        # Se conserva [0, 7] y [9, 20]: el segundo 12 original pasa a ser el 10.
        mapa = MapaTiempos.identidad(20.0).tras_conservar([(0.0, 7.0), (9.0, 20.0)])
        assert mapa.llevar(5.0) == (5.0, False)
        assert mapa.llevar(12.0) == (10.0, False)
        assert mapa.duracion == pytest.approx(18.0)

    def test_un_momento_que_se_ha_quitado_salta_al_siguiente_que_queda(self):
        mapa = MapaTiempos.identidad(20.0).tras_conservar([(0.0, 7.0), (9.0, 20.0)])
        assert mapa.llevar(8.0) == (7.0, True)

    def test_dos_cortes_seguidos_se_componen(self):
        # Primero se quita [7, 9] del original; después se quita [2, 3] del resultado.
        mapa = (
            MapaTiempos.identidad(20.0)
            .tras_conservar([(0.0, 7.0), (9.0, 20.0)])
            .tras_conservar([(0.0, 2.0), (3.0, 18.0)])
        )
        assert mapa.llevar(1.0) == (1.0, False)
        assert mapa.llevar(5.0) == (4.0, False)
        assert mapa.llevar(12.0) == (9.0, False)
        assert mapa.llevar(2.5) == (2.0, True)
        assert mapa.duracion == pytest.approx(17.0)

    def test_despues_del_final_se_queda_en_el_final(self):
        mapa = MapaTiempos.identidad(10.0).tras_conservar([(0.0, 4.0)])
        assert mapa.llevar(8.0) == (4.0, True)

    def test_un_tramo_del_original_se_lleva_entero(self):
        mapa = MapaTiempos.identidad(20.0).tras_conservar([(0.0, 7.0), (9.0, 20.0)])
        assert mapa.llevar_tramo(10.0, 12.0) == (8.0, 10.0)
        # Un tramo que se quitó entero ya no existe en el resultado.
        assert mapa.llevar_tramo(7.5, 8.5) is None

    def test_un_extracto_empieza_en_cero(self):
        mapa = MapaTiempos.extracto(10.0, 16.0)
        assert mapa.llevar(12.0) == (2.0, False)
        assert mapa.llevar(4.0) == (0.0, True)
        assert mapa.duracion == pytest.approx(6.0)

# -*- coding: utf-8 -*-
"""Tests unitarios — Módulo 3: Montador de Vídeo (Timeline + Filtros)."""
import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos.montador_video import calcular_timeline, _construir_filtro_video


class TestCalcularTimeline:
    def test_falla_sin_duraciones(self, proyecto_temp):
        """Sin narracion_duraciones.json debe lanzar FileNotFoundError."""
        import pytest
        with pytest.raises(FileNotFoundError):
            calcular_timeline(proyecto_temp["ruta"], proyecto_temp["datos"])

    def test_timeline_correcto_con_duraciones(self, proyecto_temp, duraciones_fake):
        """Con duraciones fake, el timeline debe calcularse correctamente."""
        timeline = calcular_timeline(proyecto_temp["ruta"], proyecto_temp["datos"])

        assert "duracion_total_seg" in timeline
        assert "escenas" in timeline
        assert len(timeline["escenas"]) == 2

        # Verificar primera escena
        e1 = timeline["escenas"][0]
        assert e1["id"] == "escena_test_01"
        assert e1["inicio_seg"] == 0.0
        # Duración = pausa_antes(1.0) + voz(4.5) + pausa_despues(1.0) = 6.5
        assert abs(e1["duracion_necesaria"] - 6.5) < 0.01

        # Verificar segunda escena empieza donde termina la primera
        e2 = timeline["escenas"][1]
        assert e2["inicio_seg"] == e1["fin_seg"]

    def test_timeline_se_guarda_en_disco(self, proyecto_temp, duraciones_fake):
        calcular_timeline(proyecto_temp["ruta"], proyecto_temp["datos"])
        ruta_timeline = os.path.join(proyecto_temp["ruta"], "output", "timeline.json")
        assert os.path.exists(ruta_timeline)
        with open(ruta_timeline, "r") as f:
            data = json.load(f)
        assert data["duracion_total_seg"] > 0

    def test_duracion_total_es_suma_escenas(self, proyecto_temp, duraciones_fake):
        timeline = calcular_timeline(proyecto_temp["ruta"], proyecto_temp["datos"])
        suma = sum(e["duracion_necesaria"] for e in timeline["escenas"])
        assert abs(timeline["duracion_total_seg"] - suma) < 0.01


class TestConstruirFiltroVideo:
    def _escena_base(self, trans_in="cut", trans_out="cut"):
        return {
            "id": "test", "duracion_necesaria": 10.0,
            "inicio_trim": 0, "clip_usado": "c.mp4",
            "clip_recortado": False, "clip_extendido": False,
            "transicion_entrada": trans_in,
            "transicion_salida": trans_out
        }

    def test_filtro_basico_contiene_scale_y_fps(self):
        filtro = _construir_filtro_video(self._escena_base(), "1920x1080", 30, 1, 0)
        assert "scale=1920:1080" in filtro
        assert "fps=30" in filtro

    def test_filtro_contiene_tpad(self):
        filtro = _construir_filtro_video(self._escena_base(), "1920x1080", 30, 1, 0)
        assert "tpad" in filtro

    def test_fade_from_black_agrega_fade_in(self):
        escena = self._escena_base(trans_in="fade_from_black")
        filtro = _construir_filtro_video(escena, "1920x1080", 30, 1, 0)
        assert "fade=t=in" in filtro

    def test_fade_to_black_agrega_fade_out(self):
        escena = self._escena_base(trans_out="fade_to_black")
        filtro = _construir_filtro_video(escena, "1920x1080", 30, 1, 0)
        assert "fade=t=out" in filtro

    def test_crossfade_entrada_agrega_fade_in(self):
        escena = self._escena_base(trans_in="crossfade")
        filtro = _construir_filtro_video(escena, "1920x1080", 30, 2, 1)
        assert "fade=t=in" in filtro

    def test_crossfade_salida_agrega_fade_out(self):
        escena = self._escena_base(trans_out="crossfade")
        filtro = _construir_filtro_video(escena, "1920x1080", 30, 2, 0)
        assert "fade=t=out" in filtro

    def test_cut_no_agrega_fades(self):
        filtro = _construir_filtro_video(self._escena_base(), "1920x1080", 30, 1, 0)
        assert "fade=t=in" not in filtro
        assert "fade=t=out" not in filtro

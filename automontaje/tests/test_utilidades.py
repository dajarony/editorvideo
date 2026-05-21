# -*- coding: utf-8 -*-
"""Tests unitarios - Modulo de Utilidades."""
import os
import sys
import logging
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos.utilidades import (
    configurar_logger, activar_log_archivo, obtener_info_media,
    limpiar_carpeta_temporal, ruta_segura_proyecto, validar_id_escena,
    validar_resolucion, normalizar_fps, validar_velocidad_tts,
    validar_fuente_subtitulos
)


class TestLogger:
    def test_logger_se_crea_correctamente(self):
        log = configurar_logger()
        assert log is not None
        assert log.name == "AEGS"
        assert log.level == logging.DEBUG

    def test_logger_tiene_handler_consola(self):
        log = configurar_logger()
        tiene_stream = any(isinstance(h, logging.StreamHandler) for h in log.handlers)
        assert tiene_stream

    def test_activar_log_archivo_crea_directorio(self, tmp_path):
        activar_log_archivo(str(tmp_path), "logs_test", "test.log")
        assert (tmp_path / "logs_test").is_dir()
        assert (tmp_path / "logs_test" / "test.log").exists()


class TestObtenerInfoMedia:
    def test_archivo_inexistente_retorna_error(self):
        resultado = obtener_info_media("/ruta/falsa/archivo.mp4")
        assert "error" in resultado
        assert "no encontrado" in resultado["error"].lower() or "not found" in resultado["error"].lower()

    def test_retorna_dict_con_claves_correctas_o_error(self, tmp_path):
        fake = tmp_path / "fake.mp4"
        fake.write_bytes(b"\x00" * 100)
        resultado = obtener_info_media(str(fake))
        assert isinstance(resultado, dict)
        if "error" not in resultado:
            assert "duracion" in resultado
            assert "resolucion" in resultado
            assert "codec" in resultado


class TestLimpiarCarpetaTemporal:
    def test_limpia_carpeta_existente(self, tmp_path):
        temp = tmp_path / "output" / "temp_clips"
        temp.mkdir(parents=True)
        (temp / "clip.mp4").write_text("fake")
        limpiar_carpeta_temporal(str(tmp_path), "output/temp_clips")
        assert not temp.exists()

    def test_no_falla_si_carpeta_no_existe(self, tmp_path):
        limpiar_carpeta_temporal(str(tmp_path), "inexistente")


class TestValidacionesSeguridad:
    def test_ruta_segura_permite_relativa_dentro_del_proyecto(self, tmp_path):
        ruta = ruta_segura_proyecto(str(tmp_path), "clips/video.mp4")
        assert os.path.commonpath([str(tmp_path), ruta]) == str(tmp_path)

    def test_ruta_segura_rechaza_escape(self, tmp_path):
        with pytest.raises(ValueError):
            ruta_segura_proyecto(str(tmp_path), "../secreto.mp4")

    def test_id_escena_seguro(self):
        assert validar_id_escena("escena_01-ok") is True
        assert validar_id_escena("../mal") is False

    def test_resolucion_segura(self):
        assert validar_resolucion("1920x1080") is True
        assert validar_resolucion("1920:1080,evil") is False

    def test_fps_seguro(self):
        assert normalizar_fps(30) == 30

    def test_velocidad_tts_segura(self):
        assert validar_velocidad_tts("-5%") is True
        assert validar_velocidad_tts("-5%;bad") is False

    def test_fuente_subtitulos_segura(self):
        assert validar_fuente_subtitulos("Arial Bold") is True
        assert validar_fuente_subtitulos("Arial,PrimaryColour=&H0") is False

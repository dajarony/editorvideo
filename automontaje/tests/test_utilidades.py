# -*- coding: utf-8 -*-
"""Tests unitarios — Módulo de Utilidades."""
import os
import sys
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos.utilidades import configurar_logger, activar_log_archivo, obtener_info_media, limpiar_carpeta_temporal


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
        # Archivo vacío — ffprobe debería fallar pero no crashear
        fake = tmp_path / "fake.mp4"
        fake.write_bytes(b"\x00" * 100)
        resultado = obtener_info_media(str(fake))
        # Puede ser error (archivo inválido) o dict con claves
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
        # No debe lanzar excepción
        limpiar_carpeta_temporal(str(tmp_path), "inexistente")

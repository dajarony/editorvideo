# -*- coding: utf-8 -*-
"""Tests — Entorno reproducible: dependencias, tests de internet, FFmpeg configurable y Whisper opcional."""
import json
import os
import subprocess
import sys
import tomllib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos import subtitulos, utilidades  # noqa: E402

RAIZ = os.path.join(os.path.dirname(__file__), "..")


def _pyproject():
    with open(os.path.join(RAIZ, "pyproject.toml"), "rb") as f:
        return tomllib.load(f)


class TestDependencias:
    def test_whisper_no_es_obligatorio(self):
        obligatorias = " ".join(_pyproject()["project"]["dependencies"]).lower()
        assert "whisper" not in obligatorias
        assert "torch" not in obligatorias

    def test_whisper_esta_en_el_extra_subtitulos(self):
        extras = _pyproject()["project"]["optional-dependencies"]
        assert any("openai-whisper" in dep for dep in extras["subtitulos"])
        assert any(dep.startswith("pytest") for dep in extras["dev"])


class TestTestsDeInternet:
    def test_edge_tts_real_se_omite_sin_la_variable(self, tmp_path):
        """Sin AEGS_TEST_INTERNET los tests de Edge TTS real no se ejecutan y lo dicen."""
        entorno = {k: v for k, v in os.environ.items() if k != "AEGS_TEST_INTERNET"}
        res = subprocess.run(
            [sys.executable, "-m", "pytest", os.path.join(RAIZ, "tests", "test_narracion.py"),
             "-q", "-rs", "-p", "no:cacheprovider", f"--basetemp={tmp_path / 'pt'}"],
            cwd=RAIZ, env=entorno, capture_output=True, text=True,
        )
        assert res.returncode == 0, res.stdout + res.stderr
        assert "3 skipped" in res.stdout
        assert "AEGS_TEST_INTERNET" in res.stdout


class TestBinariosFFmpeg:
    def test_sin_variables_usa_el_path(self, monkeypatch):
        monkeypatch.delenv("AEGS_FFMPEG", raising=False)
        monkeypatch.delenv("AEGS_FFPROBE", raising=False)
        assert utilidades.binario("ffmpeg") == "ffmpeg"
        assert utilidades.binario("ffprobe") == "ffprobe"

    def test_la_variable_tiene_prioridad(self, monkeypatch):
        monkeypatch.setenv("AEGS_FFMPEG", sys.executable)
        monkeypatch.setenv("AEGS_FFPROBE", sys.executable)
        assert utilidades.binario("ffmpeg") == sys.executable
        assert utilidades.binario("ffprobe") == sys.executable

    def test_ruta_inexistente_da_error_claro(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AEGS_FFMPEG", str(tmp_path / "no-existe"))
        with pytest.raises(FileNotFoundError, match="AEGS_FFMPEG"):
            utilidades.binario("ffmpeg")

    def test_binario_desconocido_se_rechaza(self):
        with pytest.raises(ValueError):
            utilidades.binario("rm")

    def test_ffprobe_de_info_media_usa_la_variable(self, monkeypatch, tmp_path):
        archivo = tmp_path / "x.mp4"
        archivo.write_bytes(b"0")
        monkeypatch.setenv("AEGS_FFPROBE", sys.executable)
        llamadas = []

        def falso_run(comando, **kwargs):
            llamadas.append(comando)
            return subprocess.CompletedProcess(comando, 0, stdout=json.dumps({"format": {"duration": "1.5"}, "streams": []}), stderr="")

        monkeypatch.setattr(utilidades.subprocess, "run", falso_run)
        assert utilidades.obtener_info_media(str(archivo))["duracion"] == 1.5
        assert llamadas[0][0] == sys.executable

    def test_ningun_modulo_llama_a_ffmpeg_por_nombre(self):
        """Todas las llamadas pasan por utilidades.binario()."""
        for nombre in os.listdir(os.path.join(RAIZ, "modulos")):
            if not nombre.endswith(".py") or nombre == "utilidades.py":
                continue
            with open(os.path.join(RAIZ, "modulos", nombre), encoding="utf-8") as f:
                codigo = f.read()
            for literal in ('"ffmpeg",', '"ffprobe",', "['ffmpeg',", "['ffprobe',"):
                assert literal not in codigo, f"{nombre} llama a {literal} sin utilidades.binario()"

    def test_pydub_usa_los_mismos_binarios(self, monkeypatch):
        import pydub.utils
        from pydub import AudioSegment

        monkeypatch.setattr(AudioSegment, "converter", AudioSegment.converter)
        monkeypatch.setattr(pydub.utils, "get_prober_name", pydub.utils.get_prober_name)
        monkeypatch.setenv("AEGS_FFMPEG", sys.executable)
        monkeypatch.setenv("AEGS_FFPROBE", sys.executable)
        utilidades.preparar_pydub()
        assert AudioSegment.converter == sys.executable
        assert pydub.utils.get_prober_name() == sys.executable


class TestWhisperOpcional:
    def test_sin_whisper_el_error_dice_como_instalarlo(self, monkeypatch, tmp_path):
        salida = tmp_path / "output"
        salida.mkdir()
        (salida / "timeline.json").write_text(json.dumps({"escenas": []}), encoding="utf-8")
        (salida / "narracion_duraciones.json").write_text("{}", encoding="utf-8")
        monkeypatch.setitem(sys.modules, "whisper", None)
        res = subtitulos.procesar_subtitulos(str(tmp_path), {"subtitulos": {"generar": True}, "escenas": []})
        assert res["exito"] is False
        assert 'pip install "automontaje[subtitulos]"' in res["error"]

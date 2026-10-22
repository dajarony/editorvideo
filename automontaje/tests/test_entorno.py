# -*- coding: utf-8 -*-
"""Tests — Entorno reproducible: dependencias, tests de internet, FFmpeg configurable y Whisper opcional."""
import json
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos import subtitulos, utilidades  # noqa: E402

RAIZ = os.path.join(os.path.dirname(__file__), "..")


def _pyproject():
    tomllib = pytest.importorskip("tomllib")  # Python 3.11+; en 3.10 solo se omiten estos tests
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
        assert "4 skipped" in res.stdout
        assert "AEGS_TEST_INTERNET" in res.stdout

    def test_ningun_test_de_narracion_sin_marca_llama_a_edge_tts(self, tmp_path):
        """generar_audio_escena llama a edge_tts.Communicate(...).save() sin mock: es Edge TTS real."""
        entorno = {k: v for k, v in os.environ.items() if k != "AEGS_TEST_INTERNET"}
        res = subprocess.run(
            [sys.executable, "-m", "pytest", os.path.join(RAIZ, "tests", "test_narracion.py"),
             "--collect-only", "-q", "-m", "not internet", "-p", "no:cacheprovider",
             f"--basetemp={tmp_path / 'pt'}"],
            cwd=RAIZ, env=entorno, capture_output=True, text=True,
        )
        assert res.returncode in (0, 5), res.stdout + res.stderr  # 5 = ningún test sin la marca
        assert "test_genera_audio_sin_ffprobe_falla_graciosamente" not in res.stdout, res.stdout


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

    def test_ruta_relativa_se_devuelve_absoluta(self, monkeypatch, tmp_path):
        (tmp_path / "ffmpeg-local").write_bytes(b"")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AEGS_FFMPEG", "ffmpeg-local")
        assert utilidades.binario("ffmpeg") == str(tmp_path / "ffmpeg-local")

    def test_ruta_relativa_funciona_aunque_ffmpeg_corra_en_otra_carpeta(self, monkeypatch, tmp_path):
        from modulos import montador_video
        (tmp_path / "herramientas").mkdir()
        (tmp_path / "herramientas" / "ffmpeg").write_bytes(b"")
        proyecto = tmp_path / "proyecto"
        (proyecto / montador_video.CARPETA_TEMP).mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AEGS_FFMPEG", os.path.join("herramientas", "ffmpeg"))
        vistos = []

        def falso_run(comando, **kwargs):
            base = kwargs.get("cwd") or os.getcwd()
            vistos.append(os.path.isfile(os.path.join(base, comando[0])))
            return subprocess.CompletedProcess(comando, 0, stdout="", stderr="")

        monkeypatch.setattr(montador_video.subprocess, "run", falso_run)
        montador_video._ensamblar_concat_demuxer(str(proyecto), [])
        assert vistos == [True]

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
        """Todas las llamadas pasan por utilidades.binario(): ningún 'ffmpeg'/'ffprobe' como
        elemento de una lista de comando ni como argumento de shutil.which()."""
        patron = re.compile(r"""(?:[\[,]\s*|which\(\s*)["'](?:ffmpeg|ffprobe)["']""")
        archivos = [os.path.join(RAIZ, "modulos", n) for n in os.listdir(os.path.join(RAIZ, "modulos"))
                    if n.endswith(".py") and n != "utilidades.py"] + [os.path.join(RAIZ, "main.py")]
        for archivo in archivos:
            with open(archivo, encoding="utf-8") as f:
                codigo = re.sub(r"""binario\(["'](?:ffmpeg|ffprobe)["']\)""", "", f.read())
            encontrados = patron.findall(codigo)
            assert not encontrados, f"{os.path.basename(archivo)} llama a ffmpeg/ffprobe sin binario(): {encontrados}"

    def test_info_media_con_ruta_mala_devuelve_error(self, monkeypatch, tmp_path):
        """Con AEGS_FFPROBE mal configurada, obtener_info_media devuelve su dict de error, no una excepción."""
        archivo = tmp_path / "x.mp4"
        archivo.write_bytes(b"0")
        monkeypatch.setenv("AEGS_FFPROBE", str(tmp_path / "no-existe"))
        resultado = utilidades.obtener_info_media(str(archivo))
        assert "AEGS_FFPROBE" in resultado["error"]

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

    def test_pydub_sin_variables_no_cambia(self, monkeypatch):
        """Sin AEGS_FFMPEG/AEGS_FFPROBE, la mezcla sigue igual que antes."""
        import pydub.utils
        from pydub import AudioSegment

        monkeypatch.delenv("AEGS_FFMPEG", raising=False)
        monkeypatch.delenv("AEGS_FFPROBE", raising=False)
        antes = (AudioSegment.converter, pydub.utils.get_prober_name)
        utilidades.preparar_pydub()
        assert (AudioSegment.converter, pydub.utils.get_prober_name) == antes


class TestWhisperOpcional:
    def test_sin_whisper_el_error_dice_como_instalarlo(self, monkeypatch, tmp_path):
        salida = tmp_path / "output"
        salida.mkdir()
        (salida / "timeline.json").write_text(json.dumps({"escenas": []}), encoding="utf-8")
        (salida / "narracion_duraciones.json").write_text("{}", encoding="utf-8")
        monkeypatch.setitem(sys.modules, "whisper", None)
        res = subtitulos.procesar_subtitulos(str(tmp_path), {"subtitulos": {"generar": True, "modo": "transcripcion"}, "escenas": []})
        assert res["exito"] is False
        assert 'pip install "automontaje[subtitulos]"' in res["error"]

# -*- coding: utf-8 -*-
"""Tests — Integración "narración primero" con Aura Motion Studio.

Voz sintética offline, `--solo-narracion` y montaje de duración exacta (`--duracion-estricta`).
Los tests que montan vídeo de verdad necesitan FFmpeg (PATH o AEGS_FFMPEG/AEGS_FFPROBE).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos import narracion, utilidades, validador  # noqa: E402

RAIZ = os.path.join(os.path.dirname(__file__), "..")
MAIN = os.path.join(RAIZ, "main.py")
FPS = 30


def _sha(ruta):
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture
def ffmpeg():
    """Rutas de ffmpeg y ffprobe, o se omite el test con su motivo."""
    try:
        rutas = {n: shutil.which(utilidades.binario(n)) for n in ("ffmpeg", "ffprobe")}
    except FileNotFoundError as e:
        pytest.skip(f"necesita FFmpeg: {e}")
    if not all(rutas.values()):
        pytest.skip("necesita FFmpeg y FFprobe (PATH o AEGS_FFMPEG/AEGS_FFPROBE)")
    return rutas


def _proyecto(tmp_path, escenas, estricta=False):
    (tmp_path / "clips").mkdir(exist_ok=True)
    datos = {
        "titulo": "Prueba Aura",
        "idioma": "es",
        "fps": FPS,
        "resolucion": "320x240",
        "narrador": {"motor": "sintetico", "velocidad": "+0%"},
        "escenas": escenas,
    }
    if estricta:
        datos["montaje"] = {"duracion_estricta": True}
    (tmp_path / "proyecto.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _clip(ffmpeg, ruta, segundos):
    subprocess.run(
        [ffmpeg["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=320x240:rate={FPS}",
         "-frames:v", str(round(segundos * FPS)), "-pix_fmt", "yuv420p", str(ruta)],
        check=True,
    )


def _aegs(proyecto, *flags):
    return subprocess.run([sys.executable, MAIN, str(proyecto), *flags], capture_output=True, text=True)


def _duracion(ffmpeg, ruta):
    salida = subprocess.run(
        [ffmpeg["ffprobe"], "-v", "error", "-show_entries", "format=duration", "-of", "json", str(ruta)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(salida)["format"]["duration"])


ESCENAS = [
    {"id": "hola", "clip": "clips/hola.mp4", "texto_narracion": "Hola, soy Aura y vengo a saludarte."},
    {"id": "adios", "clip": "clips/adios.mp4", "texto_narracion": "Hasta pronto."},
]


class TestVozSintetica:
    def test_es_determinista_y_crece_con_el_texto(self, tmp_path, monkeypatch):
        def sin_red(*args, **kwargs):
            raise AssertionError("la voz sintética no debe usar Edge TTS")

        monkeypatch.setattr(narracion.edge_tts, "Communicate", sin_red)
        corto, largo, otra = (tmp_path / n for n in ("corto.wav", "largo.wav", "otra.wav"))
        d_corto = narracion.generar_audio_sintetico("Hola.", "+0%", str(corto))
        d_largo = narracion.generar_audio_sintetico("Hola, esta frase es bastante más larga.", "+0%", str(largo))
        narracion.generar_audio_sintetico("Hola.", "+0%", str(otra))
        assert 0 < d_corto < d_largo
        assert _sha(corto) == _sha(otra)

    def test_la_velocidad_cambia_la_duracion(self, tmp_path):
        normal = narracion.generar_audio_sintetico("Una frase de prueba.", "+0%", str(tmp_path / "n.wav"))
        rapida = narracion.generar_audio_sintetico("Una frase de prueba.", "+50%", str(tmp_path / "r.wav"))
        assert rapida < normal

    def test_narracion_del_proyecto_escribe_duraciones_sin_red(self, tmp_path, monkeypatch):
        monkeypatch.setattr(narracion.edge_tts, "Communicate", lambda *a, **k: pytest.fail("usó Edge TTS"))
        proyecto = _proyecto(tmp_path, ESCENAS)
        datos = json.loads((proyecto / "proyecto.json").read_text(encoding="utf-8"))
        import asyncio
        res = asyncio.run(narracion.ejecutar_narracion_concurrente(str(proyecto), datos))
        assert res["exito"], res
        duraciones = json.loads((proyecto / "output" / "narracion_duraciones.json").read_text(encoding="utf-8"))
        assert set(duraciones) == {"hola", "adios"}
        assert all(d["duracion_real_seg"] > 0 and d["archivo"].endswith(".wav") for d in duraciones.values())


class TestValidacionEstricta:
    def test_motor_desconocido_se_rechaza(self, tmp_path):
        proyecto = _proyecto(tmp_path, ESCENAS)
        datos = json.loads((proyecto / "proyecto.json").read_text(encoding="utf-8"))
        datos["narrador"]["motor"] = "otro"
        (proyecto / "proyecto.json").write_text(json.dumps(datos), encoding="utf-8")
        res = validador.inicializar_validador(str(proyecto))
        assert any("motor" in e for e in res["errores"]), res["errores"]

    def test_duracion_estricta_rechaza_transiciones_que_no_son_cut(self, tmp_path):
        escenas = [dict(ESCENAS[0], transicion_salida="crossfade"), dict(ESCENAS[1])]
        proyecto = _proyecto(tmp_path, escenas, estricta=True)
        for escena in escenas:
            (proyecto / escena["clip"]).write_bytes(b"")
        res = validador.inicializar_validador(str(proyecto))
        assert any("con montaje.duracion_estricta solo se admite" in e and "hola" in e for e in res["errores"]), res["errores"]

    def test_sin_duracion_estricta_crossfade_sigue_valido(self, tmp_path):
        escenas = [dict(ESCENAS[0], transicion_salida="crossfade"), dict(ESCENAS[1])]
        proyecto = _proyecto(tmp_path, escenas, estricta=False)
        for escena in escenas:
            (proyecto / escena["clip"]).write_bytes(b"")
        res = validador.inicializar_validador(str(proyecto))
        assert not any("con montaje.duracion_estricta solo se admite" in e for e in res["errores"]), res["errores"]


class TestFlujoNarracionPrimero:
    def test_solo_narracion_mide_y_se_detiene(self, tmp_path, ffmpeg):
        proyecto = _proyecto(tmp_path, ESCENAS)
        for escena in ESCENAS:
            _clip(ffmpeg, proyecto / escena["clip"], 1)
        res = _aegs(proyecto, "--solo-narracion")
        assert res.returncode == 0, res.stdout + res.stderr
        duraciones = json.loads((proyecto / "output" / "narracion_duraciones.json").read_text(encoding="utf-8"))
        assert set(duraciones) == {"hola", "adios"}
        assert not (proyecto / "output" / "video_final.mp4").exists()

    def _narrar_y_cortar_clips(self, tmp_path, ffmpeg, sobra_seg=0.0):
        proyecto = _proyecto(tmp_path, ESCENAS, estricta=True)
        for escena in ESCENAS:
            _clip(ffmpeg, proyecto / escena["clip"], 1)  # provisional, solo para validar
        assert _aegs(proyecto, "--solo-narracion").returncode == 0
        duraciones = json.loads((proyecto / "output" / "narracion_duraciones.json").read_text(encoding="utf-8"))
        for i, escena in enumerate(ESCENAS):
            extra = sobra_seg if i == 0 else 0.0
            _clip(ffmpeg, proyecto / escena["clip"], duraciones[escena["id"]]["duracion_real_seg"] + extra)
        return proyecto, duraciones

    def test_clips_exactos_dan_la_duracion_total(self, tmp_path, ffmpeg):
        proyecto, duraciones = self._narrar_y_cortar_clips(tmp_path, ffmpeg)
        res = _aegs(proyecto, "--skip-tts", "--skip-subs")
        assert res.returncode == 0, res.stdout + res.stderr
        total = sum(d["duracion_real_seg"] for d in duraciones.values())
        assert abs(_duracion(ffmpeg, proyecto / "output" / "video_final.mp4") - total) <= 1.5 / FPS

    @pytest.mark.parametrize("sobra", [1.0, -0.5])
    def test_clip_que_no_encaja_falla_sin_recortar_ni_congelar(self, tmp_path, ffmpeg, sobra):
        proyecto, duraciones = self._narrar_y_cortar_clips(tmp_path, ffmpeg, sobra_seg=sobra)
        res = _aegs(proyecto, "--skip-tts", "--skip-subs")
        salida = res.stdout + res.stderr
        assert res.returncode != 0
        assert "hola" in salida and "duración estricta" in salida, salida
        assert not (proyecto / "output" / "video_final.mp4").exists()

    def test_flag_de_cli_activa_el_modo_estricto(self, tmp_path, ffmpeg):
        proyecto = _proyecto(tmp_path, ESCENAS)  # sin "montaje" en el JSON
        for escena in ESCENAS:
            _clip(ffmpeg, proyecto / escena["clip"], 1)
        assert _aegs(proyecto, "--solo-narracion").returncode == 0
        res = _aegs(proyecto, "--skip-tts", "--skip-subs", "--duracion-estricta")
        assert res.returncode != 0
        assert "duración estricta" in res.stdout + res.stderr

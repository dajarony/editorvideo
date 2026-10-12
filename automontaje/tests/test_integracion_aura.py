# -*- coding: utf-8 -*-
"""Tests — Integración "narración primero" con Aura Motion Studio.

Voz sintética offline, `--solo-narracion` y montaje de duración exacta (`--duracion-estricta`).
Los tests que montan vídeo de verdad necesitan FFmpeg (PATH o AEGS_FFMPEG/AEGS_FFPROBE).
"""
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import wave

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos import mezclador_audio, montador_video, narracion, utilidades, validador  # noqa: E402

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

    @pytest.mark.parametrize("velocidad", ["+0%", "+50%"])
    def test_cada_caracter_alarga_la_narracion(self, tmp_path, velocidad):
        def dur(texto, nombre):
            return narracion.generar_audio_sintetico(texto, velocidad, str(tmp_path / nombre))

        assert dur("Hola.", "a.wav") < dur("Hola amigo.", "b.wav")
        assert dur("Hola.", "c.wav") < dur("Supercalifragilístico.", "d.wav")

    def test_velocidad_mal_formada_es_error_controlado(self, tmp_path):
        with pytest.raises(ValueError, match="Velocidad no válida"):
            narracion.generar_audio_sintetico("Hola.", "rapido", str(tmp_path / "x.wav"))
        datos = {"narrador": {"motor": "sintetico", "velocidad": "rapido"}, "escenas": ESCENAS}
        res = asyncio.run(narracion.ejecutar_narracion_concurrente(str(tmp_path), datos))
        assert not res["exito"]
        assert {e["id"] for e in res["errores"]} == {"hola", "adios"}

    def test_la_velocidad_cambia_la_duracion(self, tmp_path):
        normal = narracion.generar_audio_sintetico("Una frase de prueba.", "+0%", str(tmp_path / "n.wav"))
        rapida = narracion.generar_audio_sintetico("Una frase de prueba.", "+50%", str(tmp_path / "r.wav"))
        assert rapida < normal

    def test_narracion_del_proyecto_escribe_duraciones_sin_red(self, tmp_path, monkeypatch):
        monkeypatch.setattr(narracion.edge_tts, "Communicate", lambda *a, **k: pytest.fail("usó Edge TTS"))
        proyecto = _proyecto(tmp_path, ESCENAS)
        datos = json.loads((proyecto / "proyecto.json").read_text(encoding="utf-8"))
        res = asyncio.run(narracion.ejecutar_narracion_concurrente(str(proyecto), datos))
        assert res["exito"], res
        duraciones = json.loads((proyecto / "output" / "narracion_duraciones.json").read_text(encoding="utf-8"))
        assert set(duraciones) == {"hola", "adios"}
        assert all(d["duracion_real_seg"] > 0 and d["archivo"].endswith(".wav") for d in duraciones.values())


class TestValidacionEstricta:
    @pytest.mark.parametrize("motor", ["otro", [], {}])
    def test_motor_desconocido_se_rechaza(self, tmp_path, motor):
        proyecto = _proyecto(tmp_path, ESCENAS)
        datos = json.loads((proyecto / "proyecto.json").read_text(encoding="utf-8"))
        datos["narrador"]["motor"] = motor
        (proyecto / "proyecto.json").write_text(json.dumps(datos), encoding="utf-8")
        res = validador.inicializar_validador(str(proyecto))
        assert any("motor" in e for e in res["errores"]), res["errores"]

    @pytest.mark.parametrize("escenas", [None, 5])
    def test_escenas_mal_tipadas_en_modo_estricto_es_error_controlado(self, tmp_path, escenas):
        proyecto = _proyecto(tmp_path, escenas, estricta=True)
        res = validador.inicializar_validador(str(proyecto))
        assert any("'escenas' debe ser una lista" in e for e in res["errores"]), res["errores"]

    def test_sin_clips_requeridos_un_clip_ausente_es_aviso(self, tmp_path):
        proyecto = _proyecto(tmp_path, ESCENAS)
        exigente = validador.inicializar_validador(str(proyecto))
        assert any("Clip inválido o ausente en 'hola'" in e for e in exigente["errores"])
        permisivo = validador.inicializar_validador(str(proyecto), requiere_clips=False)
        assert permisivo["exito"], permisivo["errores"]
        assert any("Clip inválido o ausente en 'hola'" in w for w in permisivo["warnings"])

    def test_sin_clips_requeridos_la_estructura_sigue_validandose(self, tmp_path):
        escenas = [dict(ESCENAS[0], transicion_salida="crossfade"), {"id": "sin_texto", "clip": "clips/x.mp4"}]
        proyecto = _proyecto(tmp_path, escenas)
        res = validador.inicializar_validador(str(proyecto), requiere_clips=False, duracion_estricta=True)
        assert any("con montaje.duracion_estricta solo se admite" in e for e in res["errores"]), res["errores"]
        assert any("'sin_texto' no tiene texto" in e for e in res["errores"]), res["errores"]

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
    def test_solo_narracion_no_necesita_los_clips_aun(self, tmp_path, ffmpeg):
        # Narración primero: los clips se renderizan DESPUÉS de medir la voz.
        proyecto = _proyecto(tmp_path, ESCENAS)
        assert not (proyecto / "clips" / "hola.mp4").exists()
        res = _aegs(proyecto, "--solo-narracion")
        assert res.returncode == 0, res.stdout + res.stderr
        duraciones = json.loads((proyecto / "output" / "narracion_duraciones.json").read_text(encoding="utf-8"))
        assert set(duraciones) == {"hola", "adios"}
        assert not (proyecto / "output" / "video_final.mp4").exists()

    def test_solo_narracion_con_skip_tts_se_rechaza(self, tmp_path):
        proyecto = _proyecto(tmp_path, ESCENAS)
        res = _aegs(proyecto, "--solo-narracion", "--skip-tts")
        assert res.returncode == 2
        assert "--skip-tts" in res.stderr
        assert not (proyecto / "output").exists()

    def _narrar_y_cortar_clips(self, tmp_path, ffmpeg, sobra_seg=0.0):
        tmp_path.mkdir(exist_ok=True)
        proyecto = _proyecto(tmp_path, ESCENAS, estricta=True)
        res = _aegs(proyecto, "--solo-narracion")
        assert res.returncode == 0, res.stdout + res.stderr
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
        assert abs(_duracion(ffmpeg, proyecto / "output" / "video_final.mp4") - total) <= 1.0 / FPS

    def test_muchas_escenas_no_acumulan_deriva(self, tmp_path, ffmpeg):
        # 10 escenas de 1,48 s = 44,4 fotogramas a 30 fps. Cada clip a medida (44 fotogramas) cumple
        # la tolerancia de ±1 fotograma, pero el vídeo final debe durar la suma (14,8 s) ±1 fotograma.
        escenas = [
            {"id": f"e{i}", "clip": f"clips/e{i}.mp4", "texto_narracion": "Texto de prueba suficiente."}
            for i in range(10)
        ]
        proyecto = _proyecto(tmp_path, escenas, estricta=True)
        (proyecto / "output" / "narracion").mkdir(parents=True)
        duraciones = {}
        for e in escenas:
            with wave.open(str(proyecto / "output" / "narracion" / f"{e['id']}.wav"), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(b"\x00\x00" * 35520)  # 1,48 s exactos
            duraciones[e["id"]] = {"archivo": f"output/narracion/{e['id']}.wav", "duracion_real_seg": 1.48}
            _clip(ffmpeg, proyecto / e["clip"], 1.48)
        (proyecto / "output" / "narracion_duraciones.json").write_text(json.dumps(duraciones), encoding="utf-8")
        res = _aegs(proyecto, "--skip-tts", "--skip-subs")
        assert res.returncode == 0, res.stdout + res.stderr
        assert abs(_duracion(ffmpeg, proyecto / "output" / "video_final.mp4") - 10 * 1.48) <= 1.0 / FPS

    def test_ruta_de_proyecto_relativa_monta(self, tmp_path, ffmpeg, monkeypatch):
        proyecto, _ = self._narrar_y_cortar_clips(tmp_path / "proyecto", ffmpeg)
        datos = json.loads((proyecto / "proyecto.json").read_text(encoding="utf-8"))
        monkeypatch.chdir(tmp_path)
        assert mezclador_audio.mezclar_audio_proyecto("proyecto", datos)["exito"]
        res = montador_video.montar_video_proyecto("proyecto", datos)
        assert res["exito"], res
        assert (proyecto / "output" / "video_final.mp4").exists()

    @pytest.mark.parametrize("sobra", [1.0, -1.0])
    def test_clip_que_no_encaja_falla_sin_recortar_ni_congelar(self, tmp_path, ffmpeg, sobra):
        proyecto, duraciones = self._narrar_y_cortar_clips(tmp_path, ffmpeg, sobra_seg=sobra)
        assert duraciones["hola"]["duracion_real_seg"] > 1.5  # el caso -1 s deja un clip real
        previo = proyecto / "output" / "video_final.mp4"
        previo.write_bytes(b"video de una ejecucion anterior")
        res = _aegs(proyecto, "--skip-tts", "--skip-subs")
        salida = res.stdout + res.stderr
        assert res.returncode != 0
        assert "hola" in salida and "duración estricta" in salida, salida
        # El error da las dos duraciones: la que necesita la escena y la del clip.
        necesita, dura = (float(x) for x in re.search(r"necesita ([\d.]+) s .* dura ([\d.]+) s", salida).groups())
        assert abs(necesita - duraciones["hola"]["duracion_real_seg"]) <= 1.0 / FPS
        assert abs(dura - (duraciones["hola"]["duracion_real_seg"] + sobra)) <= 1.0 / FPS
        assert not (proyecto / "output" / "video_final.mp4").exists()

    def test_clip_con_audio_mas_largo_que_su_video_no_se_congela(self, tmp_path, ffmpeg):
        proyecto, duraciones = self._narrar_y_cortar_clips(tmp_path, ffmpeg)
        necesita = duraciones["hola"]["duracion_real_seg"]
        clip = proyecto / "clips" / "hola.mp4"
        # Vídeo 1 s más corto que la escena, pero con una pista de audio que llega hasta su final:
        # el contenedor "dura" lo que pide la escena y el vídeo no.
        solo_video, solo_audio = tmp_path / "solo_video.mp4", tmp_path / "solo_audio.m4a"
        _clip(ffmpeg, solo_video, necesita - 1.0)
        subprocess.run(
            [ffmpeg["ffmpeg"], "-v", "error", "-y", "-f", "lavfi",
             "-i", f"sine=frequency=440:sample_rate=48000:duration={necesita:.3f}", "-c:a", "aac", str(solo_audio)],
            check=True,
        )
        subprocess.run(
            [ffmpeg["ffmpeg"], "-v", "error", "-y", "-i", str(solo_video), "-i", str(solo_audio),
             "-map", "0:v", "-map", "1:a", "-c", "copy", str(clip)],
            check=True,
        )
        dur_video = float(json.loads(subprocess.run(
            [ffmpeg["ffprobe"], "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=duration", "-of", "json", str(clip)],
            capture_output=True, text=True, check=True).stdout)["streams"][0]["duration"])
        assert abs(dur_video - (necesita - 1.0)) <= 1.0 / FPS  # el vídeo es de verdad 1 s más corto
        assert abs(_duracion(ffmpeg, clip) - necesita) <= 1.0 / FPS  # y el contenedor no
        res = _aegs(proyecto, "--skip-tts", "--skip-subs")
        salida = res.stdout + res.stderr
        assert res.returncode != 0, salida
        assert "hola" in salida and "duración estricta" in salida, salida
        assert not (proyecto / "output" / "video_final.mp4").exists()

    def test_fallo_de_validacion_estricta_no_deja_video_anterior(self, tmp_path, ffmpeg):
        escenas = [dict(ESCENAS[0], transicion_salida="crossfade"), dict(ESCENAS[1])]
        proyecto = _proyecto(tmp_path, escenas, estricta=True)
        (proyecto / "output").mkdir()
        (proyecto / "output" / "video_final.mp4").write_bytes(b"video de una ejecucion anterior")
        res = _aegs(proyecto, "--skip-tts", "--skip-subs")
        assert res.returncode == 1
        assert "solo se admite" in res.stdout + res.stderr
        assert not (proyecto / "output" / "video_final.mp4").exists()

    def test_flag_de_cli_activa_el_modo_estricto(self, tmp_path, ffmpeg):
        proyecto = _proyecto(tmp_path, ESCENAS)  # sin "montaje" en el JSON
        assert _aegs(proyecto, "--solo-narracion").returncode == 0
        for escena in ESCENAS:
            _clip(ffmpeg, proyecto / escena["clip"], 1)
        res = _aegs(proyecto, "--skip-tts", "--skip-subs", "--duracion-estricta")
        assert res.returncode != 0
        assert "duración estricta" in res.stdout + res.stderr


class TestTimelineEstricto:
    """Borde de la tolerancia (±1 fotograma) y escenas sin narración, sobre calcular_timeline."""

    def _preparar(self, tmp_path, ffmpeg, fotogramas_clip):
        proyecto = _proyecto(tmp_path, ESCENAS[:1], estricta=True)
        _clip(ffmpeg, proyecto / "clips" / "hola.mp4", fotogramas_clip / FPS)
        (proyecto / "output").mkdir()
        duraciones = {"hola": {"archivo": "output/narracion/hola.wav", "duracion_real_seg": 1.0}}
        (proyecto / "output" / "narracion_duraciones.json").write_text(json.dumps(duraciones), encoding="utf-8")
        return proyecto, json.loads((proyecto / "proyecto.json").read_text(encoding="utf-8"))

    @pytest.mark.parametrize("fotogramas", [FPS - 1, FPS, FPS + 1])
    def test_un_fotograma_de_diferencia_se_acepta(self, tmp_path, ffmpeg, fotogramas):
        proyecto, datos = self._preparar(tmp_path, ffmpeg, fotogramas)
        timeline = montador_video.calcular_timeline(str(proyecto), datos)
        assert timeline["escenas"][0]["id"] == "hola"

    @pytest.mark.parametrize("fotogramas", [FPS - 2, FPS + 2])
    def test_dos_fotogramas_de_diferencia_fallan(self, tmp_path, ffmpeg, fotogramas):
        proyecto, datos = self._preparar(tmp_path, ffmpeg, fotogramas)
        with pytest.raises(ValueError, match="duración estricta: la escena 'hola'"):
            montador_video.calcular_timeline(str(proyecto), datos)

    def test_la_rejilla_redondea_medio_fotograma_hacia_arriba(self):
        # Igual que Math.round de JS (el adaptador de Aura): round() de Python daría 2.
        assert montador_video._fotograma(2.5, 1) == 3
        assert montador_video._fotograma(1.0, FPS) == FPS

    def test_clip_sin_pista_de_video_falla(self, tmp_path, ffmpeg):
        proyecto, datos = self._preparar(tmp_path, ffmpeg, FPS)
        subprocess.run(
            [ffmpeg["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
             "-c:a", "aac", str(proyecto / "clips" / "hola.mp4")],
            check=True,
        )
        with pytest.raises(ValueError, match="no tiene pista de vídeo"):
            montador_video.calcular_timeline(str(proyecto), datos)

    def test_escena_sin_narracion_falla_en_modo_estricto(self, tmp_path, ffmpeg):
        proyecto, datos = self._preparar(tmp_path, ffmpeg, FPS)
        datos["escenas"].append(dict(ESCENAS[1]))
        with pytest.raises(ValueError, match="'adios' no está en narracion_duraciones.json"):
            montador_video.calcular_timeline(str(proyecto), datos)
        datos["montaje"]["duracion_estricta"] = False
        timeline = montador_video.calcular_timeline(str(proyecto), datos)
        assert [e["id"] for e in timeline["escenas"]] == ["hola"]  # sin modo estricto: aviso y se omite

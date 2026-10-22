# -*- coding: utf-8 -*-
"""Tests — Imagen y voz no se desincronizan.

1. Quitar silencios corta los MISMOS tramos en el audio y en el vídeo.
2. Un fundido cruzado (crossfade) entre escenas no acorta el vídeo respecto al audio:
   cada escena empieza en su segundo del timeline y el total es la suma de las escenas.

Los tests que generan medios necesitan FFmpeg (PATH o AEGS_FFMPEG/AEGS_FFPROBE).
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos import mejoras, montador_video, utilidades  # noqa: E402
from configuracion import FADE_TRANSICION_SEG  # noqa: E402

MAIN = os.path.join(os.path.dirname(__file__), "..", "main.py")
FPS = 30


@pytest.fixture
def ffmpeg():
    """Rutas de ffmpeg y ffprobe, o se omite el test con su motivo."""
    try:
        rutas = {n: shutil.which(utilidades.binario(n)) for n in ("ffmpeg", "ffprobe")}
    except FileNotFoundError as e:
        pytest.skip(f"necesita FFmpeg: {e}")
    if not all(rutas.values()):
        pytest.skip("necesita FFmpeg y FFprobe (PATH o AEGS_FFMPEG/AEGS_FFPROBE)")
    filtros = subprocess.run([rutas["ffmpeg"], "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    if " xfade " not in filtros:
        pytest.skip("este FFmpeg no tiene el filtro xfade (hace falta FFmpeg 4.3 o posterior)")
    return rutas


def _duraciones_pistas(ffmpeg, ruta):
    salida = subprocess.run(
        [ffmpeg["ffprobe"], "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", str(ruta)],
        capture_output=True, text=True, check=True,
    ).stdout
    return {s["codec_type"]: float(s["duration"]) for s in json.loads(salida)["streams"]}


# ─── 1. Quitar silencios ────────────────────────────────

class TestTramosDeSilencio:
    def test_lee_los_silencios_del_registro_de_ffmpeg(self):
        registro = (
            "[silencedetect @ 0x1] silence_start: 2.0034\n"
            "[silencedetect @ 0x1] silence_end: 3.9971 | silence_duration: 1.9937\n"
            "[silencedetect @ 0x1] silence_start: 7.5\n"
        )
        assert mejoras._silencios_detectados(registro, duracion_total=9.0) == [(2.0034, 3.9971), (7.5, 9.0)]

    def test_conserva_un_margen_de_cada_silencio(self):
        mantener = mejoras._tramos_sin_silencio([(2.0, 4.0)], duracion_total=6.0, margen=0.15)
        assert mantener == [(0.0, 2.15), (3.85, 6.0)]

    def test_un_silencio_mas_corto_que_dos_margenes_no_se_corta(self):
        assert mejoras._tramos_sin_silencio([(2.0, 2.25)], duracion_total=6.0, margen=0.15) == [(0.0, 6.0)]

    def test_sin_silencios_se_mantiene_todo(self):
        assert mejoras._tramos_sin_silencio([], duracion_total=5.0, margen=0.15) == [(0.0, 5.0)]


def _video_rojo_azul_con_hueco(ffmpeg, ruta):
    """6 s: rojo 0–4 s y azul 4–6 s; tono 0–2 s, silencio 2–4 s, tono 4–6 s.
    El tono vuelve justo cuando la imagen pasa a azul: así se mide la sincronía."""
    subprocess.run(
        [ffmpeg["ffmpeg"], "-v", "error", "-y",
         "-f", "lavfi", "-i", f"color=c=red:s=160x120:r={FPS}:d=4",
         "-f", "lavfi", "-i", f"color=c=blue:s=160x120:r={FPS}:d=2",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=6",
         "-filter_complex",
         "[0:v][1:v]concat=n=2:v=1:a=0[v];[2:a]volume='if(between(t,2,4),0,0.5)':eval=frame[a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(ruta)],
        check=True,
    )


def _primer_fotograma_azul(ffmpeg, ruta):
    salida = subprocess.run(
        [ffmpeg["ffprobe"], "-v", "error", "-f", "lavfi", "-i", f"movie={_ruta_filtro(ruta)},signalstats",
         "-show_entries", "frame=pts_time:frame_tags=lavfi.signalstats.VAVG", "-of", "json"],
        capture_output=True, text=True, check=True,
    ).stdout
    for frame in json.loads(salida)["frames"]:
        if float(frame["tags"]["lavfi.signalstats.VAVG"]) < 128:  # rojo: V alto; azul: V bajo
            return float(frame["pts_time"])
    raise AssertionError("no aparece ningún fotograma azul")


def _ruta_filtro(ruta):
    # Dentro de un filtro de FFmpeg los ':' y '\' de una ruta de Windows hay que escaparlos.
    return str(ruta).replace("\\", "/").replace(":", "\\\\:")


def _vuelta_del_tono(ffmpeg, ruta):
    registro = subprocess.run(
        [ffmpeg["ffmpeg"], "-hide_banner", "-i", str(ruta), "-af", "silencedetect=noise=-35dB:d=0.05", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    finales = [float(linea.split("silence_end:")[1].split("|")[0]) for linea in registro.splitlines() if "silence_end:" in linea]
    assert finales, "el tono no vuelve tras el silencio"
    return finales[0]


class TestCortarSilenciosSincronizado:
    def test_corta_lo_mismo_en_audio_y_en_video(self, tmp_path, ffmpeg):
        entrada, salida = tmp_path / "entrada.mp4", tmp_path / "salida.mp4"
        _video_rojo_azul_con_hueco(ffmpeg, entrada)
        mejoras.cortar_silencios(str(entrada), str(salida), umbral_db=-35.0, duracion_min=0.6)

        pistas = _duraciones_pistas(ffmpeg, salida)
        assert pistas["video"] < 4.8, f"no se quitó el silencio del vídeo: {pistas}"
        assert abs(pistas["video"] - pistas["audio"]) < 0.1, f"audio y vídeo acaban distintos: {pistas}"
        # Sincronía: el tono vuelve a la vez que la imagen pasa a azul (±2 fotogramas).
        assert abs(_vuelta_del_tono(ffmpeg, salida) - _primer_fotograma_azul(ffmpeg, salida)) <= 2 / FPS

    def test_sin_silencios_no_cambia_la_duracion(self, tmp_path, ffmpeg):
        entrada, salida = tmp_path / "entrada.mp4", tmp_path / "salida.mp4"
        subprocess.run(
            [ffmpeg["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=red:s=160x120:r={FPS}:d=3",
             "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=3",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(entrada)],
            check=True,
        )
        mejoras.cortar_silencios(str(entrada), str(salida))
        assert abs(_duraciones_pistas(ffmpeg, salida)["video"] - 3.0) < 0.1


# ─── 2. Fundido cruzado entre escenas ───────────────────

def _escenas(transiciones, duraciones):
    escenas, inicio = [], 0.0
    for i, (dur, (entra, sale)) in enumerate(zip(duraciones, transiciones)):
        escenas.append({"id": f"e{i}", "inicio_seg": inicio, "fin_seg": inicio + dur, "duracion_necesaria": dur,
                        "transicion_entrada": entra, "transicion_salida": sale})
        inicio += dur
    return escenas


class TestGrafoCrossfade:
    def test_cada_fundido_empieza_donde_empieza_su_escena(self):
        escenas = _escenas([("cut", "crossfade"), ("crossfade", "crossfade"), ("crossfade", "cut")], [3.0, 4.0, 2.5])
        grafo = montador_video._grafo_transiciones(escenas, FADE_TRANSICION_SEG)
        assert f"offset={3.0:.3f}" in grafo and f"offset={7.0:.3f}" in grafo

    def test_la_escena_que_sale_con_fundido_se_alarga_lo_que_dura_el_fundido(self):
        escenas = _escenas([("cut", "crossfade"), ("crossfade", "cut"), ("cut", "cut")], [3.0, 4.0, 2.5])
        assert montador_video._duracion_procesada(escenas, 0, FADE_TRANSICION_SEG) == pytest.approx(3.0 + FADE_TRANSICION_SEG)
        assert montador_video._duracion_procesada(escenas, 1, FADE_TRANSICION_SEG) == pytest.approx(4.0)
        assert montador_video._duracion_procesada(escenas, 2, FADE_TRANSICION_SEG) == pytest.approx(2.5)


class TestCrossfadeNoAcortaElVideo:
    def test_video_y_audio_duran_lo_mismo_que_el_timeline(self, tmp_path, ffmpeg):
        (tmp_path / "clips").mkdir()
        escenas = []
        textos = ["Primera escena con algo de texto.", "Segunda escena.", "Tercera y última escena del vídeo."]
        for i, texto in enumerate(textos):
            subprocess.run(
                [ffmpeg["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=320x240:rate={FPS}",
                 "-frames:v", str(8 * FPS), "-pix_fmt", "yuv420p", str(tmp_path / "clips" / f"c{i}.mp4")],
                check=True,
            )
            escenas.append({"id": f"c{i}", "clip": f"clips/c{i}.mp4", "texto_narracion": texto,
                            "transicion_entrada": "crossfade" if i else "cut",
                            "transicion_salida": "crossfade" if i < len(textos) - 1 else "cut"})
        datos = {"titulo": "Fundidos", "idioma": "es", "fps": FPS, "resolucion": "320x240",
                 "narrador": {"motor": "sintetico", "velocidad": "+0%"}, "escenas": escenas}
        (tmp_path / "proyecto.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

        res = subprocess.run([sys.executable, MAIN, str(tmp_path), "--skip-subs"], capture_output=True, text=True)
        assert res.returncode == 0, res.stdout + res.stderr

        total = json.loads((tmp_path / "output" / "timeline.json").read_text(encoding="utf-8"))["duracion_total_seg"]
        pistas = _duraciones_pistas(ffmpeg, tmp_path / "output" / "video_final.mp4")
        assert pistas["video"] == pytest.approx(total, abs=1.5 / FPS), (pistas, total)
        assert pistas["audio"] == pytest.approx(total, abs=1.5 / FPS), (pistas, total)

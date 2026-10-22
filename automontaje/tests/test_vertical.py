# -*- coding: utf-8 -*-
"""Tests — Formato vertical 9:16 con encuadre elegible.

Un vídeo horizontal con la mitad izquierda roja y la derecha azul: «izquierda» conserva
el rojo, «derecha» el azul, «centro» el corte entre los dos y «completo» no pierde nada.
"""
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos import editor_comandos, mejoras, utilidades  # noqa: E402


@pytest.fixture
def ffmpeg():
    try:
        rutas = {n: shutil.which(utilidades.binario(n)) for n in ("ffmpeg", "ffprobe")}
    except FileNotFoundError as e:
        pytest.skip(f"necesita FFmpeg: {e}")
    if not all(rutas.values()):
        pytest.skip("necesita FFmpeg y FFprobe (PATH o AEGS_FFMPEG/AEGS_FFPROBE)")
    return rutas


@pytest.fixture
def rojo_azul(tmp_path, ffmpeg):
    ruta = tmp_path / "rojo_azul.mp4"
    subprocess.run(
        [ffmpeg["ffmpeg"], "-v", "error", "-y",
         "-f", "lavfi", "-i", "color=c=red:s=640x360:r=10:d=1",
         "-f", "lavfi", "-i", "color=c=blue:s=640x360:r=10:d=1",
         "-filter_complex", "[0:v][1:v]hstack,format=yuv420p",
         "-c:v", "libx264", str(ruta)],
        check=True,
    )
    return ruta


def _color(ffmpeg, ruta, x, y, w=60, h=60):
    """Color medio (r, g, b) de una zona del primer fotograma."""
    datos = subprocess.run(
        [ffmpeg["ffmpeg"], "-v", "error", "-i", str(ruta), "-frames:v", "1",
         "-vf", f"crop={w}:{h}:{x}:{y},scale=1:1:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout
    return tuple(datos[:3])


def _es_rojo(c):
    return c[0] > 150 and c[2] < 100


def _es_azul(c):
    return c[2] > 150 and c[0] < 100


class TestEncuadreVertical:
    @pytest.mark.parametrize("encuadre,comprobar", [("izquierda", _es_rojo), ("derecha", _es_azul)])
    def test_un_lado(self, tmp_path, ffmpeg, rojo_azul, encuadre, comprobar):
        salida = tmp_path / f"{encuadre}.mp4"
        mejoras.convertir_vertical_9_16(str(rojo_azul), str(salida), encuadre=encuadre)
        for x in (60, 510, 960):
            assert comprobar(_color(ffmpeg, salida, x, 930)), (encuadre, x)

    def test_centro_corta_por_la_mitad(self, tmp_path, ffmpeg, rojo_azul):
        salida = tmp_path / "centro.mp4"
        mejoras.convertir_vertical_9_16(str(rojo_azul), str(salida))
        assert _es_rojo(_color(ffmpeg, salida, 60, 930))
        assert _es_azul(_color(ffmpeg, salida, 960, 930))

    def test_completo_conserva_los_dos_lados_sin_recortar(self, tmp_path, ffmpeg, rojo_azul):
        salida = tmp_path / "completo.mp4"
        mejoras.convertir_vertical_9_16(str(rojo_azul), str(salida), encuadre="completo")
        dims = subprocess.run([ffmpeg["ffprobe"], "-v", "error", "-show_entries", "stream=width,height",
                               "-of", "csv=p=0", str(salida)], capture_output=True, text=True, check=True).stdout
        assert dims.strip() == "1080,1920"
        # El vídeo entero ocupa una franja de 1080x304 centrada: rojo a la izquierda, azul a la derecha.
        assert _es_rojo(_color(ffmpeg, salida, 60, 930))
        assert _es_azul(_color(ffmpeg, salida, 960, 930))

    def test_encuadre_desconocido_es_un_error_claro(self, tmp_path, rojo_azul):
        with pytest.raises(ValueError, match="Encuadre vertical desconocido"):
            mejoras.convertir_vertical_9_16(str(rojo_azul), str(tmp_path / "x.mp4"), encuadre="arriba")


class TestEncuadreEnComandos:
    @pytest.mark.parametrize("orden,esperado", [
        ("hazlo vertical para reels", "centro"),
        ("vertical pero que se vea la persona de la izquierda", "izquierda"),
        ("formato tiktok encuadrado a la derecha", "derecha"),
        ("vertical sin recortar nada", "completo"),
    ])
    def test_el_comando_elige_el_encuadre(self, orden, esperado):
        cfg = editor_comandos.parsear_comando_edicion(orden)["config"]
        assert cfg["formato_vertical"] is True
        assert cfg["encuadre_vertical"] == esperado

# -*- coding: utf-8 -*-
"""Tests — Los tiempos de un contrato se refieren al vídeo ORIGINAL.

«Quita del 7 al 9 y pon un texto en el segundo 12»: el 12 es el del vídeo que la persona tiene
delante, aunque el corte vaya antes. Un contrato puede pedir lo contrario con "tiempos": "resultado".
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos import contrato_edicion as ce  # noqa: E402
from modulos import utilidades  # noqa: E402


@pytest.fixture
def registro_falso(monkeypatch):
    """Herramientas falsas que anotan con qué tiempos se las llamó y quitan tiempo como un corte real."""
    llamadas = []

    def corte(entrada, salida, params):
        llamadas.append(("corte", params["inicio"], params["fin"]))
        shutil.copy2(entrada, salida)
        return ce.SalidaPaso(salida, conservados=[(0.0, params["inicio"]), (params["fin"], 1e9)])

    def texto(entrada, salida, params):
        llamadas.append(("texto", params["inicio"]))
        shutil.copy2(entrada, salida)
        return salida

    registro = dict(ce.REGISTRO_HERRAMIENTAS)
    registro["corte"] = ce.REGISTRO_HERRAMIENTAS["corte"].__class__(
        **{**ce.REGISTRO_HERRAMIENTAS["corte"].__dict__, "ejecutar": corte})
    registro["texto"] = ce.REGISTRO_HERRAMIENTAS["texto"].__class__(
        **{**ce.REGISTRO_HERRAMIENTAS["texto"].__dict__, "ejecutar": texto})
    monkeypatch.setattr(ce, "REGISTRO_HERRAMIENTAS", registro)
    return llamadas


def _ejecutar(tmp_path, pasos, **extra):
    entrada = tmp_path / "entrada.mp4"
    entrada.write_text("video", encoding="utf-8")
    return ce.ejecutar_contrato_herramientas(str(entrada), str(tmp_path / "salida.mp4"), {"herramientas": pasos, **extra})


CORTE_7_9 = {"herramienta": "corte", "parametros": {"inicio": 7.0, "fin": 9.0}}


class TestTiemposDelOriginal:
    def test_un_texto_despues_de_un_corte_cae_en_el_mismo_momento_del_original(self, tmp_path, registro_falso):
        res = _ejecutar(tmp_path, [CORTE_7_9, {"herramienta": "texto", "parametros": {"texto": "Idea", "inicio": 12.0}}])
        assert res["exito"], res
        assert registro_falso == [("corte", 7.0, 9.0), ("texto", 10.0)]
        assert res["contrato"]["tiempos"] == "original"

    def test_con_tiempos_del_resultado_no_se_traducen(self, tmp_path, registro_falso):
        res = _ejecutar(tmp_path, [CORTE_7_9, {"herramienta": "texto", "parametros": {"texto": "Idea", "inicio": 12.0}}],
                        tiempos="resultado")
        assert res["exito"], res
        assert registro_falso[-1] == ("texto", 12.0)

    def test_un_texto_en_un_tramo_quitado_va_al_siguiente_momento_y_avisa(self, tmp_path, registro_falso):
        res = _ejecutar(tmp_path, [CORTE_7_9, {"herramienta": "texto", "parametros": {"texto": "Idea", "inicio": 8.0}}])
        assert registro_falso[-1] == ("texto", 7.0)
        assert any("se habia quitado" in a for a in res["avisos"]), res["avisos"]

    def test_un_segundo_corte_se_traduce_al_resultado(self, tmp_path, registro_falso):
        segundo = {"herramienta": "corte", "parametros": {"inicio": 12.0, "fin": 14.0}}
        _ejecutar(tmp_path, [CORTE_7_9, segundo])
        assert registro_falso == [("corte", 7.0, 9.0), ("corte", 10.0, 12.0)]

    def test_un_corte_de_algo_ya_quitado_se_omite_y_el_video_sale_igual(self, tmp_path, registro_falso):
        repetido = {"herramienta": "corte", "parametros": {"inicio": 7.5, "fin": 8.5}}
        res = _ejecutar(tmp_path, [CORTE_7_9, repetido])
        assert res["exito"], res
        assert registro_falso == [("corte", 7.0, 9.0)]
        assert res["pasos_omitidos"] == ["corte"]
        assert (tmp_path / "salida.mp4").exists()

    def test_tiempos_desconocidos_es_un_error_de_validacion(self):
        res = ce.validar_contrato_herramientas({"herramientas": [], "tiempos": "ayer"})
        assert not res["valido"]
        assert any("'tiempos'" in e for e in res["errores"]), res["errores"]


@pytest.fixture
def ffmpeg():
    try:
        rutas = {n: shutil.which(utilidades.binario(n)) for n in ("ffmpeg", "ffprobe")}
    except FileNotFoundError as e:
        pytest.skip(f"necesita FFmpeg: {e}")
    if not all(rutas.values()):
        pytest.skip("necesita FFmpeg y FFprobe (PATH o AEGS_FFMPEG/AEGS_FFPROBE)")
    return rutas


class TestCortesRealesEncadenados:
    def test_dos_cortes_que_se_solapan_quitan_la_union_del_original(self, tmp_path, ffmpeg):
        entrada = tmp_path / "entrada.mp4"
        subprocess.run(
            [ffmpeg["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=30:duration=10",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=10", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-shortest", str(entrada)],
            check=True,
        )
        salida = tmp_path / "salida.mp4"
        contrato = {"herramientas": [
            {"herramienta": "corte", "parametros": {"inicio": 1.0, "fin": 2.0}},
            {"herramienta": "corte", "parametros": {"inicio": 1.5, "fin": 3.0}},
        ]}
        res = ce.ejecutar_contrato_herramientas(str(entrada), str(salida), contrato)
        assert res["exito"], res
        duracion = float(json.loads(subprocess.run(
            [ffmpeg["ffprobe"], "-v", "error", "-show_entries", "format=duration", "-of", "json", str(salida)],
            capture_output=True, text=True, check=True).stdout)["format"]["duration"])
        # Se quita la unión [1, 3] del original: quedan 8 s (encadenado sobre el resultado quedarían 7,5).
        assert duracion == pytest.approx(8.0, abs=0.1)

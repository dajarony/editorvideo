"""Comportamientos de usuario incorporados en la revisión del editor."""
import json
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modulos.contrato_edicion import validar_contrato_herramientas, ejecutar_contrato_herramientas
from modulos.editor_comandos import parsear_comando_edicion
from modulos.proceso import ControlProceso
from modulos.servicio_edicion import previsualizar
from modulos.subtitulos import generar_srt_matematico
from modulos.utilidades import binario


@pytest.mark.parametrize("frase,campo", [
    ("sin mejorar", "mejora_real"),
    ("no lo hagas vertical", "formato_vertical"),
    ("no quites los silencios", "cortar_silencios"),
])
def test_una_negacion_no_activa_la_herramienta(frase, campo):
    assert parsear_comando_edicion(frase)["config"][campo] is False


@pytest.mark.parametrize("valor", [True, float("nan"), float("inf")])
def test_tiempos_no_aceptan_booleanos_ni_no_finitos(valor):
    contrato = {"herramientas": [{"herramienta": "texto", "parametros":
                {"texto": "Hola", "inicio": valor}}]}
    assert not validar_contrato_herramientas(contrato)["valido"]


def test_guion_no_necesita_whisper(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    (output / "timeline.json").write_text(json.dumps({"escenas": [
        {"id": "e", "inicio_seg": 3}]}), encoding="utf-8")
    (output / "narracion_duraciones.json").write_text(json.dumps({"e": {
        "archivo": "output/narracion/e.mp3", "duracion_real_seg": 2}}), encoding="utf-8")
    monkeypatch.setitem(sys.modules, "whisper", None)
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    ruta = generar_srt_matematico(str(tmp_path), {"subtitulos": {"modo": "guion"},
        "escenas": [{"id": "e", "texto_narracion": "Esto es una prueba clara.", "pausa_antes_seg": 1}]})
    srt = open(ruta, encoding="utf-8-sig").read()
    assert "00:00:04,000 --> 00:00:06,000" in srt
    assert "Esto es una prueba clara." in srt


def test_cancelar_contrato_conserva_salida_anterior(tmp_path, monkeypatch):
    from modulos.contrato_edicion import REGISTRO_HERRAMIENTAS, HerramientaEdicion
    entrada, salida = tmp_path / "entrada.mp4", tmp_path / "salida.mp4"
    entrada.write_bytes(b"original")
    salida.write_bytes(b"anterior")
    control = ControlProceso()
    def paso(src, dst, params):
        open(dst, "wb").write(b"parcial")
        control.cancelar()
        return dst
    monkeypatch.setitem(REGISTRO_HERRAMIENTAS, "prueba", HerramientaEdicion(
        "prueba", "prueba", {}, paso))
    # El control consulta la duración antes del paso.
    with patch("modulos.efectos._info_video", return_value=(1, 320, 180, 30)):
        resultado = ejecutar_contrato_herramientas(str(entrada), str(salida),
                    {"herramientas": [{"herramienta": "prueba", "parametros": {}}]}, control=control)
    assert resultado["cancelado"]
    assert salida.read_bytes() == b"anterior"


def test_previsualizacion_compara_dos_lados(tmp_path):
    from modulos.servicio_edicion import previsualizar
    from modulos.utilidades import obtener_info_media
    entrada, salida = tmp_path / "entrada.mp4", tmp_path / "comparacion.mp4"
    try:
        ffmpeg = binario("ffmpeg")
    except FileNotFoundError as exc:
        pytest.skip(str(exc))
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=red:s=160x90:r=10:d=2",
                    "-c:v", "libx264", str(entrada)], capture_output=True, check=True)
    res = previsualizar(str(entrada), str(salida), {"tipo": "video", "audio_fades": False}, 0, 1)
    assert res["exito"], res
    assert obtener_info_media(str(salida))["resolucion"] == "1280x360"


def test_error_de_previsualizacion_conserva_salida_anterior(tmp_path):
    salida = tmp_path / "comparacion.mp4"
    salida.write_bytes(b"resultado anterior")
    resultado = previsualizar(str(tmp_path / "ausente.mp4"), str(salida),
                             {"tipo": "video", "audio_fades": False})
    assert not resultado["exito"]
    assert salida.read_bytes() == b"resultado anterior"


@pytest.mark.parametrize("desde", [float("nan"), float("inf"), float("-inf")])
def test_previsualizacion_rechaza_inicio_no_finito(tmp_path, desde):
    resultado = previsualizar(str(tmp_path / "ausente.mp4"),
                             str(tmp_path / "comparacion.mp4"), {"tipo": "video"}, desde)
    assert not resultado["exito"]
    assert "inicio positivo" in resultado["errores"][0]


def test_modelo_local_solo_propone_contratos_validados(monkeypatch):
    from modulos import modelo_ordenes
    class Respuesta:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            return json.dumps({"message": {"content": json.dumps({"herramientas": [
                {"herramienta": "texto", "parametros": {"texto": "Hola", "inicio": 2}}]})}}).encode()
    def responder(peticion, timeout):
        assert peticion.full_url == "http://127.0.0.1:11434/api/chat"
        assert b"texto" in peticion.data
        return Respuesta()
    monkeypatch.setattr(modelo_ordenes, "urlopen", responder)
    propuesta = modelo_ordenes.interpretar_orden("Escribe Hola al segundo 2", "modelo-local")
    assert propuesta["herramientas"][0]["parametros"]["inicio"] == 2

# -*- coding: utf-8 -*-
"""Tests del sistema de contratos por herramientas."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos.contrato_edicion import (
    HerramientaEdicion,
    REGISTRO_HERRAMIENTAS,
    ejecutar_contrato_herramientas,
    listar_herramientas,
    validar_contrato_herramientas,
)


class TestContratoHerramientas:
    def test_catalogo_expone_herramientas_existentes(self):
        nombres = {h["nombre"] for h in listar_herramientas()}
        assert "mejora_real" in nombres
        assert "vertical_9_16" in nombres
        assert "limpiar_voz" in nombres

    def test_validador_normaliza_defaults(self):
        contrato = {
            "herramientas": [
                {"herramienta": "mejora_real", "parametros": {}},
                {"herramienta": "vertical_9_16", "parametros": {}},
            ]
        }

        res = validar_contrato_herramientas(contrato)

        assert res["valido"] is True
        pasos = res["contrato"]["herramientas"]
        assert pasos[0]["parametros"]["nivel"] == "media"
        assert pasos[1]["parametros"] == {}

    def test_validador_rechaza_herramienta_desconocida(self):
        res = validar_contrato_herramientas({
            "herramientas": [{"herramienta": "ffmpeg_crudo", "parametros": {}}]
        })

        assert res["valido"] is False
        assert any("desconocida" in e for e in res["errores"])

    def test_validador_rechaza_parametro_desconocido(self):
        res = validar_contrato_herramientas({
            "herramientas": [
                {"herramienta": "mejora_real", "parametros": {"comando": "rm"}}
            ]
        })

        assert res["valido"] is False
        assert any("Parametro desconocido" in e for e in res["errores"])

    def test_validador_rechaza_choice_invalido(self):
        res = validar_contrato_herramientas({
            "herramientas": [
                {"herramienta": "mejora_real", "parametros": {"nivel": "brutal"}}
            ]
        })

        assert res["valido"] is False
        assert any("debe ser uno de" in e for e in res["errores"])

    def test_ejecutor_aplica_herramientas_en_orden(self, tmp_path, monkeypatch):
        entrada = tmp_path / "entrada.mp4"
        salida = tmp_path / "salida.mp4"
        entrada.write_text("inicio", encoding="utf-8")

        def herramienta_a(src, dst, params):
            texto = open(src, "r", encoding="utf-8").read()
            with open(dst, "w", encoding="utf-8") as f:
                f.write(texto + "|a")
            return dst

        def herramienta_b(src, dst, params):
            texto = open(src, "r", encoding="utf-8").read()
            with open(dst, "w", encoding="utf-8") as f:
                f.write(texto + "|" + params["marca"])
            return dst

        registro = dict(REGISTRO_HERRAMIENTAS)
        registro["fake_a"] = HerramientaEdicion(
            nombre="fake_a",
            descripcion="Prueba A",
            parametros={},
            ejecutar=herramienta_a,
        )
        registro["fake_b"] = HerramientaEdicion(
            nombre="fake_b",
            descripcion="Prueba B",
            parametros={"marca": {"type": "str", "default": "b"}},
            ejecutar=herramienta_b,
        )
        monkeypatch.setattr("modulos.contrato_edicion.REGISTRO_HERRAMIENTAS", registro)

        res = ejecutar_contrato_herramientas(str(entrada), str(salida), {
            "herramientas": [
                {"herramienta": "fake_a", "parametros": {}},
                {"herramienta": "fake_b", "parametros": {"marca": "final"}},
            ]
        })

        assert res["exito"] is True
        assert res["pasos_ejecutados"] == ["fake_a", "fake_b"]
        assert salida.read_text(encoding="utf-8") == "inicio|a|final"

    def test_ejecutor_no_crea_salida_si_contrato_invalido(self, tmp_path):
        entrada = tmp_path / "entrada.mp4"
        salida = tmp_path / "salida.mp4"
        entrada.write_text("inicio", encoding="utf-8")

        res = ejecutar_contrato_herramientas(str(entrada), str(salida), {
            "herramientas": [{"herramienta": "no_existe", "parametros": {}}]
        })

        assert res["exito"] is False
        assert not salida.exists()


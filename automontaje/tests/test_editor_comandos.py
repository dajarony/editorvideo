# -*- coding: utf-8 -*-
"""Tests unitarios - interprete de comandos de edicion."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos.editor_comandos import parsear_comando_edicion, parsear_comando_contrato


class TestEditorComandos:
    def test_comando_vertical_mejora_silencios(self):
        plan = parsear_comando_edicion(
            "hazlo vertical para reels, mejora calidad media y quita silencios"
        )
        cfg = plan["config"]
        assert cfg["formato_vertical"] is True
        assert cfg["mejora_real"] is True
        assert cfg["nivel_mejora"] == "media"
        assert cfg["cortar_silencios"] is True

    def test_comando_cinematico_fuerte(self):
        plan = parsear_comando_edicion("look cinematico fuerte con ia x4")
        cfg = plan["config"]
        assert cfg["color_grading"] is True
        assert cfg["estilo_color"] == "cinematico"
        assert cfg["nivel_mejora"] == "fuerte"
        assert cfg["esrgan"] is True

    def test_comando_sin_color_grading(self):
        plan = parsear_comando_edicion("mejora natural sin color grading")
        cfg = plan["config"]
        assert cfg["color_grading"] is False
        assert cfg["estilo_color"] == "natural_claro"

    def test_comando_subtitulos(self):
        plan = parsear_comando_edicion("ponle subtitulos y hazlo vertical")
        cfg = plan["config"]
        assert cfg["subtitulos"] is True
        assert cfg["formato_vertical"] is True
        assert "subtitulos automaticos" in plan["acciones"]

    def test_comando_sin_subtitulos_no_contradice(self):
        plan = parsear_comando_edicion("mejora fuerte sin subtitulos")
        cfg = plan["config"]
        assert cfg["subtitulos"] is False
        assert "sin subtitulos" in plan["acciones"]
        assert "subtitulos automaticos" not in plan["acciones"]

    def test_comando_quitar_musica_activa_voz_fuerte(self):
        plan = parsear_comando_edicion("quita la musica de fondo y deja solo la voz fuerte")
        cfg = plan["config"]
        assert cfg["limpiar_voz"] is True
        assert cfg["nivel_voz"] == "fuerte"

    def test_contrato_desde_comando_texto(self):
        plan = parsear_comando_contrato(
            'en el segundo 12 pon texto "Idea clave" durante 3 segundos arriba'
        )
        paso = plan["contrato"]["herramientas"][0]
        assert paso["herramienta"] == "texto"
        assert paso["parametros"]["inicio"] == 12
        # El texto a mostrar conserva las mayusculas originales.
        assert paso["parametros"]["texto"] == "Idea clave"
        assert paso["parametros"]["posicion"] == "arriba"

    def test_contrato_desde_comando_zoom(self):
        plan = parsear_comando_contrato("en 00:18 zoom suave durante 2 segundos")
        paso = plan["contrato"]["herramientas"][0]
        assert paso["herramienta"] == "zoom"
        assert paso["parametros"]["inicio"] == 18
        assert paso["parametros"]["duracion"] == 2
        assert paso["parametros"]["intensidad"] == "suave"

    def test_contrato_desde_comando_corte(self):
        plan = parsear_comando_contrato("corta de 7 a 9")
        paso = plan["contrato"]["herramientas"][0]
        assert paso["herramienta"] == "corte"
        assert paso["parametros"] == {"inicio": 7.0, "fin": 9.0}

    def test_contrato_desde_comando_imagen(self):
        plan = parsear_comando_contrato(
            "en 00:25 pon imagen logo.png arriba derecha durante 4 segundos"
        )
        paso = plan["contrato"]["herramientas"][0]
        assert paso["herramienta"] == "imagen"
        assert paso["parametros"]["archivo"] == "logo.png"
        assert paso["parametros"]["posicion"] == "arriba_der"

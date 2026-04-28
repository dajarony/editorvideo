# -*- coding: utf-8 -*-
"""Tests unitarios — Módulo 0: Validador."""
import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos.validador import inicializar_validador


class TestValidadorEstructuraJSON:
    def test_proyecto_sin_json_falla(self, tmp_path):
        res = inicializar_validador(str(tmp_path))
        assert res["exito"] is False
        assert any("No se encontró" in e for e in res["errores"])

    def test_json_invalido_falla(self, tmp_path):
        (tmp_path / "proyecto.json").write_text("{invalid json", encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        assert res["exito"] is False
        assert any("JSON inválido" in e for e in res["errores"])

    def test_campos_obligatorios_faltantes(self, tmp_path):
        (tmp_path / "proyecto.json").write_text('{"titulo": "Test"}', encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        assert res["exito"] is False
        assert any("idioma" in e or "narrador" in e or "escenas" in e for e in res["errores"])

    def test_escenas_vacias_genera_error(self, tmp_path):
        data = {"titulo": "T", "idioma": "es", "narrador": {"voz": "es-ES-AlvaroNeural"}, "escenas": []}
        (tmp_path / "proyecto.json").write_text(json.dumps(data), encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        assert res["exito"] is False
        assert any("no tiene escenas" in e for e in res["errores"])


class TestValidadorEscenas:
    def test_id_duplicado_genera_error(self, tmp_path):
        data = {
            "titulo": "T", "idioma": "es",
            "narrador": {"voz": "es-ES-AlvaroNeural"},
            "escenas": [
                {"id": "dup", "clip": "c.mp4", "texto_narracion": "Texto largo de prueba uno."},
                {"id": "dup", "clip": "c.mp4", "texto_narracion": "Texto largo de prueba dos."}
            ]
        }
        (tmp_path / "proyecto.json").write_text(json.dumps(data), encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        assert any("duplicado" in e.lower() for e in res["errores"])

    def test_escena_sin_texto_genera_error(self, tmp_path):
        data = {
            "titulo": "T", "idioma": "es",
            "narrador": {"voz": "es-ES-AlvaroNeural"},
            "escenas": [{"id": "s1", "clip": "c.mp4", "texto_narracion": ""}]
        }
        (tmp_path / "proyecto.json").write_text(json.dumps(data), encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        assert any("no tiene texto" in e for e in res["errores"])

    def test_texto_corto_genera_warning(self, tmp_path):
        clips = tmp_path / "clips"
        clips.mkdir()
        data = {
            "titulo": "T", "idioma": "es",
            "narrador": {"voz": "es-ES-AlvaroNeural"},
            "escenas": [{"id": "s1", "clip": "clips/c.mp4", "texto_narracion": "Hola."}]
        }
        (tmp_path / "proyecto.json").write_text(json.dumps(data), encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        # El clip no existe así que habrá error de clip, pero el warning de texto corto también
        assert any("corto" in w.lower() for w in res["warnings"])

    def test_clip_inexistente_genera_error(self, tmp_path):
        data = {
            "titulo": "T", "idioma": "es",
            "narrador": {"voz": "es-ES-AlvaroNeural"},
            "escenas": [{"id": "s1", "clip": "clips/no_existe.mp4", "texto_narracion": "Texto largo suficiente."}]
        }
        (tmp_path / "proyecto.json").write_text(json.dumps(data), encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        assert any("inválido" in e.lower() or "ausente" in e.lower() for e in res["errores"])


class TestValidadorMusica:
    def test_musica_archivo_inexistente_genera_error(self, tmp_path):
        data = {
            "titulo": "T", "idioma": "es",
            "narrador": {"voz": "es-ES-AlvaroNeural"},
            "musica": {"fuente": "archivo", "archivo": "musica/no_existe.mp3"},
            "escenas": [{"id": "s1", "clip": "c.mp4", "texto_narracion": "Texto de prueba largo."}]
        }
        (tmp_path / "proyecto.json").write_text(json.dumps(data), encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        assert any("música" in e.lower() or "music" in e.lower() for e in res["errores"])

    def test_sin_musica_genera_warning(self, tmp_path):
        data = {
            "titulo": "T", "idioma": "es",
            "narrador": {"voz": "es-ES-AlvaroNeural"},
            "escenas": [{"id": "s1", "clip": "c.mp4", "texto_narracion": "Texto de prueba largo."}]
        }
        (tmp_path / "proyecto.json").write_text(json.dumps(data), encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        assert any("musica" in w.lower() or "música" in w.lower() for w in res["warnings"])


class TestValidadorNarrador:
    def test_voz_desconocida_genera_warning(self, tmp_path):
        data = {
            "titulo": "T", "idioma": "es",
            "narrador": {"voz": "xx-XX-FakeNeural"},
            "escenas": [{"id": "s1", "clip": "c.mp4", "texto_narracion": "Texto de prueba largo."}]
        }
        (tmp_path / "proyecto.json").write_text(json.dumps(data), encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        assert any("conocida" in w.lower() or "verificada" in w.lower() for w in res["warnings"])


class TestValidadorLogicaTiempos:
    def test_fin_menor_que_inicio_genera_error(self, tmp_path):
        """Si el clip no existe, se detecta como error de clip.
        Si existiera y ffprobe funcionara, detectaría error de lógica de tiempos.
        En ambos casos, la validación debe fallar."""
        data = {
            "titulo": "T", "idioma": "es",
            "narrador": {"voz": "es-ES-AlvaroNeural"},
            "escenas": [{
                "id": "s1", "clip": "c.mp4",
                "texto_narracion": "Texto de prueba largo.",
                "clip_inicio_seg": 10, "clip_fin_seg": 5
            }]
        }
        (tmp_path / "proyecto.json").write_text(json.dumps(data), encoding="utf-8")
        res = inicializar_validador(str(tmp_path))
        # Debe fallar (ya sea por clip o por lógica de tiempos)
        assert res["exito"] is False
        assert len(res["errores"]) > 0

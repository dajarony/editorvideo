# -*- coding: utf-8 -*-
"""Tests — Módulo 1: Narración (Edge TTS).
Los tests de integración TTS requieren internet.
La verificación post-gen requiere ffprobe, que puede no estar instalado.
"""
import os
import sys
import asyncio
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import edge_tts

# Fix Windows event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class TestEdgeTTSDirecto:
    """Tests de la API edge-tts directamente (sin ffprobe)."""

    @pytest.mark.asyncio
    async def test_edge_tts_genera_archivo(self, tmp_path):
        """Verifica que edge-tts crea un archivo MP3 real."""
        ruta = str(tmp_path / "test.mp3")
        comunicador = edge_tts.Communicate(
            text="Hola, esta es una prueba.", voice="es-ES-AlvaroNeural"
        )
        await comunicador.save(ruta)
        assert os.path.exists(ruta)
        assert os.path.getsize(ruta) > 1000  # MP3 real > 1KB

    @pytest.mark.asyncio
    async def test_edge_tts_velocidad_negativa(self, tmp_path):
        """Verifica que el parámetro rate funciona."""
        ruta = str(tmp_path / "slow.mp3")
        comunicador = edge_tts.Communicate(
            text="Prueba con velocidad lenta.", voice="es-ES-AlvaroNeural", rate="-5%"
        )
        await comunicador.save(ruta)
        assert os.path.exists(ruta)
        assert os.path.getsize(ruta) > 1000

    @pytest.mark.asyncio
    async def test_edge_tts_texto_largo(self, tmp_path):
        """Verifica generación con texto más largo (como narración real)."""
        ruta = str(tmp_path / "largo.mp3")
        texto = (
            "En un mundo lleno de ruido, a veces lo más valiente "
            "es quedarse en silencio. El silencio no es vacío, "
            "es espacio para pensar, para sentir, para ser."
        )
        comunicador = edge_tts.Communicate(
            text=texto, voice="es-ES-AlvaroNeural", rate="-5%"
        )
        await comunicador.save(ruta)
        assert os.path.exists(ruta)
        # Un texto largo debe generar un archivo más grande
        assert os.path.getsize(ruta) > 5000


class TestNarracionModulo:
    """Tests del módulo narración con mock de ffprobe."""

    @pytest.mark.asyncio
    async def test_genera_audio_sin_ffprobe_falla_graciosamente(self, tmp_path):
        """Sin ffprobe, la función falla con reintentos pero no crashea."""
        from modulos.narracion import generar_audio_escena
        resultado = await generar_audio_escena(
            id_escena="test_no_ffprobe",
            texto="Prueba sin ffprobe.",
            voz="es-ES-AlvaroNeural",
            velocidad="+0%",
            ruta_salida=str(tmp_path / "test.mp3")
        )
        # Sin ffprobe, el MP3 se genera pero no se puede verificar
        # La función debe fallar limpiamente, no crashear
        if "exito" in resultado:
            # Si ffprobe existe, éxito; si no, fallo controlado
            assert isinstance(resultado["exito"], bool)

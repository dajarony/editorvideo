# -*- coding: utf-8 -*-
"""Fixtures compartidos para todos los tests del sistema AEGS."""

import os
import sys
import json
import shutil
import tempfile
import pytest

# Añadir el directorio raíz del proyecto al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def pytest_collection_modifyitems(config, items):
    """Los tests marcados `internet` (Edge TTS real) solo corren con AEGS_TEST_INTERNET=1."""
    if os.environ.get("AEGS_TEST_INTERNET") == "1":
        return
    omitir = pytest.mark.skip(reason="necesita red: exporta AEGS_TEST_INTERNET=1 para ejecutarlo")
    for item in items:
        if "internet" in item.keywords:
            item.add_marker(omitir)


@pytest.fixture
def proyecto_temp(tmp_path):
    """Crea un proyecto temporal con estructura completa para testing."""
    # Crear estructura de carpetas
    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()
    musica_dir = tmp_path / "musica"
    musica_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    narracion_dir = output_dir / "narracion"
    narracion_dir.mkdir()

    # JSON del proyecto
    datos = {
        "titulo": "Test Project",
        "idioma": "es",
        "resolucion": "1920x1080",
        "fps": 30,
        "narrador": {
            "voz": "es-ES-AlvaroNeural",
            "velocidad": "+0%"
        },
        "musica": {
            "fuente": "archivo",
            "archivo": "musica/test_music.mp3",
            "volumen_base": 0.30,
            "volumen_durante_voz": 0.08,
            "fade_in_segundos": 1.0,
            "fade_out_segundos": 1.0
        },
        "subtitulos": {
            "generar": False,
            "fuente": "Arial",
            "tamano": 24
        },
        "transiciones": {
            "tipo_default": "crossfade",
            "duracion_default_segundos": 1.0
        },
        "escenas": [
            {
                "id": "escena_test_01",
                "clip": "clips/test_01.mp4",
                "clip_inicio_seg": 0,
                "clip_fin_seg": None,
                "texto_narracion": "Esta es una prueba del sistema de automontaje de vídeo.",
                "pausa_antes_seg": 1.0,
                "pausa_despues_seg": 1.0,
                "transicion_entrada": "fade_from_black",
                "transicion_salida": "crossfade"
            },
            {
                "id": "escena_test_02",
                "clip": "clips/test_02.mp4",
                "clip_inicio_seg": 0,
                "clip_fin_seg": None,
                "texto_narracion": "El sistema valida, narra, mezcla, monta y subtitula automáticamente.",
                "pausa_antes_seg": 0.5,
                "pausa_despues_seg": 1.5,
                "transicion_entrada": "crossfade",
                "transicion_salida": "fade_to_black"
            }
        ]
    }

    with open(tmp_path / "proyecto.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)

    return {"ruta": str(tmp_path), "datos": datos}


@pytest.fixture
def datos_proyecto_valido(proyecto_temp):
    """Devuelve solo el diccionario de datos del proyecto."""
    return proyecto_temp["datos"]


@pytest.fixture
def duraciones_fake(proyecto_temp):
    """Crea un narracion_duraciones.json falso para tests de módulos 2+."""
    duraciones = {
        "escena_test_01": {
            "archivo": "output/narracion/escena_test_01.mp3",
            "duracion_real_seg": 4.5
        },
        "escena_test_02": {
            "archivo": "output/narracion/escena_test_02.mp3",
            "duracion_real_seg": 6.2
        }
    }
    ruta = os.path.join(proyecto_temp["ruta"], "output", "narracion_duraciones.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(duraciones, f, indent=2)
    return duraciones

# -*- coding: utf-8 -*-
"""Tests — Un solo motor: la ventana, la CLI y los contratos ejecutan lo mismo.

Las casillas de la interfaz (o los flags de la CLI) se convierten en un contrato de
herramientas en un orden fijo, y ese contrato lo ejecuta el mismo ejecutor que los
contratos escritos a mano. Así una corrección en una herramienta vale para todos.
"""
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modulos import contrato_edicion as ce  # noqa: E402
from modulos import servicio_edicion as se  # noqa: E402
from modulos import superresolucion, utilidades  # noqa: E402


def _nombres(contrato):
    return [p["herramienta"] for p in contrato["herramientas"]]


class TestContratoDesdeOpciones:
    def test_todas_las_opciones_de_video_en_su_orden(self):
        config = {
            "cortar_silencios": True, "eliminar_muletillas": True, "color_grading": True,
            "estilo_color": "calido", "mejora_real": True, "nivel_mejora": "fuerte",
            "formato_vertical": True, "encuadre_vertical": "izquierda", "limpiar_voz": True,
            "nivel_voz": "suave", "subtitulos": True, "audio_fades": True, "esrgan": True,
            "modelo_esrgan": "realesrgan-x4plus-anime", "idioma": "es",
        }
        contrato = se.contrato_desde_config(config)
        assert _nombres(contrato) == [
            "cortar_silencios", "eliminar_muletillas", "color_grading", "mejora_real",
            "vertical_9_16", "limpiar_voz", "subtitulos", "fades_audio", "superresolucion_ia",
        ]
        params = {p["herramienta"]: p["parametros"] for p in contrato["herramientas"]}
        assert params["color_grading"] == {"estilo": "calido"}
        assert params["mejora_real"] == {"nivel": "fuerte"}
        assert params["vertical_9_16"]["encuadre"] == "izquierda"
        assert params["superresolucion_ia"] == {"modelo": "realesrgan-x4plus-anime"}
        assert ce.validar_contrato_herramientas(contrato)["valido"]

    def test_una_imagen_solo_recibe_lo_que_sirve_para_imagenes(self):
        config = {"tipo": "imagen", "cortar_silencios": True, "color_grading": True, "mejora_real": True,
                  "formato_vertical": True, "subtitulos": True, "audio_fades": True, "esrgan": True}
        assert _nombres(se.contrato_desde_config(config)) == ["mejora_real", "superresolucion_ia"]

    def test_sin_opciones_no_hay_pasos(self):
        assert se.contrato_desde_config({"mejora_real": False, "audio_fades": False})["herramientas"] == []


class TestProcesarUsaElEjecutorDeContratos:
    def test_procesar_ejecuta_el_contrato_y_avisa_del_progreso(self, tmp_path, monkeypatch):
        llamadas = []

        def falsa(nombre):
            def ejecutar(entrada, salida, params):
                llamadas.append(nombre)
                shutil.copy2(entrada, salida)
                return salida
            return ejecutar

        registro = {n: h.__class__(**{**h.__dict__, "ejecutar": falsa(n)}) for n, h in ce.REGISTRO_HERRAMIENTAS.items()}
        monkeypatch.setattr(ce, "REGISTRO_HERRAMIENTAS", registro)
        entrada = tmp_path / "v.mp4"
        entrada.write_text("x", encoding="utf-8")
        progreso = []
        res = se.procesar(str(entrada), str(tmp_path / "s.mp4"), {"cortar_silencios": True, "mejora_real": True},
                          al_progresar=lambda f, t: progreso.append(f))
        assert res["exito"], res
        assert llamadas == ["cortar_silencios", "mejora_real", "fades_audio"]
        assert progreso[0] == 0.0 and progreso[-1] == 1.0

    def test_aplicar_todas_mejoras_va_por_el_mismo_camino(self, tmp_path, monkeypatch):
        from modulos import mejoras

        visto = {}

        def procesar(entrada, salida, config, **kwargs):
            visto["config"] = config
            shutil.copy2(entrada, salida)
            return {"exito": True, "archivo": salida, "pasos_ejecutados": ["mejora_real"]}

        monkeypatch.setattr(se, "procesar", procesar)
        entrada = tmp_path / "v.mp4"
        entrada.write_text("x", encoding="utf-8")
        res = mejoras.aplicar_todas_mejoras(str(entrada), str(tmp_path / "s.mp4"), {"color_grading": False})
        assert res == {"exito": True, "archivo": str(tmp_path / "s.mp4"), "pasos": ["mejora_real"]}
        assert visto["config"]["color_grading"] is False


class TestSuperresolucion:
    def test_sin_real_esrgan_el_error_dice_donde_ponerlo(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AEGS_REALESRGAN", str(tmp_path / "no_existe.exe"))
        entrada = tmp_path / "foto.png"
        entrada.write_bytes(b"")
        with pytest.raises(RuntimeError, match="Real-ESRGAN"):
            superresolucion.ampliar_con_ia(str(entrada), str(tmp_path / "s.png"))

    def test_un_video_se_amplia_fotograma_a_fotograma_y_conserva_el_audio(self, tmp_path, monkeypatch):
        try:
            ffmpeg = shutil.which(utilidades.binario("ffmpeg"))
            ffprobe = shutil.which(utilidades.binario("ffprobe"))
        except FileNotFoundError as e:
            pytest.skip(f"necesita FFmpeg: {e}")
        if not (ffmpeg and ffprobe):
            pytest.skip("necesita FFmpeg y FFprobe")
        entrada = tmp_path / "v.mp4"
        subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=10:duration=1",
                        "-f", "lavfi", "-i", "sine=duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", str(entrada)], check=True)

        def esrgan_falso(carpeta_entrada, carpeta_salida, modelo, escala=4):
            # Hace lo que haría Real-ESRGAN: cada fotograma, `escala` veces más grande, con el mismo nombre.
            for nombre in os.listdir(carpeta_entrada):
                subprocess.run([ffmpeg, "-v", "error", "-y", "-i", os.path.join(carpeta_entrada, nombre),
                                "-vf", f"scale=iw*{escala}:ih*{escala}", os.path.join(carpeta_salida, nombre)],
                               check=True)

        monkeypatch.setattr(superresolucion, "_ejecutar_esrgan", esrgan_falso)
        monkeypatch.setattr(superresolucion, "ejecutable_esrgan", lambda: "falso")
        salida = tmp_path / "s.mp4"
        superresolucion.ampliar_con_ia(str(entrada), str(salida))
        info = subprocess.run([ffprobe, "-v", "error", "-show_entries", "stream=codec_type,width,height",
                               "-of", "csv=p=0", str(salida)], capture_output=True, text=True, check=True).stdout
        assert "video,256,192" in info.replace(" ", "")
        assert "audio" in info

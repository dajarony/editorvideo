# -*- coding: utf-8 -*-
"""Interprete simple de comandos de edicion en espanol.

Este modulo convierte ordenes del usuario en una configuracion estructurada.
No llama a ningun servicio externo: es una base local y determinista para el
modo editor por comandos.
"""

import re
from dataclasses import dataclass, asdict


@dataclass
class ConfigEdicion:
    cortar_silencios: bool = False
    eliminar_muletillas: bool = False
    color_grading: bool = False
    estilo_color: str = "natural_claro"
    audio_fades: bool = True
    mejora_real: bool = True
    nivel_mejora: str = "media"
    formato_vertical: bool = False
    subtitulos: bool = False
    limpiar_voz: bool = False
    nivel_voz: str = "media"
    esrgan: bool = False
    modelo_esrgan: str = "realesrgan-x4plus"


def parsear_comando_edicion(texto: str) -> dict:
    """Convierte texto libre en ajustes de edicion soportados por la app."""
    t = " ".join((texto or "").lower().split())
    cfg = ConfigEdicion()
    acciones = []
    avisos = []

    if not t:
        return {"config": asdict(cfg), "acciones": acciones, "avisos": ["Comando vacio."]}

    if any(p in t for p in ("sin silencio", "quita silenc", "elimina silenc", "corta silenc")):
        cfg.cortar_silencios = True
        acciones.append("cortar silencios")
    if any(p in t for p in ("no cortes silencio", "mantener silenc", "deja los silenc")):
        cfg.cortar_silencios = False
        acciones.append("mantener silencios")

    if any(p in t for p in ("muletilla", "eh", "umm", "mmm", "relleno")):
        cfg.eliminar_muletillas = True
        acciones.append("eliminar muletillas")

    if any(p in t for p in ("vertical", "tiktok", "reels", "shorts", "9:16", "9/16")):
        cfg.formato_vertical = True
        acciones.append("formato vertical 9:16")

    if any(p in t for p in ("quita ruido", "quitar ruido", "sin ruido", "limpia la voz",
                            "limpiar voz", "limpia el audio", "limpiar audio",
                            "quita musica", "quita música", "sin musica", "sin música",
                            "solo voz", "solo la voz", "aisla voz", "aislar voz",
                            "realza voz", "realzar voz")):
        cfg.limpiar_voz = True
        acciones.append("aislar voz / quitar musica")
    if any(p in t for p in ("quita la musica", "quitar la musica", "quita la música",
                            "quitar la música", "elimina la musica", "elimina la música")):
        cfg.limpiar_voz = True
        if "aislar voz / quitar musica" not in acciones:
            acciones.append("aislar voz / quitar musica")

    if "voz suave" in t or "limpieza suave" in t:
        cfg.nivel_voz = "suave"
    if "voz fuerte" in t or "limpieza fuerte" in t or "mucho ruido" in t:
        cfg.nivel_voz = "fuerte"

    nego_subs = any(p in t for p in ("sin subtitulo", "sin subtítulo", "no subtitulo",
                                     "no subtítulo", "quita subtitulo", "quita subtítulo"))
    if nego_subs:
        cfg.subtitulos = False
        acciones.append("sin subtitulos")
    elif any(p in t for p in ("subtitulo", "subtítulo", "subtitula", "subtítula",
                              "pon texto", "texto en pantalla")):
        cfg.subtitulos = True
        acciones.append("subtitulos automaticos")

    if any(p in t for p in ("sin mejorar", "no mejores", "original")):
        cfg.mejora_real = False
        acciones.append("sin mejora visual")
    if any(p in t for p in ("mejora", "nitid", "calidad", "brillo", "claro", "vivo", "color")):
        cfg.mejora_real = True
        acciones.append("mejora visual real")

    if any(p in t for p in ("suave", "ligero", "natural")):
        cfg.nivel_mejora = "suave"
    if any(p in t for p in ("media", "equilibr", "normal")):
        cfg.nivel_mejora = "media"
    if any(p in t for p in ("fuerte", "maxim", "potente", "mas nitido", "más nitido")):
        cfg.nivel_mejora = "fuerte"

    if any(p in t for p in ("cinematic", "pelicula", "película")):
        cfg.color_grading = True
        cfg.estilo_color = "cinematico"
        acciones.append("color cinematografico")
    elif "calido" in t or "cálido" in t:
        cfg.color_grading = True
        cfg.estilo_color = "calido"
        acciones.append("color calido")
    elif "neutro" in t:
        cfg.color_grading = True
        cfg.estilo_color = "neutro"
        acciones.append("color neutro")
    elif any(p in t for p in ("claro", "vivo", "natural")):
        cfg.estilo_color = "natural_claro"

    if any(p in t for p in ("sin color grading", "sin grading", "no color grading")):
        cfg.color_grading = False
        acciones.append("sin color grading extra")

    if any(p in t for p in ("ia x4", "x4", "super resol", "superresol", "4k")):
        cfg.esrgan = True
        acciones.append("super resolucion IA x4")
        avisos.append("IA x4 puede tardar mucho en videos largos.")

    if any(p in t for p in ("anime", "dibujo", "animacion", "animación")):
        cfg.modelo_esrgan = "realesrgan-x4plus-anime"

    if not acciones:
        acciones.append("mejora visual real")
        avisos.append("No detecte una orden concreta; aplico mejora natural por defecto.")

    return {"config": asdict(cfg), "acciones": acciones, "avisos": avisos}


_PATRON_TIEMPO = r"\d+(?::\d{1,2}){0,2}(?:[\.,]\d+)?"


def _segundos(valor: str) -> float:
    texto = str(valor).strip().replace(",", ".")
    partes = texto.split(":")
    if len(partes) == 1:
        return float(partes[0])
    if len(partes) == 2:
        return float(partes[0]) * 60 + float(partes[1])
    if len(partes) == 3:
        return float(partes[0]) * 3600 + float(partes[1]) * 60 + float(partes[2])
    raise ValueError(f"tiempo invalido: {valor}")


def _inicio_en_texto(texto: str) -> float | None:
    patrones = [
        rf"\ben\s+(?:el\s+)?(?:segundo\s+)?({_PATRON_TIEMPO})",
        rf"\bsegundo\s+({_PATRON_TIEMPO})",
        rf"\bminuto\s+({_PATRON_TIEMPO})",
    ]
    for patron in patrones:
        m = re.search(patron, texto)
        if m:
            valor = _segundos(m.group(1))
            if "minuto" in m.group(0) and ":" not in m.group(1):
                valor *= 60
            return valor
    return None


def _duracion_en_texto(texto: str, default: float) -> float:
    m = re.search(rf"\bdurante\s+({_PATRON_TIEMPO})\s*(?:s|seg|segundo|segundos)?", texto)
    if not m:
        return default
    return _segundos(m.group(1))


def _posicion_en_texto(texto: str, posiciones: list[str], default: str) -> str:
    mapa = {
        "arriba izquierda": "arriba_izq",
        "arriba derecha": "arriba_der",
        "abajo izquierda": "abajo_izq",
        "abajo derecha": "abajo_der",
        "arriba": "arriba",
        "centro": "centro",
        "abajo": "abajo",
    }
    for frase, valor in mapa.items():
        if frase in texto and valor in posiciones:
            return valor
    return default


def _intensidad_en_texto(texto: str) -> str:
    if any(p in texto for p in ("suave", "ligero", "poco")):
        return "suave"
    if any(p in texto for p in ("fuerte", "potente", "mucho")):
        return "fuerte"
    return "media"


def _texto_entre_comillas(fragmento: str) -> str | None:
    m = re.search(r"[\"']([^\"']+)[\"']", fragmento)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:texto|frase)\s+(.+?)(?:\s+en\s+|\s+durante\s+|$)", fragmento)
    if m:
        return m.group(1).strip(" :.-")
    return None


def parsear_comando_contrato(texto: str) -> dict:
    """Convierte ordenes por tiempo en un contrato de herramientas.

    Ejemplos:
    - en el segundo 12 pon texto "Idea clave" durante 3 segundos
    - en 00:18 zoom suave durante 2 segundos
    - corta de 7 a 9
    - en 00:25 pon imagen logo.png arriba derecha durante 4 segundos
    """
    original = texto or ""
    # Se conserva la version original (con mayusculas) para el texto a mostrar;
    # la version en minusculas solo se usa para detectar palabras clave.
    fragmentos = [
        f.strip()
        for f in re.split(r"[\n;]+", original)
        if f.strip()
    ]
    herramientas = []
    acciones = []
    avisos = []

    for frag_orig in fragmentos:
        frag = frag_orig.lower()
        corte = re.search(
            rf"(?:corta|cortar|quita|quitar|elimina|eliminar)\s+"
            rf"(?:desde\s+|de\s+|del\s+)?({_PATRON_TIEMPO})\s+"
            rf"(?:a|al|hasta)\s+({_PATRON_TIEMPO})",
            frag,
        )
        if corte:
            inicio = _segundos(corte.group(1))
            fin = _segundos(corte.group(2))
            herramientas.append({
                "herramienta": "corte",
                "parametros": {"inicio": inicio, "fin": fin},
            })
            acciones.append(f"corte {inicio:g}-{fin:g}s")
            continue

        inicio = _inicio_en_texto(frag)
        if inicio is None:
            avisos.append(f"No detecte tiempo en: {frag[:60]}")
            continue

        if "zoom" in frag or "acerca" in frag:
            dur = _duracion_en_texto(frag, 2.0)
            intensidad = _intensidad_en_texto(frag)
            herramientas.append({
                "herramienta": "zoom",
                "parametros": {
                    "inicio": inicio,
                    "duracion": dur,
                    "intensidad": intensidad,
                },
            })
            acciones.append(f"zoom {intensidad} en {inicio:g}s")
            continue

        if "imagen" in frag or "logo" in frag:
            img = re.search(
                r"([^\s\"']+\.(?:png|jpg|jpeg|webp|bmp))", frag_orig, re.IGNORECASE
            )
            if not img:
                avisos.append(f"No detecte archivo de imagen en: {frag[:60]}")
                continue
            dur = _duracion_en_texto(frag, 4.0)
            pos = _posicion_en_texto(
                frag,
                ["arriba_izq", "arriba_der", "centro", "abajo_izq", "abajo_der"],
                "arriba_der",
            )
            herramientas.append({
                "herramienta": "imagen",
                "parametros": {
                    "archivo": img.group(1),
                    "inicio": inicio,
                    "duracion": dur,
                    "posicion": pos,
                },
            })
            acciones.append(f"imagen en {inicio:g}s")
            continue

        if "texto" in frag or "frase" in frag or "pon " in frag:
            texto_accion = _texto_entre_comillas(frag_orig)
            if not texto_accion:
                avisos.append(f"No detecte texto a mostrar en: {frag[:60]}")
                continue
            dur = _duracion_en_texto(frag, 3.0)
            pos = _posicion_en_texto(frag, ["arriba", "centro", "abajo"], "abajo")
            herramientas.append({
                "herramienta": "texto",
                "parametros": {
                    "texto": texto_accion,
                    "inicio": inicio,
                    "duracion": dur,
                    "posicion": pos,
                },
            })
            acciones.append(f"texto en {inicio:g}s")
            continue

        avisos.append(f"No detecte herramienta por tiempo en: {frag[:60]}")

    if not herramientas and not avisos:
        avisos.append("Comando vacio.")

    return {
        "contrato": {"herramientas": herramientas},
        "acciones": acciones,
        "avisos": avisos,
    }

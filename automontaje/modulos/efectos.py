# -*- coding: utf-8 -*-
"""Efectos de edicion por momento concreto del video.

Herramientas que actuan en un instante o tramo del video:
- cortar_fragmento : quita un trozo (inicio -> fin)
- superponer_texto : texto en pantalla durante un tramo
- superponer_imagen: imagen/logo encima durante un tramo
- aplicar_zoom     : zoom suave en un momento

Todas re-codifican a H.264/yuv420p para maxima compatibilidad.
"""

import os
import json
import subprocess
from .proceso import ejecutar_proceso

from .utilidades import binario, logger


# ─── Helpers ────────────────────────────────────────────

ENCODE_VIDEO = [
    "-c:v", "libx264", "-preset", "fast", "-crf", "20",
    "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
    "-movflags", "+faststart",
]


def _run(cmd: list, descripcion: str, cwd: str = None) -> None:
    """Ejecuta FFmpeg y lanza excepcion clara si falla."""
    res = ejecutar_proceso(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore",
        cwd=cwd
    )
    if res.returncode != 0:
        detalle = (res.stderr or res.stdout or "").strip()[-700:]
        raise RuntimeError(f"FFmpeg fallo en '{descripcion}':\n{detalle}")


def _info_video(ruta: str) -> tuple:
    """Devuelve (duracion, ancho, alto, fps) de un video."""
    res = ejecutar_proceso(
        [binario("ffprobe"), "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", ruta],
        capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    data = json.loads(res.stdout)
    duracion = float(data["format"].get("duration", 0.0))
    ancho = alto = 0
    fps = 30.0
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            ancho = int(s.get("width", 0))
            alto = int(s.get("height", 0))
            try:
                n, d = s.get("r_frame_rate", "30/1").split("/")
                fps = float(n) / float(d) if float(d) else 30.0
            except (ValueError, ZeroDivisionError):
                fps = 30.0
            break
    return duracion, ancho, alto, fps


def _tiene_audio(ruta: str) -> bool:
    """Indica si el video tiene pista de audio."""
    res = ejecutar_proceso(
        [binario("ffprobe"), "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", ruta],
        capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    return "audio" in (res.stdout or "")


def _fuente_sistema() -> str | None:
    """Localiza una fuente TTF del sistema para drawtext."""
    candidatas = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for ruta in candidatas:
        if os.path.exists(ruta):
            return ruta
    return None


# ─── 1. Cortar fragmento ────────────────────────────────

def tramos_conservados_tras_corte(duracion: float, inicio: float, fin: float) -> list:
    """Tramos que conserva cortar_fragmento (los trozos de menos de 0,05 s no se conservan)."""
    inicio, fin = max(0.0, float(inicio)), min(duracion, float(fin))
    tramos = []
    if inicio > 0.05:
        tramos.append((0.0, inicio))
    if fin < duracion - 0.05:
        tramos.append((fin, duracion))
    return tramos


def cortar_fragmento(
    ruta_entrada: str,
    ruta_salida: str,
    inicio: float,
    fin: float
) -> str:
    """Elimina el tramo [inicio, fin] y une el resto del video."""
    duracion, _, _, _ = _info_video(ruta_entrada)
    inicio = max(0.0, float(inicio))
    fin = min(duracion, float(fin))
    if fin <= inicio:
        raise RuntimeError("corte: 'fin' debe ser mayor que 'inicio'.")
    if inicio <= 0.05 and fin >= duracion - 0.05:
        raise RuntimeError("corte: el tramo abarca todo el video.")

    con_audio = _tiene_audio(ruta_entrada)
    logger.info(f"  ✂  Cortando fragmento {inicio:.2f}s → {fin:.2f}s...")

    partes_v, partes_a, n = [], [], 0
    # Parte inicial [0, inicio]
    if inicio > 0.05:
        partes_v.append(f"[0:v]trim=0:{inicio:.3f},setpts=PTS-STARTPTS[v{n}]")
        if con_audio:
            partes_a.append(f"[0:a]atrim=0:{inicio:.3f},asetpts=PTS-STARTPTS[a{n}]")
        n += 1
    # Parte final [fin, duracion]
    if fin < duracion - 0.05:
        partes_v.append(f"[0:v]trim=start={fin:.3f},setpts=PTS-STARTPTS[v{n}]")
        if con_audio:
            partes_a.append(f"[0:a]atrim=start={fin:.3f},asetpts=PTS-STARTPTS[a{n}]")
        n += 1

    if n == 1:
        # Solo queda un tramo: no hace falta concat
        cadena = ";".join(partes_v + partes_a)
        mapa = ["-map", "[v0]"]
        if con_audio:
            mapa += ["-map", "[a0]"]
    else:
        if con_audio:
            inter = "".join(f"[v{i}][a{i}]" for i in range(n))
            concat = f"{inter}concat=n={n}:v=1:a=1[v][a]"
            mapa = ["-map", "[v]", "-map", "[a]"]
        else:
            inter = "".join(f"[v{i}]" for i in range(n))
            concat = f"{inter}concat=n={n}:v=1:a=0[v]"
            mapa = ["-map", "[v]"]
        cadena = ";".join(partes_v + partes_a + [concat])

    cmd = [binario("ffmpeg"), "-y", "-i", ruta_entrada, "-filter_complex", cadena]
    cmd += mapa + ENCODE_VIDEO
    if con_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-ar", "44100"]
    cmd.append(ruta_salida)
    _run(cmd, "cortar_fragmento")
    logger.info(f"  ✅ Fragmento cortado → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── 2. Superponer texto ────────────────────────────────

_POS_TEXTO_Y = {
    "arriba": "h*0.10",
    "centro": "(h-text_h)/2",
    "abajo":  "h*0.82",
}


def superponer_texto(
    ruta_entrada: str,
    ruta_salida: str,
    texto: str,
    inicio: float,
    duracion: float = 3.0,
    posicion: str = "abajo"
) -> str:
    """Pone un texto en pantalla durante [inicio, inicio+duracion]."""
    fuente = _fuente_sistema()
    if not fuente:
        raise RuntimeError(
            "No se encontro ninguna fuente del sistema para el texto."
        )
    _, _, alto, _ = _info_video(ruta_entrada)
    inicio = max(0.0, float(inicio))
    fin = inicio + max(0.3, float(duracion))
    y = _POS_TEXTO_Y.get(posicion, _POS_TEXTO_Y["abajo"])
    fontsize = max(20, alto // 20)

    carpeta = os.path.dirname(os.path.abspath(ruta_salida)) or "."
    txt_tmp = os.path.join(carpeta, "_tmp_drawtext.txt")
    with open(txt_tmp, "w", encoding="utf-8") as f:
        f.write(texto)

    # Rutas para el filtro: relativa para el textfile, absoluta escapada
    # para la fuente (los ':' de Windows rompen el parser de filtros).
    fuente_esc = fuente.replace("\\", "/").replace(":", "\\:")
    filtro = (
        f"drawtext=textfile='_tmp_drawtext.txt':"
        f"fontfile='{fuente_esc}':"
        f"fontcolor=white:fontsize={fontsize}:"
        f"box=1:boxcolor=black@0.55:boxborderw=14:"
        f"x=(w-text_w)/2:y={y}:"
        f"enable='between(t,{inicio:.3f},{fin:.3f})'"
    )
    logger.info(f"  💬 Superponiendo texto en {inicio:.2f}s ({duracion:.1f}s)...")
    con_audio = _tiene_audio(ruta_entrada)
    cmd = [binario("ffmpeg"), "-y", "-i", os.path.abspath(ruta_entrada),
           "-vf", filtro] + ENCODE_VIDEO
    cmd += ["-c:a", "copy"] if con_audio else []
    cmd.append(os.path.abspath(ruta_salida))
    try:
        _run(cmd, "superponer_texto", cwd=carpeta)
    finally:
        if os.path.exists(txt_tmp):
            try:
                os.remove(txt_tmp)
            except OSError:
                pass
    logger.info(f"  ✅ Texto superpuesto → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── 3. Superponer imagen ───────────────────────────────

_POS_IMAGEN = {
    "arriba_izq": "20:20",
    "arriba_der": "W-w-20:20",
    "centro":     "(W-w)/2:(H-h)/2",
    "abajo_izq":  "20:H-h-20",
    "abajo_der":  "W-w-20:H-h-20",
}


def superponer_imagen(
    ruta_entrada: str,
    ruta_salida: str,
    archivo: str,
    inicio: float,
    duracion: float = 4.0,
    posicion: str = "arriba_der",
    escala: float = 0.28
) -> str:
    """Superpone una imagen/logo durante [inicio, inicio+duracion]."""
    if not os.path.exists(archivo):
        raise RuntimeError(f"No existe la imagen: {archivo}")
    duracion_v, ancho, _, _ = _info_video(ruta_entrada)
    inicio = max(0.0, float(inicio))
    fin = inicio + max(0.3, float(duracion))
    pos = _POS_IMAGEN.get(posicion, _POS_IMAGEN["arriba_der"])
    ancho_img = max(40, int(ancho * float(escala)))

    filtro = (
        f"[1:v]scale={ancho_img}:-1[img];"
        f"[0:v][img]overlay={pos}:"
        f"enable='between(t,{inicio:.3f},{fin:.3f})'[v]"
    )
    logger.info(f"  🖼  Superponiendo imagen en {inicio:.2f}s ({duracion:.1f}s)...")
    con_audio = _tiene_audio(ruta_entrada)
    cmd = [binario("ffmpeg"), "-y", "-i", ruta_entrada, "-i", archivo,
           "-filter_complex", filtro, "-map", "[v]"]
    if con_audio:
        cmd += ["-map", "0:a"]
    cmd += ENCODE_VIDEO
    if con_audio:
        cmd += ["-c:a", "copy"]
    cmd.append(ruta_salida)
    _run(cmd, "superponer_imagen")
    logger.info(f"  ✅ Imagen superpuesta → {os.path.basename(ruta_salida)}")
    return ruta_salida


# ─── 4. Zoom en un momento ──────────────────────────────

_ZOOM_FACTOR = {"suave": 1.08, "media": 1.15, "fuerte": 1.25}


def aplicar_zoom(
    ruta_entrada: str,
    ruta_salida: str,
    inicio: float,
    duracion: float = 2.0,
    intensidad: str = "media"
) -> str:
    """Aplica un zoom (punch-in) durante [inicio, inicio+duracion]."""
    _, ancho, alto, fps = _info_video(ruta_entrada)
    inicio = max(0.0, float(inicio))
    fin = inicio + max(0.3, float(duracion))
    factor = _ZOOM_FACTOR.get(intensidad, _ZOOM_FACTOR["media"])

    f_ini = int(inicio * fps)
    f_fin = int(fin * fps)
    # zoompan con d=1: procesa fotograma a fotograma sin re-temporizar.
    filtro = (
        f"zoompan="
        f"z='if(between(in,{f_ini},{f_fin}),{factor},1.0)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:fps={fps:.4f}:s={ancho}x{alto}"
    )
    logger.info(f"  🔍 Zoom '{intensidad}' en {inicio:.2f}s ({duracion:.1f}s)...")
    con_audio = _tiene_audio(ruta_entrada)
    cmd = [binario("ffmpeg"), "-y", "-i", ruta_entrada, "-vf", filtro] + ENCODE_VIDEO
    if con_audio:
        cmd += ["-c:a", "copy"]
    cmd.append(ruta_salida)
    _run(cmd, "aplicar_zoom")
    logger.info(f"  ✅ Zoom aplicado → {os.path.basename(ruta_salida)}")
    return ruta_salida

# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════
SUME DOCBLOCK v2.0
═══════════════════════════════════════════════════════════
Archivo: modulos/utilidades.py
Tipo: Lógica → Utilidades Compartidas
Dependencias: 3 (subprocess, json, os, logging)

Entradas:
- Rutas de archivos multimedia.

Acciones:
- Ejecutar FFprobe de manera segura para obtener metadatos.
- Proveer logging dual (consola + archivo) para todo el sistema.

Salidas:
- Diccionarios estandarizados con duración, resolución y códec.
═══════════════════════════════════════════════════════════
"""

import subprocess
import json
import os
import logging
import shutil
import hashlib
import re


ID_ESCENA_RE = re.compile(r"^[A-Za-z0-9_-]+$")
RESOLUCION_RE = re.compile(r"^([1-9][0-9]{1,4})x([1-9][0-9]{1,4})$")
VELOCIDAD_TTS_RE = re.compile(r"^[+-](?:[0-9]|[1-9][0-9]|100)%$")
FUENTE_SUBTITULOS_RE = re.compile(r"^[A-Za-z0-9 _-]{1,64}$")

# ─── Logger Global ──────────────────────────────────────

def configurar_logger() -> logging.Logger:
    """Crea el logger base con salida a consola.

    El FileHandler se añade después con `activar_log_archivo()`
    cuando se conoce la ruta del proyecto.
    """
    log = logging.getLogger("AEGS")
    log.setLevel(logging.DEBUG)

    # Evitar duplicar handlers si se llama más de una vez
    if not log.handlers:
        consola = logging.StreamHandler()
        consola.setLevel(logging.INFO)
        formato = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        consola.setFormatter(formato)
        log.addHandler(consola)

    return log


logger = configurar_logger()


def ruta_segura_proyecto(ruta_proyecto: str, ruta_relativa: str) -> str:
    """Resuelve una ruta de proyecto y evita escapes fuera de la carpeta base."""
    if not isinstance(ruta_relativa, str) or not ruta_relativa.strip():
        raise ValueError("Ruta vacia o invalida.")
    if os.path.isabs(ruta_relativa):
        raise ValueError(f"Las rutas absolutas no estan permitidas: {ruta_relativa}")

    base = os.path.abspath(ruta_proyecto)
    candidata = os.path.abspath(os.path.join(base, ruta_relativa))
    try:
        comun = os.path.commonpath([base, candidata])
    except ValueError:
        comun = ""
    if comun != base:
        raise ValueError(f"La ruta sale de la carpeta del proyecto: {ruta_relativa}")
    return candidata


def validar_id_escena(valor: str) -> bool:
    """True si el ID es seguro para usarlo como clave y nombre de archivo."""
    return isinstance(valor, str) and bool(ID_ESCENA_RE.fullmatch(valor))


def validar_resolucion(valor: str) -> bool:
    """Valida resoluciones tipo 1920x1080 con limites razonables."""
    if not isinstance(valor, str):
        return False
    match = RESOLUCION_RE.fullmatch(valor)
    if not match:
        return False
    ancho, alto = (int(match.group(1)), int(match.group(2)))
    return 16 <= ancho <= 7680 and 16 <= alto <= 4320


def normalizar_fps(valor) -> int:
    """Devuelve un FPS entero seguro o lanza ValueError."""
    if isinstance(valor, bool):
        raise ValueError("fps debe ser numerico.")
    fps = int(valor)
    if fps < 1 or fps > 120:
        raise ValueError("fps debe estar entre 1 y 120.")
    return fps


def validar_velocidad_tts(valor: str) -> bool:
    """Valida rates de Edge TTS como +0%, -5% o +20%."""
    return isinstance(valor, str) and bool(VELOCIDAD_TTS_RE.fullmatch(valor))


def validar_fuente_subtitulos(valor: str) -> bool:
    """Valida nombres simples de fuente para force_style de FFmpeg."""
    return isinstance(valor, str) and bool(FUENTE_SUBTITULOS_RE.fullmatch(valor))


def activar_log_archivo(ruta_proyecto: str, carpeta_logs: str, archivo_log: str):
    """Añade un FileHandler al logger para guardar logs en disco.

    Args:
        ruta_proyecto: Ruta base del proyecto del usuario.
        carpeta_logs: Nombre de la subcarpeta de logs (ej. 'logs').
        archivo_log: Nombre del archivo de log (ej. 'proceso.log').
    """
    ruta_logs = os.path.join(ruta_proyecto, carpeta_logs)
    os.makedirs(ruta_logs, exist_ok=True)

    ruta_completa = os.path.join(ruta_logs, archivo_log)
    file_handler = logging.FileHandler(ruta_completa, encoding='utf-8', mode='w')
    file_handler.setLevel(logging.DEBUG)
    formato = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formato)
    logger.addHandler(file_handler)
    logger.debug(f"Log de archivo activado en: {ruta_completa}")


# ─── FFprobe Unificado (Ajuste 1) ──────────────────────

def obtener_info_media(ruta_archivo: str) -> dict:
    """Extrae duración, resolución y códec de un archivo multimedia.

    Usa FFprobe internamente. Una sola función para todo el sistema
    (validador, narración, montaje).

    Args:
        ruta_archivo: Ruta absoluta al archivo multimedia.

    Returns:
        dict con claves: duracion (float), resolucion (str), codec (str).
        Si hay error, devuelve dict con clave 'error'.
    """
    if not os.path.exists(ruta_archivo):
        return {"error": f"Archivo no encontrado: {ruta_archivo}"}

    comando = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        ruta_archivo
    ]

    try:
        resultado = subprocess.run(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        datos = json.loads(resultado.stdout)

        info = {
            "duracion": float(datos.get("format", {}).get("duration", 0.0)),
            "resolucion": "N/A",
            "codec": "N/A"
        }

        for stream in datos.get("streams", []):
            if stream.get("codec_type") == "video":
                info["resolucion"] = f"{stream.get('width', 0)}x{stream.get('height', 0)}"
                info["codec"] = stream.get("codec_name", "N/A")
                break
            elif stream.get("codec_type") == "audio" and info["codec"] == "N/A":
                info["codec"] = stream.get("codec_name", "N/A")

        return info

    except FileNotFoundError:
        logger.error(
            "FFprobe no encontrado. Asegúrate de que FFmpeg esté "
            "instalado y accesible en el PATH del sistema."
        )
        return {"error": "ffprobe no encontrado en PATH"}
    except subprocess.CalledProcessError as e:
        logger.error(f"FFprobe falló para '{ruta_archivo}': {e.stderr}")
        return {"error": f"ffprobe error: {e.stderr}"}
    except Exception as e:
        logger.error(f"Error inesperado al analizar media: {e}")
        return {"error": str(e)}


# ─── Verificación de Dependencias Externas ──────────────

def verificar_ffmpeg() -> dict:
    """Comprueba que ffmpeg y ffprobe están instalados y accesibles.

    Returns:
        dict con exito (bool), errores (list) y versiones (dict).
    """
    errores = []
    versiones = {}

    for binario in ("ffmpeg", "ffprobe"):
        ruta = shutil.which(binario)
        if ruta is None:
            errores.append(
                f"'{binario}' no encontrado en PATH. "
                f"Instala FFmpeg: https://ffmpeg.org/download.html"
            )
            continue
        try:
            res = subprocess.run(
                [binario, "-version"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, check=True, timeout=10
            )
            primera_linea = res.stdout.splitlines()[0] if res.stdout else "desconocida"
            versiones[binario] = primera_linea
        except Exception as e:
            errores.append(f"Error ejecutando '{binario}': {e}")

    return {"exito": not errores, "errores": errores, "versiones": versiones}


# ─── Hash para Caché TTS ────────────────────────────────

def hash_tts(texto: str, voz: str, velocidad: str) -> str:
    """Genera un hash estable de los parámetros de una narración.

    Si los tres campos no cambian, el MP3 generado será el mismo y se
    puede reutilizar desde caché en lugar de regenerarlo con Edge TTS.

    Args:
        texto: Texto de la narración.
        voz: Identificador de voz Edge TTS.
        velocidad: Ajuste de velocidad ('+0%', '-5%', etc.).

    Returns:
        Hash SHA-1 hexadecimal (40 chars).
    """
    payload = f"{voz}||{velocidad}||{texto}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


# ─── Limpieza de Temporales ─────────────────────────────

def limpiar_carpeta_temporal(ruta_proyecto: str, carpeta_temp: str):
    """Elimina la carpeta de clips temporales procesados.

    Se ejecuta al final de un renderizado exitoso para liberar disco.

    Args:
        ruta_proyecto: Ruta base del proyecto.
        carpeta_temp: Subcarpeta de temporales (ej. 'output/temp_clips').
    """
    ruta = os.path.join(ruta_proyecto, carpeta_temp)
    if os.path.isdir(ruta):
        try:
            shutil.rmtree(ruta)
            logger.info(f"Temporales eliminados: {ruta}")
        except OSError as e:
            logger.warning(f"No se pudieron limpiar temporales: {e}")

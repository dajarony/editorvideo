"""SUME DOCBLOCK: ejecucion cancelable y avance medido de procesos multimedia.

Entradas: comando y contexto de un trabajo. Salidas: CompletedProcess o Cancelado.
Cada trabajo posee su evento; cancelar uno no interrumpe otros trabajos.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import os
import re
import subprocess
import threading
import time


class Cancelado(Exception):
    pass


class ControlProceso:
    def __init__(self, al_progresar=None):
        self.evento = threading.Event()
        self.al_progresar = al_progresar or (lambda fraccion, texto: None)
        self.indice = 0
        self.total = 1
        self.duracion = 0
        self.texto = "Procesando"

    def cancelar(self):
        self.evento.set()

    def comprobar(self):
        if self.evento.is_set():
            raise Cancelado("Proceso cancelado; no se publica una salida parcial.")

    def avance(self, segundos):
        if self.duracion > 0:
            parcial = min(0.99, max(0, segundos / self.duracion))
            self.al_progresar((self.indice + parcial) / self.total,
                              f"{self.texto} · {segundos:.1f}/{self.duracion:.1f} s")


_control = ContextVar("aegs_control", default=None)


@contextmanager
def contexto(control):
    token = _control.set(control)
    try:
        if control:
            control.comprobar()
        yield
    finally:
        _control.reset(token)


def comprobar_cancelacion():
    control = _control.get()
    if control:
        control.comprobar()


def ejecutar_proceso(comando, **kwargs):
    """Compatible con run(capture_output=True); sin contexto conserva el comportamiento.

La cancelacion detiene FFmpeg y Real-ESRGAN. Las llamadas en memoria a modelos
comprueban la cancelacion entre fases; no se interrumpe una inferencia nativa.
"""
    control = _control.get()
    if control is None:
        return subprocess.run(comando, **kwargs)
    control.comprobar()
    cmd = list(comando)
    es_render = (os.path.basename(str(cmd[0])).lower().startswith("ffmpeg")
                 and "-i" in cmd and cmd[-1] != "-" and not str(cmd[-1]).startswith("pipe:"))
    if es_render:
        cmd[1:1] = ["-progress", "pipe:1", "-nostats"]
    opciones = dict(kwargs)
    opciones.pop("capture_output", None)
    comprobar = opciones.pop("check", False)
    limite = opciones.pop("timeout", None)
    opciones.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if os.name == "nt":
        opciones.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    inicio = time.monotonic()
    with subprocess.Popen(cmd, **opciones) as proceso:
        try:
            while True:
                control.comprobar()
                if limite is not None and time.monotonic() - inicio > limite:
                    raise subprocess.TimeoutExpired(cmd, limite)
                try:
                    stdout, stderr = proceso.communicate(timeout=0.1)
                    break
                except subprocess.TimeoutExpired as parcial:
                    if es_render and parcial.stdout:
                        datos = parcial.stdout.decode("utf-8", "replace") if isinstance(parcial.stdout, bytes) else parcial.stdout
                        tiempos = re.findall(r"out_time_us=(\d+)", datos)
                        if tiempos:
                            control.avance(int(tiempos[-1]) / 1_000_000)
        except BaseException:
            proceso.kill()
            proceso.communicate()
            raise
    control.comprobar()
    resultado = subprocess.CompletedProcess(cmd, proceso.returncode, stdout, stderr)
    if comprobar:
        resultado.check_returncode()
    return resultado

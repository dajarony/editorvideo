"""La ventana recibe el avance del motor como (fracción, texto)."""
import pytest

pytest.importorskip("customtkinter")

from interfaz import App


class Boton:
    def configure(self, **kwargs):
        pass


class Barra:
    def set(self, valor):
        assert isinstance(valor, (float, int))


class VentanaFalsa:
    _avisar_progreso = App._avisar_progreso
    _iniciar_trabajo = App._iniciar_trabajo
    _hilo_contrato = App._hilo_contrato

    def __init__(self):
        self.btn_procesar = Boton()
        self.btn_seleccionar_archivo = Boton()
        self.btn_preview = Boton()
        self.btn_cancelar = Boton()
        self.btn_ejecutar_contrato = Boton()
        self.barra = Barra()
        self.estados = []
        self.control_actual = None

    def after(self, _delay, callback):
        callback()

    def _estado(self, texto, progreso=None):
        assert isinstance(texto, str)
        self.estados.append((texto, progreso))
        if progreso is not None:
            self.barra.set(progreso)

    def _ruta_salida_unica(self, ruta):
        return ruta

    def _terminar_trabajo(self):
        pass


def test_avance_de_ffmpeg_llega_con_texto_y_fraccion():
    ventana = VentanaFalsa()
    ventana._iniciar_trabajo()
    ventana.control_actual.duracion = 10
    ventana.control_actual.avance(2.5)
    assert ventana.estados == [("Procesando · 2.5/10.0 s", 0.25)]


def test_avance_del_contrato_llega_con_texto_y_fraccion(monkeypatch):
    from automontaje.modulos import contrato_edicion

    ventana = VentanaFalsa()

    def ejecutar(_entrada, _salida, _contrato, al_progresar, control):
        al_progresar(0.4, "Aplicando color")
        return {"exito": False, "cancelado": True}

    monkeypatch.setattr(contrato_edicion, "ejecutar_contrato_herramientas", ejecutar)
    ventana._hilo_contrato("entrada.mp4", {"herramientas": []})
    assert ("Aplicando color", 0.4) in ventana.estados

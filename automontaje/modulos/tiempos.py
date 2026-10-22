# -*- coding: utf-8 -*-
"""Mapa de tiempos: dónde acaba cada segundo del vídeo original tras los cortes.

Regla del editor: los tiempos de un contrato se refieren al vídeo ORIGINAL, el que la persona
tiene delante al pedir «pon un texto en el segundo 12». Cada herramienta que quita tiempo
(un corte, quitar silencios) informa de los tramos que conserva, y el mapa se recompone, de
modo que el segundo 12 del original sigue siendo el mismo momento aunque antes se haya quitado
un trozo.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tramos más cortos que esto no cuentan: son el redondeo de un corte, no contenido.
_MINIMO = 1e-6


@dataclass(frozen=True)
class MapaTiempos:
    """Tramos del original que siguen en el resultado: (inicio_original, fin_original, inicio_resultado)."""

    tramos: tuple

    @staticmethod
    def identidad(duracion: float) -> "MapaTiempos":
        return MapaTiempos(((0.0, float(duracion), 0.0),))

    @staticmethod
    def extracto(desde: float, hasta: float) -> "MapaTiempos":
        """El resultado es solo [desde, hasta] del original, empezando en 0 (una previsualización)."""
        return MapaTiempos(((float(desde), float(hasta), 0.0),))

    @property
    def duracion(self) -> float:
        """Duración del resultado."""
        return sum(fin - inicio for inicio, fin, _ in self.tramos)

    def llevar(self, t: float) -> tuple:
        """(segundo en el resultado, si ese momento se había quitado).

        Un momento quitado salta al primer momento que queda después; pasado el final, al final.
        """
        for inicio, fin, destino in self.tramos:
            if t < inicio:
                return destino, True
            if t <= fin:
                return destino + (t - inicio), False
        return self.duracion, True

    def llevar_tramo(self, inicio: float, fin: float):
        """[inicio, fin] del original en el resultado, o None si se quitó entero."""
        a, _ = self.llevar(inicio)
        b, _ = self.llevar(fin)
        return (a, b) if b - a > _MINIMO else None

    def tras_conservar(self, conservados: list) -> "MapaTiempos":
        """El mapa después de un paso que solo conserva `conservados`, en tiempos de SU entrada."""
        nuevos = []
        destino = 0.0
        for k_inicio, k_fin in conservados:
            for inicio, fin, actual in self.tramos:
                # Parte de este tramo (en tiempos de la entrada del paso) que cae dentro de lo conservado.
                a = max(k_inicio, actual)
                b = min(k_fin, actual + (fin - inicio))
                if b - a > _MINIMO:
                    nuevos.append((inicio + (a - actual), inicio + (b - actual), destino + (a - k_inicio)))
            destino += k_fin - k_inicio
        nuevos.sort()
        return MapaTiempos(tuple(nuevos))

"""Caso de uso: MIRAR LA PANTALLA (vía rápida).

Captura → modelo de visión directo → respuesta. SIN pasar por el agente.

Diferencia clave con `ResumirLeccion`:
  - `ResumirLeccion`  → resumen de una lección leída por la extensión (texto)
  - `MirarPantalla`   → mira la pantalla AHORA (imagen), respuesta en ~5 s

Medido: captura 2,6 s + visión 2,65 s ≈ 5,3 s la vuelta completa.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..dominio.puertos import CapturaPantalla, MotorVision


@dataclass
class Mirada:
    """Resultado de una mirada a la pantalla."""

    texto: str = ""
    ms_total: int = 0
    ms_captura: int = 0
    ms_vision: int = 0
    pantallas: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.texto)

    def resumen(self) -> str:
        if self.error:
            return f"error: {self.error}"
        return f"{self.ms_total} ms ({self.pantallas} pantallas)"


class MirarPantalla:
    """Orquesta captura + visión. Todo adaptadores: se puede testear."""

    PREGUNTA_DEFECTO = (
        "¿Qué hay en esta pantalla? Si hay una pregunta de práctica, di la "
        "alternativa correcta y el concepto para entenderla. Si hay código, "
        "señala el error y dame los pasos numerados para arreglarlo."
    )

    def __init__(
        self,
        captura: CapturaPantalla,
        vision: MotorVision,
        preguntas_frecuentes: bool = True,
    ) -> None:
        self.captura = captura
        self.vision = vision

    def ejecutar(self, pregunta: str | None = None) -> Mirada:
        t0 = time.perf_counter()

        capturado = self.captura.capturar()
        if not capturado.ok:
            return Mirada(error=capturado.error, ms_captura=capturado.ms)

        respuesta = self.vision.mirar(
            capturado.rutas,
            pregunta or self.PREGUNTA_DEFECTO,
        )
        if not respuesta.ok:
            return Mirada(
                error=respuesta.error,
                ms_captura=capturado.ms,
                ms_vision=respuesta.ms,
                pantallas=len(capturado.rutas),
            )

        return Mirada(
            texto=respuesta.texto,
            ms_total=int((time.perf_counter() - t0) * 1000),
            ms_captura=capturado.ms,
            ms_vision=respuesta.ms,
            pantallas=len(capturado.rutas),
        )

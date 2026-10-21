"""Caso de uso: resumir una lección.

Orquesta el flujo rápido:
    ética → caché → (si no hay) motor rápido en streaming → guardar

No sabe NADA de FastAPI, Ollama ni SQLite. Solo usa puertos.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator

from ..dominio.entidades import ExamenDetectado, Leccion, Resumen
from ..dominio.puertos import Cache, FiltroEtica, MotorPreguntas, MotorResumen


@dataclass
class Evento:
    """Evento para el dashboard (SSE)."""

    tipo: str  # status | token | resumen | preguntas | error
    datos: dict


class ResumirLeccion:
    def __init__(
        self,
        cache: Cache,
        motor_rapido: MotorResumen,
        motor_profundo: MotorPreguntas,
        filtro: FiltroEtica,
    ) -> None:
        self.cache = cache
        self.motor_rapido = motor_rapido
        self.motor_profundo = motor_profundo
        self.filtro = filtro

    async def ejecutar(self, leccion: Leccion) -> AsyncIterator[Evento]:
        """Genera eventos. `live=True` significa streaming al dashboard."""

        # 1. Ética primero. Siempre.
        if self.filtro.es_examen(leccion):
            yield Evento("error", {"msg": "Parece una evaluación: captura bloqueada por diseño."})
            return

        # 2. ¿Texto suficiente?
        if not leccion.es_util():
            yield Evento("error", {"msg": "Texto insuficiente para resumir."})
            return

        huella = self.cache.huella(leccion)
        resumen_guardado, preguntas_guardadas = self.cache.obtener(huella)

        # 3. Caché: si ya lo tenemos, es instantáneo (<0,1 s).
        if resumen_guardado:
            yield Evento("resumen", {
                "titulo": leccion.titulo,
                "texto": resumen_guardado,
                "desde_cache": True,
            })
        else:
            # 4. Streaming desde el motor rápido.
            yield Evento("status", {"msg": "resumiendo…", "reset": True, "titulo": leccion.titulo})
            resumen = Resumen()
            try:
                async for trozo in self.motor_rapido.resumir(leccion):
                    resumen.agregar(trozo)
                    yield Evento("token", {"texto": trozo})
            except Exception as exc:  # noqa: BLE001 — se reporta al dashboard
                yield Evento("error", {"msg": f"resumen: {exc}"})
                return

            if not resumen.listo:
                yield Evento("error", {"msg": "El modelo no devolvió texto."})
                return

            self.cache.guardar_resumen(huella, leccion, resumen.texto)

        # 5. Preguntas: si ya están, se emiten; si no, se lanzan en segundo plano.
        if preguntas_guardadas:
            yield Evento("preguntas", {"preguntas": [p.__dict__ for p in preguntas_guardadas]})
        else:
            asyncio.create_task(self._generar_en_segundo_plano(huella, leccion))

    async def _generar_en_segundo_plano(self, huella: str, leccion: Leccion) -> None:
        """El motor profundo piensa tranquilo. El usuario ya tiene su resumen."""
        try:
            preguntas = await self.motor_profundo.generar(leccion)
            if preguntas:
                self.cache.guardar_preguntas(huella, preguntas)
        except Exception:  # noqa: BLE001 — no debe tumbar el flujo rápido
            pass

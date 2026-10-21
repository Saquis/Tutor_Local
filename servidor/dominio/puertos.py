"""Puertos del dominio — Tutor Local.

Contratos (interfaces) que la infraestructura debe cumplir.
Son el borde del hexágono: el dominio define QUÉ necesita,
la infraestructura decide CÓMO lo hace.

Gracias a esto podemos cambiar sin tocar la lógica:
    MotorResumen:  Ollama local  ↔  DeepSeek API  ↔  cualquier otro
    FuenteTexto:   DOM del navegador  ↔  OCR de pantalla  ↔  PDF
    Cache:         SQLite  ↔  memoria  ↔  Redis
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Protocol

from .entidades import Leccion, Pregunta


class MotorResumen(ABC):
    """Modelo RÁPIDO. Su trabajo: primera frase en pantalla cuanto antes."""

    @abstractmethod
    async def resumir(self, leccion: Leccion) -> AsyncIterator[str]:
        """Emite trozos de texto a medida que el modelo los produce."""
        raise NotImplementedError
        yield ""  # pragma: no cover — hace que sea un generador asíncrono


class MotorPreguntas(ABC):
    """Modelo PROFUNDO. Su trabajo: pensar, no llegar rápido."""

    @abstractmethod
    async def generar(self, leccion: Leccion, cuantas: int = 5) -> list[Pregunta]:
        """Devuelve preguntas de práctica ya validadas."""
        raise NotImplementedError


class Cache(ABC):
    """Almacén por huella (url + contenido). Repetir cuesta cero."""

    @abstractmethod
    def huella(self, leccion: Leccion) -> str:
        ...

    @abstractmethod
    def obtener(self, huella: str) -> tuple[str | None, list[Pregunta] | None]:
        """(resumen, preguntas). Cualquiera puede ser None."""
        ...

    @abstractmethod
    def guardar_resumen(self, huella: str, leccion: Leccion, resumen: str) -> None:
        ...

    @abstractmethod
    def guardar_preguntas(self, huella: str, preguntas: list[Pregunta]) -> None:
        ...


class FiltroEtica(Protocol):
    """Blocklist de exámenes. Decisión de diseño, no un detalle técnico."""

    def es_examen(self, leccion: Leccion) -> bool:
        ...


class CapturaPantalla(Protocol):
    """Toma una foto del escritorio (todas las pantallas).

    Implementación real: PowerShell en Windows.
    Adaptador falso en tests: devuelve rutas inventadas.
    """

    def capturar(self):
        """Devuelve algo con `.rutas`, `.ms`, `.ok` y `.error`."""
        ...


class MotorVision(Protocol):
    """Mira 1..n imágenes y responde una pregunta sobre ellas.

    Es la VÍA RÁPIDA: llamada directa a la API, sin el agente en medio.
    Medido con deepseek-flash: ~2,65 s por imagen.
    """

    def mirar(self, rutas, pregunta: str):
        """Devuelve algo con `.texto`, `.ms`, `.ok` y `.error`."""
        ...


class Reloj(Protocol):
    """Inyectable para poder testear sin esperar de verdad."""

    def ahora(self) -> float:
        ...

"""Entidades del dominio — Tutor Local.

Reglas de negocio puras. NO importa nada de infraestructura,
ni FastAPI, ni requests, ni sqlite. Solo Python estándar.

Puertos y adaptadores: estas entidades son el centro del hexágono.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Leccion:
    """Material de estudio que el humano tiene abierto.

    `texto` es lo que se va a resumir. `seleccion` es lo que el humano
    marcó a propósito: si existe, manda sobre el contexto.
    """

    url: str
    titulo: str
    texto: str
    seleccion: str = ""
    capturada_en: datetime = field(default_factory=datetime.now)

    @property
    def contenido_efectivo(self) -> str:
        """Si hay selección, ella manda; la página solo da contexto."""
        if self.seleccion.strip():
            return f"[SELECCIÓN]\n{self.seleccion}\n\n[CONTEXTO]\n{self.texto[:4000]}"
        return self.texto

    def es_util(self, minimo: int = 200) -> bool:
        """Descarta capturas vacías o basura (menús, cookies)."""
        return len(self.contenido_efectivo.strip()) >= minimo

    @property
    def huella(self) -> str:
        """Clave de caché. Se calcula en el puerto Cache, no aquí."""
        raise NotImplementedError("La huella la calcula el adaptador de caché")


@dataclass(frozen=True)
class Pregunta:
    """Pregunta de práctica generada por el motor profundo."""

    enunciado: str
    opciones: tuple[str, ...]
    respuesta: int  # índice 0-based
    porque: str = ""

    def __post_init__(self) -> None:
        if not self.opciones:
            raise ValueError("Una pregunta necesita al menos una opción")
        if not 0 <= self.respuesta < len(self.opciones):
            raise ValueError(
                f"respuesta={self.respuesta} fuera de rango "
                f"(hay {len(self.opciones)} opciones)"
            )


@dataclass
class Resumen:
    """Resumen en streaming de una lección."""

    texto: str = ""
    desde_cache: bool = False

    def agregar(self, trozo: str) -> None:
        self.texto += trozo

    @property
    def listo(self) -> bool:
        return bool(self.texto.strip())


class ErrorDominio(Exception):
    """Error de negocio, no técnico."""


class ExamenDetectado(ErrorDominio):
    """La página parece una evaluación. Se bloquea por diseño."""

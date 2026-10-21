"""Filtro de ética: blocklist de exámenes.

Decisión de diseño (D-005), NO un detalle técnico.

El sistema se NIEGA a ayudar si la página parece una evaluación,
proctoring o examen oficial. Es específico a propósito para no
bloquear páginas de estudio legítimas ("Exam Prep" sigue permitido).

NO DESACTIVAR. Está aquí para que el proyecto sea honesto.
"""
from __future__ import annotations

import re

from ..dominio.entidades import Leccion

# Específico, no genérico: "exam" solo NO basta (bloquearía "exam prep").
PATRON_EXAMEN = re.compile(
    r"proctor"
    r"|take[-_ ]?exam"
    r"|exam[-_ ]?session"
    r"|official[-_ ]?exam"
    r"|pearsonvue"
    r"|certiport"
    r"|examity"
    r"|respondus"
    r"|lockdown[-_ ]?browser"
    r"|honorlock",
    re.IGNORECASE,
)

# Cuántos caracteres del cuerpo revisar (cubre también la ruta OCR).
VENTANA_TEXTO = 600


class FiltroExamenes:
    """Implementa el puerto FiltroEtica."""

    def es_examen(self, leccion: Leccion) -> bool:
        return bool(
            PATRON_EXAMEN.search(leccion.url)
            or PATRON_EXAMEN.search(leccion.titulo)
            or PATRON_EXAMEN.search(leccion.texto[:VENTANA_TEXTO])
        )

    @property
    def patron(self) -> str:
        return PATRON_EXAMEN.pattern

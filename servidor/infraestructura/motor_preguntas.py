"""Adaptador: motor PROFUNDO (preguntas de práctica).

Implementa MotorPreguntas. Corre en segundo plano: aquí SÍ nos
podemos tomar tiempo, porque el usuario ya tiene su resumen.

Dos backends intercambiables (ventaja de los puertos):
  - `OllamaPreguntas`  → local, gratis, privado (recomendado)
  - `DeepSeekPreguntas` → API remota, mejor calidad, cuesta tokens
"""
from __future__ import annotations

import json
import re

import httpx

from ..dominio.entidades import Leccion, Pregunta

PROMPT_SISTEMA = (
    "Eres un tutor técnico. Genera {cuantas} preguntas de práctica tipo examen "
    "sobre el material. Responde SOLO con JSON válido, sin markdown, con esta forma:\n"
    '[{{"enunciado":"...","opciones":["A","B","C","D"],"respuesta":0,"porque":"breve"}}]\n'
    "`respuesta` es el índice 0-based de la opción correcta."
)


def _extraer_preguntas(texto: str) -> list[Pregunta]:
    """El modelo a veces envuelve el JSON. Buscamos el array."""
    match = re.search(r"\[.*\]", texto or "", re.S)
    if not match:
        return []
    try:
        crudas = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []

    salida: list[Pregunta] = []
    for c in crudas:
        try:
            salida.append(
                Pregunta(
                    enunciado=c["enunciado"],
                    opciones=tuple(c["opciones"]),
                    respuesta=int(c["respuesta"]),
                    porque=c.get("porque", ""),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue  # una pregunta malformada no invalida las demás
    return salida


class OllamaPreguntas:
    """Motor profundo gratuito y local."""

    def __init__(
        self,
        modelo: str = "phi3:3.8b",
        base_url: str = "http://localhost:11434",
        timeout: float = 300.0,
    ) -> None:
        self.modelo = modelo
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def generar(self, leccion: Leccion, cuantas: int = 5) -> list[Pregunta]:
        payload = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": PROMPT_SISTEMA.format(cuantas=cuantas)},
                {
                    "role": "user",
                    "content": f"Título: {leccion.titulo}\n\n{leccion.texto[:14000]}",
                },
            ],
            "stream": False,
            "options": {"temperature": 0.4, "num_predict": 1200},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as cliente:
            r = await cliente.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            contenido = r.json().get("message", {}).get("content", "")
        return _extraer_preguntas(contenido)


class DeepSeekPreguntas:
    """Motor profundo por API. Mejor calidad, cuesta tokens."""

    def __init__(
        self,
        api_key: str,
        modelo: str = "deepseek-flash",
        base_url: str = "https://api.deepseek.com",
        timeout: float = 180.0,
    ) -> None:
        self.api_key = api_key
        self.modelo = modelo
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def generar(self, leccion: Leccion, cuantas: int = 5) -> list[Pregunta]:
        payload = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": PROMPT_SISTEMA.format(cuantas=cuantas)},
                {
                    "role": "user",
                    "content": f"Título: {leccion.titulo}\n\n{leccion.texto[:14000]}",
                },
            ],
            "temperature": 0.4,
            "max_tokens": 2000,
        }
        cabeceras = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as cliente:
            r = await cliente.post(
                f"{self.base_url}/chat/completions", json=payload, headers=cabeceras
            )
            r.raise_for_status()
            contenido = r.json()["choices"][0]["message"]["content"]
        return _extraer_preguntas(contenido)

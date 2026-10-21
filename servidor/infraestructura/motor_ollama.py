"""Adaptador: motor RÁPIDO con Ollama (modelo local).

Implementa MotorResumen. Es la ruta crítica de latencia:
medido 0.33 s al primer token con phi3:3.8b en la RTX 3050 Ti.

Habla con Ollama por HTTP. En este proyecto Ollama corre en WSL y
Windows lo alcanza transparente en http://localhost:11434.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from ..dominio.entidades import Leccion

PROMPT_SISTEMA = (
    "Eres un tutor técnico. Responde en español, de forma concisa. "
    "Resume el material en máximo 6 viñetas, define 3-5 términos clave "
    "y señala 1 confusión típica. Sin preámbulos."
)


class MotorOllama:
    """Implementa MotorResumen usando un modelo local vía Ollama."""

    def __init__(
        self,
        modelo: str = "phi3:3.8b",
        base_url: str = "http://localhost:11434",
        max_tokens: int = 400,
        temperatura: float = 0.3,
        timeout: float = 120.0,
        max_chars: int | None = None,
        num_ctx: int | None = None,
    ) -> None:
        import os as _os

        self.modelo = modelo
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperatura = temperatura
        self.timeout = timeout

        # ── Los dos parámetros que dominan la latencia ────────────────────
        #
        # num_ctx: ventana de contexto de Ollama (entrada + salida).
        #   Medido en esta máquina (RTX 3050 Ti, 4 GB):
        #     num_ctx 8192 -> el modelo ocupa 5.9 GB -> 66% CPU -> TTFT 11,10 s
        #     num_ctx 2048 -> el modelo ocupa 3.1 GB -> 29% CPU -> TTFT  2,91 s
        #   Si el modelo no cabe en la VRAM, Ollama tira parte a CPU y todo
        #   se vuelve ~4x más lento. Por eso 4096 es un buen equilibrio.
        #
        # max_chars: tamaño máximo de la lección que se manda.
        #   ⚠️ CRÍTICO: si la entrada no cabe en num_ctx, Ollama RECORTA el
        #   prompt EN SILENCIO y el resumen sale de media lección sin avisar.
        #   Regla: num_ctx >= tokens(entrada) + num_predict + margen
        #   En español, tokens ≈ caracteres / 2,8.
        self.num_ctx = num_ctx or int(_os.getenv("TUTOR_NUM_CTX", "4096"))
        self.max_chars = max_chars or int(
            _os.getenv("TUTOR_MAX_CHARS", str(self._entrada_segura()))
        )

    def _entrada_segura(self) -> int:
        """Caracteres que caben con seguridad en `num_ctx` sin truncar.

        Reserva: el system prompt, la salida y un margen del 15%.
        Es la defensa contra el truncamiento silencioso de Ollama.
        """
        reservado = self.max_tokens + 80
        disponible = max(0, self.num_ctx - reservado)
        return int(disponible * 2.8 * 0.85)  # 2,8 chars/token en español

    async def resumir(self, leccion: Leccion) -> AsyncIterator[str]:
        payload = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": PROMPT_SISTEMA},
                {
                    "role": "user",
                    "content": (
                        f"Título: {leccion.titulo}\n"
                        f"URL: {leccion.url}\n\n"
                        f"{leccion.contenido_efectivo[:self.max_chars]}"
                    ),
                },
            ],
            "stream": True,
            "options": {
                "num_predict": self.max_tokens,
                "num_ctx": self.num_ctx,
                "temperature": self.temperatura,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as cliente:
            async with cliente.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as respuesta:
                respuesta.raise_for_status()
                async for linea in respuesta.aiter_lines():
                    if not linea.strip():
                        continue
                    try:
                        dato = json.loads(linea)
                    except json.JSONDecodeError:
                        continue
                    trozo = dato.get("message", {}).get("content")
                    if trozo:
                        yield trozo
                    if dato.get("done"):
                        break

    async def disponible(self) -> bool:
        """Comprueba que Ollama responde y tiene el modelo cargado."""
        try:
            async with httpx.AsyncClient(timeout=10) as cliente:
                r = await cliente.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                nombres = {m["name"] for m in r.json().get("models", [])}
                return any(n.startswith(self.modelo.split(":")[0]) for n in nombres)
        except Exception:  # noqa: BLE001
            return False
"""Raíz de composición — aquí se cablea todo.

Este es el único archivo que conoce a la vez el dominio y la
infraestructura. Es lo que permite que el resto sea testeable.

Ejecutar:
    python -m servidor.main

Variables de entorno (todas opcionales, hay defaults):
    TUTOR_TOKEN        token compartido con la extensión
    TUTOR_HOST         0.0.0.0 para aceptar conexiones de Windows
    TUTOR_PUERTO       8765
    TUTOR_MODELO       phi3:3.8b
    TUTOR_OLLAMA       http://localhost:11434
    TUTOR_DB           ruta de study.db
    DEEPSEEK_API_KEY   si se quiere el motor profundo por API
"""
from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from .aplicacion.filtro_examenes import FiltroExamenes
from .aplicacion.mirar_pantalla import MirarPantalla
from .aplicacion.resumir_leccion import ResumirLeccion
from .entrada.api import crear_api
from .infraestructura.cache_sqlite import CacheSqlite
from .infraestructura.captura_windows import CapturaWindows
from .infraestructura.motor_ollama import MotorOllama
from .infraestructura.motor_preguntas import DeepSeekPreguntas, OllamaPreguntas
from .infraestructura.motor_vision import MotorVisionDeepSeek

AQUI = Path(__file__).parent


def construir():
    """Cablea adaptadores → puertos → casos de uso."""
    token = os.getenv("TUTOR_TOKEN", "cambia-este-token")
    modelo = os.getenv("TUTOR_MODELO", "phi3:3.8b")
    ollama = os.getenv("TUTOR_OLLAMA", "http://localhost:11434")
    db = os.getenv("TUTOR_DB", str(AQUI / "study.db"))

    cache = CacheSqlite(db)
    filtro = FiltroExamenes()

    # Motor RÁPIDO: local siempre (es la ruta crítica de latencia).
    motor_rapido = MotorOllama(modelo=modelo, base_url=ollama)

    # Motor PROFUNDO: local por defecto; API si hay clave.
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if api_key:
        motor_profundo = DeepSeekPreguntas(api_key=api_key)
        profundo_desc = "deepseek-flash (API)"
    else:
        motor_profundo = OllamaPreguntas(modelo=modelo, base_url=ollama)
        profundo_desc = f"{modelo} (local)"

    caso_uso = ResumirLeccion(
        cache=cache,
        motor_rapido=motor_rapido,
        motor_profundo=motor_profundo,
        filtro=filtro,
    )

    capacidades = {
        "motor_rapido": f"{modelo} (local)",
        "motor_profundo": profundo_desc,
        "cache": str(cache.ruta),
        "blocklist_examenes": True,
    }

    # ── VÍA RÁPIDA: mirar la pantalla sin el agente (captura + visión) ──
    vision = MotorVisionDeepSeek()
    captura = CapturaWindows(
        script=AQUI.parent / "ocr" / "captura.ps1",
        destino_script=AQUI.parent / "ocr" / "capturas",
        destino_local=Path(os.getenv("TUTOR_CAPTURAS", str(AQUI / "capturas"))),
    )
    mirar = MirarPantalla(captura=captura, vision=vision)
    capacidades["via_rapida"] = (
        f"captura + {vision.modelo} directo" if vision.configurado
        else "inactiva (falta DEEPSEEK_API_KEY)"
    )

    return caso_uso, token, capacidades, mirar


def main() -> None:
    caso_uso, token, capacidades, mirar = construir()
    app = crear_api(caso_uso, token, capacidades, mirar=mirar)

    host = os.getenv("TUTOR_HOST", "127.0.0.1")
    puerto = int(os.getenv("TUTOR_PUERTO", "8765"))

    print("=" * 58)
    print("  TUTOR LOCAL — copiloto de lectura")
    print("=" * 58)
    for k, v in capacidades.items():
        print(f"  {k:20} {v}")
    print(f"  {'escuchando':20} http://{host}:{puerto}")
    print("=" * 58)
    uvicorn.run(app, host=host, port=puerto, log_level="warning")


if __name__ == "__main__":
    main()

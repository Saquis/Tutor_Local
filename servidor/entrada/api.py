"""Adaptador de entrada: API HTTP + dashboard SSE.

Este es el borde exterior del hexágono. NO contiene reglas de negocio:
solo traduce HTTP ↔ casos de uso.

Endpoints:
    POST /ingest   ← la extensión manda el texto de la lección
    GET  /events   ← dashboard escucha en streaming (SSE)
    GET  /         ← dashboard
    GET  /salud    ← estado del sistema
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from ..aplicacion.resumir_leccion import ResumirLeccion
from ..dominio.entidades import Leccion

AQUI = Path(__file__).parent


def crear_api(caso_uso: ResumirLeccion, token: str, capacidades: dict, mirar=None) -> FastAPI:
    app = FastAPI(title="Tutor Local", docs_url=None, redoc_url=None)

    suscriptores: set[asyncio.Queue] = set()
    estado = {"ultima": None, "eventos": 0, "desde": time.time()}
    # Candado: evita que dos miradas se pisen (el panel puede pedir antes
    # de que termine la anterior). Sin esto, algunas devuelven 0 ms.
    _candado = asyncio.Lock()

    def emitir(evento: dict) -> None:
        """Difunde a todos los dashboards conectados."""
        for cola in list(suscriptores):
            try:
                cola.put_nowait(json.dumps(evento, ensure_ascii=False))
            except asyncio.QueueFull:
                pass
        estado["eventos"] += 1

    @app.post("/ingest")
    async def ingest(peticion: Request):
        # Sin token no entra nadie. Y NO se habilita CORS a propósito:
        # las páginas web no pueden leer /events ni enviar /ingest.
        if peticion.headers.get("x-token") != token:
            return JSONResponse({"ok": False, "motivo": "token"}, status_code=401)

        datos = await peticion.json()
        leccion = Leccion(
            url=datos.get("url", ""),
            titulo=datos.get("titulo") or datos.get("title") or "",
            texto=(datos.get("texto") or datos.get("text") or "").strip(),
            seleccion=(datos.get("seleccion") or datos.get("selection") or "").strip(),
        )
        en_vivo = bool(datos.get("live"))
        estado["ultima"] = {"url": leccion.url, "titulo": leccion.titulo, "vivo": en_vivo}

        if en_vivo:
            inicio = time.perf_counter()
            async for ev in caso_uso.ejecutar(leccion):
                emitir({"type": ev.tipo, **ev.datos})
            ms = round((time.perf_counter() - inicio) * 1000)
            print(f"  -> resumen servido en {ms} ms")
            return {"ok": True, "ms": ms}

        # Precómputo en segundo plano (no bloquea)
        asyncio.create_task(_consumir(caso_uso.ejecutar(leccion), emitir))
        return {"ok": True}

    @app.get("/events")
    async def events():
        cola: asyncio.Queue = asyncio.Queue(maxsize=500)
        suscriptores.add(cola)

        async def generar():
            try:
                yield 'data: {"type":"hola"}\n\n'
                while True:
                    yield f"data: {await cola.get()}\n\n"
            finally:
                suscriptores.discard(cola)

        return StreamingResponse(
            generar(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/salud")
    async def salud():
        return {
            "ok": True,
            "capacidades": capacidades,
            "ultima_leccion": estado["ultima"],
            "eventos_emitidos": estado["eventos"],
            "activo_desde_s": round(time.time() - estado["desde"], 1),
            "dashboards_conectados": len(suscriptores),
        }

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        html = (AQUI / "dashboard.html").read_text(encoding="utf-8")
        return html.replace("__TOKEN__", token)

    # ── VÍA RÁPIDA: mirar la pantalla sin pasar por el agente ──────────
    # Captura + modelo de visión directo. Medido: ~5,2 s la vuelta completa
    # (2,4 s captura + 2,8 s visión). El agente tardaría ~30 s.

    # Interruptor de pausa: si está activo, /vista NO llama a la API.
    # Sirve para cortar el consumo aunque el panel siga abierto.
    pausa = {"activo": False}

    @app.get("/vista/pausa")
    async def vista_pausa(on: str = "1"):
        pausa["activo"] = on not in ("0", "false", "no")
        return {"ok": True, "pausado": pausa["activo"]}

    @app.get("/vista/estado")
    async def vista_estado():
        return {"pausado": pausa["activo"]}

    @app.get("/vista")
    async def vista(pregunta: str | None = None):
        if pausa["activo"]:
            return {
                "ok": False,
                "pausado": True,
                "texto": "",
                "error": "vista en pausa (no se consultó al modelo)",
                "ms_total": 0, "ms_captura": 0, "ms_vision": 0, "pantallas": 0,
            }
        if mirar is None:
            return JSONResponse({"ok": False, "error": "vista no configurada"}, status_code=503)
        # Se ejecuta en un hilo: subprocess + HTTP bloquean.
        async with _candado:
            resultado = await asyncio.to_thread(mirar.ejecutar, pregunta)
        return {
            "ok": resultado.ok,
            "texto": resultado.texto,
            "error": resultado.error,
            "ms_total": resultado.ms_total,
            "ms_captura": resultado.ms_captura,
            "ms_vision": resultado.ms_vision,
            "pantallas": resultado.pantallas,
        }

    @app.get("/vista/panel", response_class=HTMLResponse)
    async def vista_panel():
        return (AQUI / "vista.html").read_text(encoding="utf-8")

    return app


async def _consumir(generador, emitir) -> None:
    async for ev in generador:
        emitir({"type": ev.tipo, **ev.datos})

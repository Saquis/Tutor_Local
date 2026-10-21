"""Prueba de extremo a extremo — Tutor Local.

Simula lo que hace la extensión:
  1. Se conecta al dashboard (/events)
  2. Manda una lección (/ingest)
  3. Mide el tiempo al PRIMER token y al resumen completo

Ejecutar (desde Tutor_Local):
    python pruebas\\prueba_extremo_a_extremo.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

import httpx

# Windows usa cp1252 por defecto en la consola: forzamos UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE = os.getenv("TUTOR_URL", "http://127.0.0.1:8765")
TOKEN = os.getenv("TUTOR_TOKEN", "-eIDzFPmtkHZYUzdd1jEzlfRDPF7ntwO")

LECCION = {
    "url": "https://ejemplo.local/leccion/indices-sql",
    "titulo": "Indices en bases de datos",
    "texto": (
        "Un indice es una estructura de datos auxiliar que acelera la busqueda de filas "
        "en una tabla. Sin indice, el motor debe recorrer la tabla completa fila por fila "
        "(full table scan). Con indice, el motor salta directamente a las filas relevantes, "
        "igual que el indice alfabetico de un libro evita leer todas las paginas. "
        "La mayoria de los motores usan arboles B o B+ porque mantienen los datos ordenados "
        "y permiten busquedas, inserciones y borrados en tiempo logaritmico. "
        "El costo de un indice es doble: ocupa espacio en disco y ralentiza las escrituras, "
        "porque cada INSERT, UPDATE o DELETE debe actualizar tambien el indice. "
        "Por eso se crean indices solo en columnas que se consultan con frecuencia, "
        "especialmente las que aparecen en WHERE, JOIN y ORDER BY. "
        "Un indice compuesto cubre varias columnas y solo sirve si la consulta usa "
        "un prefijo de esas columnas. Un indice que no se usa no solo no ayuda: "
        "tambien perjudica, porque se mantiene en cada escritura sin aportar nada."
    ),
    "seleccion": "",
    "live": True,
}


async def main() -> int:
    eventos: list[dict] = []
    t0 = time.perf_counter()
    primer_token: float | None = None

    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as cliente:
        # --- 1. comprobar que el servidor está vivo ---
        try:
            salud = (await cliente.get(f"{BASE}/salud")).json()
        except Exception as e:
            print(f"❌ El servidor no responde en {BASE}: {e}")
            print("   Arrancalo con:  servidor\\iniciar.bat")
            return 1

        print("=" * 60)
        print("  SERVIDOR OK")
        for k, v in salud.get("capacidades", {}).items():
            print(f"    {k:20} {v}")
        print("=" * 60)

        # --- 2. escuchar el dashboard en segundo plano ---
        async def escuchar():
            nonlocal primer_token
            try:
                async with cliente.stream("GET", f"{BASE}/events") as r:
                    async for linea in r.aiter_lines():
                        if not linea.startswith("data:"):
                            continue
                        try:
                            ev = json.loads(linea[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        eventos.append(ev)
                        if ev.get("type") == "token" and primer_token is None:
                            primer_token = time.perf_counter() - t0
                        if ev.get("type") in ("error", "preguntas"):
                            return
            except Exception:
                return

        tarea = asyncio.create_task(escuchar())
        await asyncio.sleep(0.4)  # dar tiempo a suscribirse

        # --- 3. mandar la lección ---
        print("\n-> Enviando leccion...")
        r = await cliente.post(f"{BASE}/ingest", json=LECCION,
                               headers={"x-token": TOKEN})
        if r.status_code != 200:
            print(f"❌ /ingest devolvió HTTP {r.status_code}: {r.text[:200]}")
            return 1
        datos = r.json()
        print(f"  respuesta: {datos}")

        # --- 4. esperar a que termine el flujo ---
        try:
            await asyncio.wait_for(tarea, timeout=90)
        except asyncio.TimeoutError:
            tarea.cancel()

        total = time.perf_counter() - t0

    # --- 5. informe ---
    resumen = "".join(e["texto"] for e in eventos if e.get("type") == "token")
    if not resumen:
        for e in eventos:
            if e.get("type") == "resumen":
                resumen = e.get("texto", "")

    errores = [e.get("msg") for e in eventos if e.get("type") == "error"]
    preguntas = next((e for e in eventos if e.get("type") == "preguntas"), None)

    print("\n" + "=" * 60)
    print("  RESULTADO")
    print("=" * 60)
    if primer_token is not None:
        marca = "✅" if primer_token < 1.5 else "⚠️"
        print(f"  {marca} primer token:   {primer_token:.2f} s   (objetivo < 1,5 s)")
    print(f"  ⏱️  resumen completo: {total:.2f} s")
    print(f"  📄 tokens recibidos:  {len([e for e in eventos if e.get('type')=='token'])}")

    if errores:
        print("\n  ❌ ERRORES:")
        for e in errores:
            print(f"     · {e}")

    if resumen:
        print("\n  --- RESUMEN GENERADO ---")
        for linea in resumen.strip().splitlines():
            print(f"  {linea}")
    else:
        print("\n  ⚠️  No llegó resumen (¿Ollama está corriendo y tiene el modelo?)")

    if preguntas:
        lista = preguntas.get("preguntas", [])
        print(f"\n  --- {len(lista)} PREGUNTAS (en caché) ---")
        for i, p in enumerate(lista[:3], 1):
            print(f"  {i}. {p.get('enunciado','')[:80]}")
    else:
        print("\n  ℹ️  Las preguntas se generan en segundo plano (revisa el dashboard).")

    return 0 if resumen else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

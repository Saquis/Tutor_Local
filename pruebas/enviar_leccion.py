"""Envia una leccion al servidor y mide. Minimal y robusto para Windows."""
import json
import sys
import time

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os

BASE = os.environ.get("TUTOR_BASE", "http://127.0.0.1:8765")
TOKEN = os.environ["TUTOR_TOKEN"]  # export TUTOR_TOKEN=... antes de correr

with open("pruebas/leccion_ejemplo.json", encoding="utf-8") as f:
    datos = json.load(f)

print("Enviando leccion (%d caracteres)..." % len(datos["texto"]))
t0 = time.perf_counter()
try:
    r = httpx.post(BASE + "/ingest", json=datos,
                   headers={"x-token": TOKEN}, timeout=300)
    total = time.perf_counter() - t0
    print("HTTP", r.status_code)
    print("respuesta:", r.json())
    print("TIEMPO TOTAL: %.2f s" % total)
except Exception as e:
    print("ERROR:", type(e).__name__, e)
    sys.exit(1)

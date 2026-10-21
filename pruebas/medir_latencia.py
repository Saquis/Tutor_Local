"""Mide latencia: cache-miss (genera) vs cache-hit (instantaneo)."""
import json
import sys
import time

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8765"
TOKEN = os.environ["TUTOR_TOKEN"]  # export TUTOR_TOKEN=... antes de correr


def enviar(leccion, etiqueta):
    t0 = time.perf_counter()
    try:
        r = httpx.post(BASE + "/ingest", json=leccion,
                       headers={"x-token": TOKEN}, timeout=300)
        dt = time.perf_counter() - t0
        d = r.json()
        ms = d.get("ms", "?")
        print("  %-28s HTTP %s  ->  %.2f s  (servidor: %s ms)" %
              (etiqueta, r.status_code, dt, ms))
        return dt
    except Exception as e:
        print("  %-28s ERROR: %s" % (etiqueta, e))
        return None


with open("pruebas/leccion_ejemplo.json", encoding="utf-8") as f:
    base = json.load(f)

print("=" * 62)
print("  MEDICION DE LATENCIA")
print("=" * 62)

# 1. Cache HIT (misma leccion de antes)
print("\n[1] Misma leccion (deberia venir de CACHE):")
enviar(base, "cache hit")

# 2. Cache MISS (texto distinto -> obliga a generar)
nueva = dict(base)
nueva["texto"] = base["texto"] + " Ademas, los indices parciales aplican " \
    "una condicion WHERE y son utiles en tablas grandes con consultas selectivas."
nueva["url"] = base["url"] + "-v2"
print("\n[2] Leccion nueva (deberia GENERAR con phi3):")
enviar(nueva, "cache miss")

# 3. La nueva otra vez -> cache hit
print("\n[3] La nueva repetida (deberia ser CACHE):")
enviar(nueva, "cache hit (repetida)")

print("\n" + "=" * 62)

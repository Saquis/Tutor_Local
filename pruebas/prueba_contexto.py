"""Prueba decisiva: ?cabe el modelo en la GPU con menos contexto?

El hallazgo: phi3 con num_ctx=8192 ocupa 5.9 GB y la GPU tiene 4 GB
-> Ollama tira 66% a CPU -> todo es 100x mas lento.

Hipotesis: bajando num_ctx, la KV cache encoge, cabe en la GPU y
el primer token pasa de segundos a decimas.
"""
import json
import time
import urllib.request

URL = "http://localhost:11434/api/chat"
TEXTO = ("Un indice acelera las busquedas en una tabla. " * 40)  # ~1.880 chars


def medir(num_ctx):
    body = {
        "model": "phi3:3.8b",
        "stream": True,
        "keep_alive": "10m",
        "options": {"num_predict": 80, "num_ctx": num_ctx},
        "messages": [
            {"role": "system", "content": "Resume en 3 lineas."},
            {"role": "user", "content": TEXTO},
        ],
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    primero = None
    trozos = 0
    with urllib.request.urlopen(req, timeout=300) as r:
        for raw in r:
            if not raw.strip():
                continue
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if d.get("message", {}).get("content"):
                if primero is None:
                    primero = time.perf_counter() - t0
                trozos += 1
            if d.get("done"):
                break
    total = time.perf_counter() - t0
    print("  num_ctx=%-6d  TTFT %6.2fs  total %6.2fs  %d trozos"
          % (num_ctx, primero if primero else -1, total, trozos), flush=True)


print("=" * 74)
print("  ?CABE EN LA GPU?  phi3:3.8b  ·  entrada ~1.880 chars")
print("=" * 74, flush=True)

for ctx in (2048, 4096, 8192):
    try:
        medir(ctx)
    except Exception as e:
        print("  num_ctx=%d  ERROR: %s" % (ctx, e), flush=True)
    time.sleep(1)

print("\n  (revisa 'ollama ps' para ver el reparto CPU/GPU)", flush=True)

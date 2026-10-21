"""Experimento decisivo: latencia vs tamano de entrada (TTFT).

Mide el TIEMPO AL PRIMER TOKEN con phi3:3.8b local para distintos
tamanos de entrada. El objetivo es separar "problema del modelo" de
"problema del tamano de la entrada".

Se ejecuta en WSL (habla directo con Ollama en localhost:11434).
Escribe los resultados en pruebas/curva_latencia.txt

Uso:  python3 pruebas/curva_latencia.py
"""
import json
import time
import urllib.request

URL = "http://localhost:11434/api/chat"
MODELO = "phi3:3.8b"
TAMANOS = [500, 2000, 6000, 18000]
MAX_TOKENS = 150

SYSTEM = "Resume la leccion en espanol en 5 lineas claras."

TEXTO_BASE = (
    "Un indice es una estructura auxiliar que acelera la busqueda de filas en una tabla. "
    "Sin indice, el motor recorre la tabla completa fila por fila. Con indice, salta "
    "directamente a las filas relevantes, igual que el indice alfabetico de un libro evita "
    "leer todas las paginas. La mayoria de los motores usan arboles B o B+ porque mantienen "
    "los datos ordenados y permiten busquedas en tiempo logaritmico. El costo es doble: ocupa "
    "espacio en disco y ralentiza las escrituras, porque cada INSERT o UPDATE debe actualizar "
    "tambien el indice. Por eso se crean indices solo en columnas que se consultan con "
    "frecuencia, especialmente las que aparecen en WHERE, JOIN y ORDER BY. Un indice compuesto "
    "cubre varias columnas y solo sirve si la consulta usa un prefijo de esas columnas. "
)


def texto_de(n: int) -> str:
    base = TEXTO_BASE
    while len(base) < n:
        base += TEXTO_BASE
    return base[:n]


def medir(texto: str, etiqueta: str):
    body = {
        "model": MODELO,
        "stream": True,
        "keep_alive": "10m",
        "options": {"num_predict": MAX_TOKENS, "num_ctx": 8192},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": texto},
        ],
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    primer = None
    trozos = 0
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            if not raw.strip():
                continue
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if d.get("message", {}).get("content"):
                if primer is None:
                    primer = time.perf_counter() - t0
                trozos += 1
            if d.get("done"):
                break
    total = time.perf_counter() - t0
    linea = "%-22s %6d chars  TTFT %7.2fs  total %7.2fs  %3d trozos  %.1f tok/s" % (
        etiqueta, len(texto), primer or -1, total, trozos, trozos / total if total else 0)
    print(linea, flush=True)
    return len(texto), (primer or -1), total


print("=" * 92)
print("  CURVA DE LATENCIA — phi3:3.8b local · TTFT vs tamano de entrada")
print("=" * 92, flush=True)

print("\n[calentamiento] cargando modelo con prompt corto...", flush=True)
medir("Hola, di una frase.", "calentamiento")

resultados = []
for n in TAMANOS:
    for rep in (1, 2):
        r = medir(texto_de(n), "rep%d" % rep)
        if rep == 2:
            resultados.append(r)

with open("pruebas/curva_latencia.txt", "w", encoding="utf-8") as f:
    f.write("chars;ttft_s;total_s\n")
    for chars, ttft, total in resultados:
        f.write("%d;%.2f;%.2f\n" % (chars, ttft, total))

print("\n" + "=" * 92)
print("  RESUMEN")
print("=" * 92)
for chars, ttft, total in resultados:
    estado = "OK" if ttft < 1.5 else ("ACEPTABLE" if ttft < 8 else "LENTO")
    print("  %6d chars -> TTFT %7.2fs  %s" % (chars, ttft, estado))
print("\nGuardado en pruebas/curva_latencia.txt", flush=True)

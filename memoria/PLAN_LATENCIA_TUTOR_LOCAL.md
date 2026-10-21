# Plan: arreglar la latencia de Tutor_Local (DeepSeek en la ruta rápida)

**Fecha:** 02-oct-2026
**Origen:** revisión de `SESION_02OCT2026.md` (MVP funcional, primer token en 69,6 s vs objetivo < 1,5 s).
**Para el agente que lo lea:** este documento es una propuesta, no una orden. Evalúala, cuestiona lo que no se sostenga y dime cómo la afrontarías. Las partes marcadas con ⚠️ son hipótesis sin medir.

---

## 1. Diagnóstico (coincide con el informe)

El modelo no es lento: la **entrada** es enorme.

- `motor_ollama.py` manda hasta 18.000 caracteres (~4.500-6.000 tokens).
- Ollama hace todo el prefill antes del primer token; `stream=True` no ayuda con eso.
- `phi3:3.8b` Q4 (~2,2 GB) en una GPU de 4 GB: con 6k tokens de contexto la KV cache puede desbordar y parte del cómputo cae a CPU.
- La medición de ayer (0,33-0,62 s) fue con un prompt corto.
- La caché SQLite y el streaming funcionan bien (0,43 s en lección ya vista).

## 2. Propuesta: invertir la cascada

| Ruta | Hoy | Propuesta |
|---|---|---|
| Rápida (resumen, primer token) | phi3 local | **DeepSeek Flash remoto** (streaming) |
| Profunda (preguntas, async) | phi3 local (mismo modelo) | DeepSeek Pro o Flash, vía OpenClaw o directo |
| Respaldo sin internet | no existe | phi3 local con entrada recortada |

⚠️ Hipótesis: un modelo remoto procesa el prefill de 5k tokens en menos de ~1,5 s. Hay que medirlo (sección 4).

### Costos
Con ~0.15 USD por millón de tokens de entrada (cache miss), una lección de 5k tokens cuesta menos de una milésima de dólar. La caché SQLite evita repetir llamadas.

### Prompt cache
- System prompt fijo **al principio**, contenido de la lección **al final**.
- Así la parte repetida cae en cache hit (mucho más barata y rápida).

### Privacidad (decisión del dueño del proyecto)
El texto de las lecciones saldría a los servidores de DeepSeek. Decidir si es aceptable o si el modo "solo local" debe seguir disponible como opción.

## 3. Verificaciones previas (antes de tocar código)

1. **ID del modelo vigente.** OpenClaw usa `deepseek-chat` (131k de contexto). Fuentes recientes hablan de `deepseek-flash` (V4.1, con visión nativa). Confirmar en `api-docs.deepseek.com` qué IDs siguen activos, su contexto y su precio. La configuración actual puede estar desfasada.
2. **Camino crítico sin el gateway.** ⚠️ Hipótesis: llamar a la API de DeepSeek directamente (compatible con OpenAI) desde el servidor es más rápido que pasar por el gateway de OpenClaw. Medir ambas rutas. Dejar OpenClaw para tareas profundas y asíncronas.
3. **Entorno.** El servidor corre nativo en Windows y OpenClaw vive en WSL2. Decidir y documentar dónde corre cada cosa (desde WSL, Windows se alcanza por el gateway `172.30.16.1`, no por `127.0.0.1`).

## 4. Experimento decisivo: latencia vs tamaño de prompt

Una sola corrida separa "problema del modelo" de "problema de la entrada".

**Matriz:** 4 tamaños de entrada (500 / 2.000 / 6.000 / 18.000 caracteres) × 2-3 motores (phi3 local, `deepseek-flash` directo y, si aplica, vía OpenClaw).
**Métrica principal:** tiempo al primer token. Secundaria: tiempo total.
**Repeticiones:** 3 por celda; descartar la primera (modelo frío).

### Script: `pruebas/latencia_comparada.py`

```python
"""Mide tiempo al primer token (TTFT) y tiempo total: phi3 local vs DeepSeek.

Uso (Windows):
    set DEEPSEEK_API_KEY=sk-...
    set DEEPSEEK_MODEL=deepseek-flash      (verificar el ID vigente)
    python pruebas/latencia_comparada.py

Ajusta TEXTO_BASE si quieres usar una lección real en vez de la de ejemplo.
"""
import json
import os
import statistics
import time

import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "phi3:3.8b"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

TAMANOS = [500, 2000, 6000, 18000]   # caracteres de entrada
REPETICIONES = 3                      # la primera se descarta (modelo frío)
MAX_TOKENS = 150

SYSTEM = "Resume la lección en español en 5 líneas claras."

# Texto base: usa la lección de ejemplo si existe, si no un relleno.
try:
    with open("pruebas/leccion_ejemplo.json", encoding="utf-8") as f:
        TEXTO_BASE = f.read()
except FileNotFoundError:
    TEXTO_BASE = ("La computación en la nube ofrece recursos bajo demanda. "
                  "Los servicios se dividen en IaaS, PaaS y SaaS. ") * 50


def texto_de(n: int) -> str:
    base = TEXTO_BASE
    while len(base) < n:
        base += TEXTO_BASE
    return base[:n]


def ttft_ollama(texto: str):
    t0 = time.perf_counter()
    primero = None
    with requests.post(OLLAMA_URL, stream=True, timeout=300, json={
        "model": OLLAMA_MODEL,
        "stream": True,
        "keep_alive": "10m",
        "options": {"num_predict": MAX_TOKENS, "num_ctx": 8192},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": texto}],
    }) as r:
        r.raise_for_status()
        for linea in r.iter_lines():
            if not linea:
                continue
            d = json.loads(linea)
            if primero is None and d.get("message", {}).get("content"):
                primero = time.perf_counter() - t0
            if d.get("done"):
                break
    return primero, time.perf_counter() - t0


def ttft_deepseek(texto: str):
    t0 = time.perf_counter()
    primero = None
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}",
               "Content-Type": "application/json"}
    with requests.post(DEEPSEEK_URL, headers=headers, stream=True, timeout=120, json={
        "model": DEEPSEEK_MODEL,
        "stream": True,
        "max_tokens": MAX_TOKENS,
        "temperature": 0.2,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": texto}],
    }) as r:
        r.raise_for_status()
        for linea in r.iter_lines():
            if not linea or not linea.startswith(b"data: "):
                continue
            carga = linea[6:]
            if carga == b"[DONE]":
                break
            delta = json.loads(carga)["choices"][0]["delta"].get("content")
            if primero is None and delta:
                primero = time.perf_counter() - t0
    return primero, time.perf_counter() - t0


MOTORES = {"phi3_local": ttft_ollama}
if DEEPSEEK_KEY:
    MOTORES["deepseek"] = ttft_deepseek
else:
    print("AVISO: sin DEEPSEEK_API_KEY, solo se mide phi3 local.")


def main():
    filas = []
    for nombre, fn in MOTORES.items():
        for n in TAMANOS:
            texto = texto_de(n)
            ttfts, totales = [], []
            for i in range(REPETICIONES + 1):
                try:
                    p, t = fn(texto)
                except Exception as e:  # registrar y seguir
                    print(f"{nombre} {n} intento {i}: ERROR {e}")
                    continue
                if i == 0:
                    continue  # descartar corrida fría
                if p is not None:
                    ttfts.append(p)
                totales.append(t)
            if ttfts:
                filas.append((nombre, n, statistics.median(ttfts),
                              statistics.median(totales)))
                print(f"{nombre:11} {n:>6} chars  TTFT {filas[-1][2]:6.2f}s  "
                      f"total {filas[-1][3]:6.2f}s")

    with open("pruebas/latencia_comparada.txt", "w", encoding="utf-8") as f:
        f.write("motor;chars;ttft_s;total_s\n")
        for nombre, n, p, t in filas:
            f.write(f"{nombre};{n};{p:.2f};{t:.2f}\n")
    print("Guardado en pruebas/latencia_comparada.txt")


if __name__ == "__main__":
    main()
```

### Después de la corrida
- Revisar también `ollama ps` durante la prueba local: confirma si es `100% GPU` o hay parte en CPU.
- Repetir con **solo la selección** en vez de la página completa.
- Probar `num_ctx` más bajo y `num_predict` menor en local.
- Probar un modelo local más chico para el respaldo (`llama3.2:1b`, `qwen2.5:1.5b`).

## 5. Criterios de éxito

- Primer token **< 1,5 s** en lección nueva (ruta rápida).
- Caché: se mantiene en < 1 s.
- Ruta profunda (preguntas) no bloquea ni compite con la rápida.
- Existe un modo de respaldo local documentado.

## 6. Orden de trabajo sugerido

1. Arreglar logs de `iniciar.bat` (sin esto se prueba a ciegas).
2. `git init` + primer commit.
3. Verificar IDs y precios de DeepSeek (sección 3).
4. Correr `latencia_comparada.py` y guardar resultados.
5. Con los números: fijar la cascada (rápido / profundo / respaldo).
6. Cambiar el token por defecto `cambia-este-token` antes de exponer nada fuera de `127.0.0.1`.
7. `ocr_fallback.py` en Windows.
8. Probar `innerText` en una lección real (el hito que decide si el proyecto vive).

## 7. Control de gasto (importante)

Una revisión de código con un modelo de OpenAI en OpenClaw ya consumió unos 5 USD en una sola pasada. Antes de ejecutar nada con APIs de pago:

- Poner un **tope de gasto** en el panel del proveedor.
- Limitar `max_tokens` y el contexto por llamada.
- Para revisiones de repositorios grandes, trabajar por carpetas o archivos, no el repo entero de golpe.
- Preferir DeepSeek para tareas de volumen y reservar modelos caros para decisiones puntuales.
- Registrar tokens y costo por llamada en el log del servidor.

## 8. Preguntas abiertas para el agente

1. ¿La hipótesis de la ruta rápida remota se sostiene con los números, o hay otro cuello de botella?
2. ¿Qué tan grande es la sobrecarga del gateway de OpenClaw frente a la llamada directa?
3. ¿Conviene recortar la entrada (selección, primeras N líneas, resumen por secciones) en vez de mandar la página completa?
4. ¿Qué parte del plan cambiarías y por qué?

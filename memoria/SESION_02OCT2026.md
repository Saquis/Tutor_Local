# Sesión 02-oct-2026 — Construcción del MVP + primera prueba real

**Fecha:** 2026-10-02, ~21:16–21:38 (GMT-5)
**Proyecto:** `C:\Users\RYZEN 5 GAMER\Tutor_Local\`
**Estado:** ✅ MVP funcional end-to-end · ❌ **NO cumple el objetivo de latencia**
**Resumen en una línea:** todo el circuito funciona y la caché es instantánea, pero la primera generación tarda **69,6 s** al primer token (objetivo: <1,5 s) → **46× fuera.**

---

## 1. Qué se hizo

### 1.1 Servidor en arquitectura hexagonal (Puertos y Adaptadores)
Se creó la estructura completa, sin que el dominio dependa de frameworks:

```
servidor/
├── main.py                           raíz de composición (cablea todo)
├── dominio/
│   ├── entidades.py                  Leccion, Resumen, ExamenDetectado
│   └── puertos.py                    interfaces: Cache, MotorResumen, MotorPreguntas, FiltroEtica
├── aplicacion/
│   ├── resumir_leccion.py            caso de uso: ética → caché → motor rápido
│   └── filtro_examenes.py            blocklist de exámenes
├── infraestructura/
│   ├── cache_sqlite.py               caché por hash (URL + contenido) en study.db
│   ├── motor_ollama.py               motor RÁPIDO: Ollama /api/chat con stream=True
│   └── motor_preguntas.py            motor PROFUNDO: DeepSeek API o Ollama local
├── entrada/
│   ├── api.py                        FastAPI: /ingest · /events (SSE) · /salud · / (dashboard)
│   └── dashboard.html                panel con token inyectado (__TOKEN__)
├── iniciar.bat                       arranque en Windows
├── requirements.txt
└── study.db                          caché SQLite (ya con datos de la prueba)
```

Endpoints: `POST /ingest` (texto de la lección, protegido con header `x-token`), `GET /events` (SSE para el dashboard), `GET /salud`, `GET /` (dashboard). Sin CORS a propósito.

### 1.2 Extensión de Chrome (MV3)
- `manifest.json` · `background.js` (hace el fetch a localhost) · `content.js` (sensor pasivo: lee `innerText`, atajo Ctrl+Shift+S, no hace clic ni scroll)

### 1.3 Scripts de prueba
- `pruebas/probe_deps.py`, `pruebas/enviar_leccion.py`, `pruebas/prueba_extremo_a_extremo.py`, `pruebas/medir_latencia.py`, `pruebas/leccion_ejemplo.json`
- Resultados guardados en `pruebas/resultado.txt`, `pruebas/latencia.txt`, `pruebas/latencia_err.txt`

---

## 2. Resultados medidos

Prueba end-to-end (`prueba_extremo_a_extremo.py`) contra el servidor con `phi3:3.8b`:

```
SERVIDOR OK
  motor_rapido        phi3:3.8b (local)
  motor_profundo      phi3:3.8b (local)
  cache               C:\Users\RYZEN 5 GAMER\Tutor_Local\servidor\study.db
  blocklist_examenes  True

⚠️ primer token:      69,64 s   (objetivo < 1,5 s)
⏱️  resumen completo:  91,38 s
📄 tokens recibidos:   221
```

Prueba de latencia de los 3 casos (`medir_latencia.py`):

| Caso | Resultado | Servidor |
|---|---|---|
| Lección ya vista (caché) | **0,43 s** ✅ | 0 ms |
| Lección nueva (genera con phi3) | **89,30 s** ❌ | 88.707 ms |
| La nueva repetida (caché) | **0,62 s** ✅ | 0 ms |

**Lectura:** la caché y el streaming funcionan (el resumen llegó en trozos, es correcto y en español). Lo que no funciona es **el costo de generar por primera vez**.

---

## 3. 🔴 Errores y problemas encontrados

### 3.1 El grave — Latencia 46× fuera del objetivo
- Medido: **69,64 s al primer token** / 91,38 s el resumen completo.
- Objetivo de diseño: <1,5 s al primer token.
- Ayer se había medido `phi3:3.8b` **directo a Ollama en 0,33–0,62 s**. La diferencia (×100) es el hallazgo de la sesión.

### 3.2 No hay cascada de modelos (rápido = profundo)
- `main.py` solo crea el motor profundo distinto **si existe `DEEPSEEK_API_KEY`**. Sin esa variable, rápido y profundo son **el mismo `phi3:3.8b`**.
- Consecuencia: el resumen rápido y la generación de preguntas **compiten por la misma GPU** (4 GB VRAM). El propio `resultado.txt` lo delata: `motor_rapido phi3:3.8b (local)` / `motor_profundo phi3:3.8b (local)`.

### 3.3 Los logs del servidor están vacíos
- `servidor/out.log` y `servidor/err.log` están en **0 bytes**.
- `iniciar.bat` no está redirigiendo la salida → si el servidor truena, **no queda rastro**. Hay que arreglarlo antes de la siguiente sesión de pruebas.

### 3.4 El proyecto no está bajo control de versiones
- `git status` → `fatal: not a git repository`. Existe `.gitignore` pero **no se ha hecho `git init`**.
- Sin commits, no hay forma de volver atrás si una prueba rompe algo.

### 3.5 `ms: 0` en la respuesta del ingest (confuso)
- En modo precómputo (sin `live`) el endpoint responde `{'ok': True, 'ms': 0}` inmediatamente, porque el trabajo sigue en segundo plano.
- Es correcto por diseño, pero **confunde** al leer `resultado.txt`: parece que no midió nada.

### 3.6 `ocr/` está vacío
- Falta `ocr_fallback.py`, que **debe correr en Windows** (WSL no ve la pantalla). Es el plan B si `innerText` no trae texto limpio.

### 3.7 Token por defecto inseguro
- `TUTOR_TOKEN` tiene default `"cambia-este-token"`. El servidor hoy corrió en Windows; si algún día se bindea a `0.0.0.0`, **hay que cambiarlo sí o sí** (el diseño sin CORS depende de ese token).

### 3.8 Nota de entorno
- El servidor corrió **nativo en Windows** (la ruta impresa en la prueba es `C:\...`), no en WSL como decía el diseño. Hay que decidir y dejarlo escrito: si vive en Windows, WSL no lo alcanza por `127.0.0.1` (necesita el gateway `172.30.16.1`).

---

## 4. Diagnóstico de la causa raíz (por qué 69 s y no 0,5 s)

Lo más probable, en orden:

1. **Prompt gigantesco.** `motor_ollama.py` manda `leccion.contenido_efectivo[:18000]` → hasta 18.000 caracteres ≈ **4.500–6.000 tokens** de entrada. Ollama procesa **todo el prefill antes del primer token**; el `stream=True` no ayuda con eso.
2. **4 GB de VRAM.** `phi3:3.8b` en Q4 pesa ~2,2 GB; con un contexto de ~6k tokens, la KV cache desborda y parte del cómputo cae a **CPU** → el prefill se vuelve lentísimo.
3. **La medición de ayer (0,33 s) fue con prompt corto**, no con 18k caracteres. Es decir: el modelo no es lento, **el tamaño de la entrada sí**.
4. Posible suma: modelo frío (sin `keep_alive`), `num_predict=400` y el motor profundo local compitiendo por la GPU.

**Experimentos propuestos (baratos y decisivos):**
- Medir el mismo `phi3` con prompts de 500 / 2.000 / 6.000 / 18.000 chars → confirmar la curva.
- Repetir mandando **solo la selección** en vez de la página completa.
- Probar `num_ctx` fijo bajo + `num_predict` menor.
- Comparar con un modelo más chico en la ruta crítica (`llama3.2:1b`, `qwen2.5:1.5b`).
- Verificar si Ollama está usando GPU de verdad (`ollama ps` → `100% GPU` vs `CPU`).

---

## 5. Qué sigue (orden sugerido)

1. **Arreglar los logs** de `iniciar.bat` (sin esto se prueba a ciegas).
2. **`git init` + primer commit.**
3. **Experimento de latencia vs tamaño de prompt** (el que decide el diseño).
4. Con el resultado: elegir el par rápido/profundo **de verdad** (rápido local y chico, profundo remoto).
5. `ocr_fallback.py` en Windows.
6. Prueba del `innerText` en una lección real (el hito que decide si el proyecto vive).

---

## 6. Inventario de archivos (lo que quedó en disco)

| Ruta | Para qué |
|---|---|
| `servidor/main.py` | raíz de composición + arranque uvicorn |
| `servidor/dominio/entidades.py` | `Leccion`, `Resumen`, `ExamenDetectado` |
| `servidor/dominio/puertos.py` | interfaces del hexágono |
| `servidor/aplicacion/resumir_leccion.py` | caso de uso principal |
| `servidor/aplicacion/filtro_examenes.py` | blocklist de exámenes |
| `servidor/infraestructura/cache_sqlite.py` | caché por hash en `study.db` |
| `servidor/infraestructura/motor_ollama.py` | motor rápido (Ollama streaming) |
| `servidor/infraestructura/motor_preguntas.py` | motor profundo (DeepSeek/Ollama) |
| `servidor/entrada/api.py` | FastAPI + SSE + token |
| `servidor/entrada/dashboard.html` | dashboard |
| `servidor/iniciar.bat` | arranque en Windows |
| `extension/manifest.json`, `background.js`, `content.js` | extensión Chrome MV3 |
| `pruebas/*.py`, `resultado.txt`, `latencia.txt` | pruebas y mediciones |

---

*Informe generado por Saquis (asistente) el 02-oct-2026, a pedido de Saquis (humano).*

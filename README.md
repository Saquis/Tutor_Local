# Tutor Local — Agente visual de asistencia

> **Lee lo que tienes abierto y te ayuda — sin automatizar nada.**

Servidor local + extensión de navegador. El humano navega y opera; el software
**solo lee**. Sin automatización de entrada no hay superficie de detección de bots.

---

## 1. El problema

Los agentes de navegador (browser-use, Playwright, CDP) **son detectables**:
`navigator.webdriver`, huella de headless, fingerprint TLS/JA3, bot management por ML.
En bancos, portales oficiales y trámites **no sirven**.

Y capturar la pantalla y mandarla a un modelo grande es **lento** (medido: ~40 s
de ida y vuelta), estático, y el sistema operativo lo trata como spyware.

**La solución es la del sentido común:** el humano hace el login y la navegación;
el software lee el **texto** de la página (no píxeles) y responde rápido.

| | Captura de pantalla | `innerText` |
|---|---|---|
| Tamaño | ~2.000 KB | **~10 KB** |
| Precisión | depende de la imagen | **exacta** |
| Detección | — | **ninguna** |

---

## 2. Mediciones reales (esta máquina: RTX 3050 Ti, **4 GB VRAM**)

Todo lo de abajo está medido, no estimado.

### El tamaño del contexto domina la latencia

| `num_ctx` | Memoria del modelo | Reparto | 1er token |
|---|---|---|---|
| 8192 | 5,9 GB | **66% CPU** / 34% GPU | 11,10 s |
| 4096 | — | — | 4,72 s |
| **2048** | 3,1 GB | 29% CPU / **71% GPU** | **2,91 s** |

El modelo no cabía en la GPU y Ollama tiraba **dos tercios** del cómputo a CPU.
Bajar el contexto de 8192 a 2048 acelera el primer token **3,8×**.

### 🚨 Ollama trunca en silencio (bug encontrado)

| Entrada | `num_ctx` | Tokens **realmente** procesados |
|---|---|---|
| 6.000 chars | 2048 | **2048** ← ¡recortado sin avisar! |
| 6.000 chars | 4096 | 2110 ← el valor real |

Si la entrada no cabe, **Ollama corta el prompt y nadie se entera**: el resumen
sale de media lección. La clase lo previene con `_entrada_segura()`:

```
num_ctx ≥ tokens(entrada) + num_predict + margen      (tokens ≈ chars / 2,8 en español)
```

### Visión remota

`deepseek-flash` procesa una imagen de 274 KB en **2,65 s** y la describe bien.
Confirma que la ruta visual es viable cuando el DOM no alcanza.

---

## 3. Arquitectura — hexagonal (puertos y adaptadores)

No es decorativa: **los adaptadores son genuinamente intercambiables.**

```
                    ┌─────────────────────────────┐
   TÚ navegas  ───► │  Extensión (solo lee DOM)   │
                    └──────────────┬──────────────┘
                                   │ POST /ingest (token)
                                   ▼
        ┌───────────────────────────────────────────────┐
        │  ENTRADA      FastAPI · /events (SSE) · /     │
        ├───────────────────────────────────────────────┤
        │  APLICACIÓN   ResumirLeccion · FiltroExamenes │
        ├───────────────────────────────────────────────┤
        │  DOMINIO      Leccion · Pregunta · puertos    │
        ├───────────────────────────────────────────────┤
        │  INFRA        CacheSqlite · MotorOllama ·     │
        │               MotorPreguntas (Ollama/DeepSeek)│
        └───────────────────────────────────────────────┘
```

**El dominio no importa FastAPI, ni httpx, ni sqlite.** Solo Python estándar.

### Puertos e implementaciones

| Puerto | Implementación A | Implementación B |
|---|---|---|
| `MotorResumen` | Ollama local (phi3) | — |
| `MotorPreguntas` | Ollama local | DeepSeek API |
| `Cache` | SQLite | memoria (tests) |
| `FiltroEtica` | blocklist de exámenes | — |

Cambiar de modelo o de fuente de texto **no toca la lógica de negocio.**

---

## 4. La regla ética

El sistema **se niega a ayudar en evaluaciones.** Está en `FiltroExamenes`, y
los tests verifican que **no llama al modelo** cuando detecta proctoring:

```python
PATRON_EXAMEN = r"proctor|take[-_ ]?exam|exam[-_ ]?session|official[-_ ]?exam
                 |pearsonvue|certiport|examity|respondus|lockdown[-_ ]?browser|honorlock"
```

Es específico a propósito: **"Exam Prep" es estudio legítimo y NO se bloquea.**

---

## 5. Cómo correrlo

```bash
# 1. Dependencias (Python 3.12+)
python -m pip install -r servidor/requirements.txt

# 2. Ollama con el modelo
ollama pull phi3:3.8b

# 3. Arrancar el servidor
servidor\iniciar.bat          # Windows
# o:  python -m servidor.main

# 4. Instalar la extensión en Brave/Chrome
#    brave://extensions  →  Modo desarrollador  →  Cargar descompromida
#    → carpeta  extension/

# 5. Abrir el panel
#    http://127.0.0.1:8765
```

**Variables de entorno** (todas opcionales):

| Variable | Default | Para qué |
|---|---|---|
| `TUTOR_TOKEN` | (requerido) | Token compartido con la extensión |
| `TUTOR_NUM_CTX` | `4096` | Ventana de contexto de Ollama |
| `TUTOR_MAX_CHARS` | calculado | Límite de entrada (anti-truncamiento) |
| `TUTOR_MODELO` | `phi3:3.8b` | Modelo local |
| `TUTOR_DB` | `servidor/study.db` | Base de datos de caché |
| `DEEPSEEK_API_KEY` | — | Si se quiere el motor profundo por API |

---

## 6. Tests

```bash
python -m unittest discover -s pruebas -v
```

**16 tests · 0,005 s · sin red, sin base de datos, sin GPU.**

Eso es el pago de la arquitectura hexagonal: el núcleo se prueba con
**adaptadores falsos** que implementan los puertos.

Cubren:
- Entidades (selección sobre contexto, validación de preguntas)
- **La regla ética** (bloquea proctoring, **no** bloquea "exam prep")
- Casos de uso end-to-end con fakes (caché, streaming, errores)

---

## 7. Lo que se descartó (y por qué)

| Camino | Veredicto |
|---|---|
| Agente CDP / Playwright / browser-use | ❌ **Detectable** por los sitios |
| Foto de pantalla → modelo grande | ❌ **~40 s** y estático |
| Bucle automático de captura | ❌ **Bloqueado por el antivirus** (firma de spyware) |
| Extensión pasiva + modelo rápido | ✅ **Sin obstáculos** |

---

## 8. Estado y próximos pasos

- [x] Servidor hexagonal + extensión + panel
- [x] Caché por hash (0,43 s al repetir)
- [x] Anti-truncamiento (`num_ctx` + entrada segura)
- [x] Tests del núcleo
- [x] Token de seguridad
- [ ] Validar `innerText` en las páginas reales del usuario
- [ ] Modo "solo selección" (explicar el párrafo marcado)
- [ ] OCR para canvas/PDF

---

## 9. Estructura

```
servidor/
├── dominio/          entidades + puertos (puro)
├── aplicacion/       casos de uso + blocklist ética
├── infraestructura/  adaptadores (SQLite · Ollama · DeepSeek)
└── entrada/          FastAPI + panel SSE
extension/            manifest · background · content (MV3)
ocr/                  captura de pantalla (respaldo)
pruebas/              tests + mediciones
memoria/              bitácora y decisiones del proyecto
```

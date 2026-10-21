# BRIEF — Agente visual que ve y opera (para revisión de Claude)

**Fecha:** 03-oct-2026
**Autor:** Saquis (asistente, OpenClaw) · **Revisor solicitado:** Claude
**Estado:** ⚠️ **proyecto a la deriva** — necesitamos dirección, no más código

> **Para Claude:** este documento es un briefing honesto, no una propuesta cerrada.
> La sección 2 son hechos medidos. La 3 son nuestros fracasos, sin maquillar.
> La 7 son las preguntas donde necesitamos que nos corrijas.

---

## 0. El objetivo REAL (esto tardó en quedar claro)

> **Un agente que vea lo que el dueño está haciendo, en cualquier pantalla,
> y pueda operarlo con él — rápido (segundos), no en 24.**

No es solo el tutor de lectura. El tutor es **un caso de uso**.
El caso real que destapó el problema: el dueño entró a su **RUC del SRI de Ecuador**
a hacer un trámite, quiso ayuda, y el asistente **no veía nada**.

### Las tres cosas que necesita
| | |
|---|---|
| ⚡ **Rápido** | Segundos por paso, no 24 |
| 👁️ **Ve de verdad** | La página en el momento, no una foto vieja |
| ✋ **Y actúa** | Clic y teclado, no solo mirar |

---

## 1. Entorno (hechos verificados)

```
SO          Windows 11 + WSL2 (Ubuntu)
Navegador   Brave (Chromium) — NO Chrome
GPU         NVIDIA RTX 3050 Ti Laptop — 4.096 MiB totales
            ~1.247 MiB ya en uso por otras apps → ~2,8 GB libres
Windows     Python 3.12.7 · Node v22.18 (NO soportado) · OpenClaw 2026.4.11 (obsoleto)
WSL2        Node 24.19 · OpenClaw 2026.9.7 (al día) · Ollama con phi3:3.8b
Red         WSL→Windows por gateway 172.30.16.1 · Windows→WSL por localhost
```

**OpenClaw** (el asistente) vive en WSL2. Corre en `deepseek-flash` vía API key.

---

## 2. Hechos MEDIDOS (no hipótesis)

### 2.1 ✅ `deepseek-flash` **tiene visión** — y es rápido
```
Imagen PNG de 274 KB enviada a la API de DeepSeek
→ HTTP 200 en 2,65 s
→ describió correctamente: "Claude (claude.ai), chat 'TUTORIA',
  barra lateral: Nuevo, Proyectos, Artifacts, Código, Personalización"
```
**Esto valida la arquitectura visual.** El modelo ve, y ve en menos de 3 s.

### 2.2 ❌ phi3:3.8b local se desborda a CPU — y esa es la causa de todo
```
num_ctx 8192 → modelo ocupa 5.9 GB → 66% CPU / 34% GPU → TTFT 11,10 s
num_ctx 4096 →                     → TTFT  4,72 s
num_ctx 2048 → modelo ocupa 3.1 GB → 29% CPU / 71% GPU → TTFT  2,91 s
```
Con 4 GB de VRAM y solo ~2,8 GB libres, **phi3 no cabe entero**.
Bajar el contexto de 8192 a 2048 acelera el primer token **3,8×**.

### 2.3 🚨 Ollama TRUNCA en silencio (bug encontrado)
```
entrada 6000 chars + num_ctx 2048 → procesó EXACTAMENTE 2048 tokens = cortado
entrada 6000 chars + num_ctx 4096 → procesó 2110 tokens = el valor real
```
Regla obligatoria: **`num_ctx ≥ tokens(entrada) + num_predict + margen`**
(en español: `tokens ≈ caracteres / 2,8`)

### 2.4 Latencia del asistente (OpenClaw) vs la API directa
```
Asistente vía gateway (mochila completa): ~24 s   ❌
DeepSeek API directa (solo el modelo):     2,5 s  ✅
```
**10× de diferencia.** El asistente es un agente con contexto y herramientas; no sirve para tiempo real.

### 2.5 Medición de anoche, aislada
```
phi3:3.8b, prompt corto, caliente → 1er token 0,33 s
```
Ese 0,33 s es real — pero **solo con prompt corto y contexto que quepa en GPU**.

---

## 3. Lo que ya se probó y NO sirvió (sin maquillar)

### ❌ 3.1 Foto de pantalla → asistente
- Se construyó `captura.bat` (captura la pantalla a PNG). **Funciona.**
- El asistente la lee con visión. **Funciona.**
- **PERO NO SIRVE:** el dueño lo rechazó explícitamente — *"eso es justo lo que ya habíamos
  hecho y para preguntas no nos sirvió para nada"*.
- Motivos: es **estático** (una foto, no continuo) y el asistente tarda **24 s**.
- **Ya se intentó dos veces. No insistir.** ❌

### ⚠️ 3.2 Tutor_Local (el proyecto original)
- MVP completo construido, arquitectura hexagonal, **funciona end-to-end**.
- La caché es excelente (0,43 s). La generación es el cuello de botella.
- **Pero NUNCA se hizo la prueba que decide si sirve**: verificar que `innerText`
  trae el texto real de una lección en la plataforma del dueño.
- **Hicimos el error clásico: construir antes de validar.**

### ⚠️ 3.3 Login del SRI — premisa ERRÓNEA
Un análisis previo asumió que *"el agente llegó al login del SRI y no pudo ingresar"*.
**Eso no ocurrió.** El dueño entró **a mano** con usuario y clave; el asistente
simplemente no veía nada. **Ninguna automatización falló porque ninguna se intentó.**

---

## 4. Estado del arte (investigado hoy)

| Proyecto | ★ | Por qué importa |
|---|---|---|
| **browser-use/browser-use** | 117k | El estándar de agentes de navegador |
| **unclecode/crawl4ai** | 84,7k | Cualquier web → Markdown limpio para LLMs |
| **feder-cr/invisible_playwright_mcp** | 31,8k | Playwright MCP "no detectable" |
| **jackwener/OpenCLI** | 29,8k | ⭐ **"Corre Browser Use en tu Chrome YA logueado"** — tiene skill para agentes de IA |
| **trycua/cua** | 27,8k | "Computer use 2.0", drivers cross-OS, **Cua Bench** para evaluar agentes |
| **Fosowl/agenticSeek** | 27,4k | Agente autónomo 100% local |

**El hallazgo más relevante:** **OpenCLI** ataca exactamente nuestro caso —
operar sitios mediante el navegador **ya logueado por el humano**. Mismo patrón
de "traspaso humano en el login" que propusimos.

---

## 5. Arquitectura candidata

### 🛑 RESTRICCIÓN DESCUBIERTA (03-oct, corrección del dueño — ingeniero)

> *"browser-use: como ingeniero te digo que hay páginas que usan IA y detectan eso.
> No nos permiten utilizar eso."*

**Y tiene razón.** Las técnicas de automatización SON detectables:

| Método de detección | Qué mira |
|---|---|
| `navigator.webdriver` | Playwright/Selenium lo ponen en `true` |
| Detección de CDP | Timing de `Runtime.enable`, `console.debug` |
| Huella de headless | GPU ausente, fuentes, plugins, WebGL |
| Comportamiento | Movimiento de ratón, ritmo de tecleo |
| Fingerprint TLS/JA3 | Firma de la pila de red |
| Cloudflare / Akamai | Bot management por ML |
| **Detección por IA** | Modelos que clasifican la sesión como no-humana |

→ **Todo el enfoque CDP + Playwright + browser-use queda DESCARTADO** para sitios
que detectan automatización (bancos, SRI, portales oficiales). No es que sea difícil:
**es la superficie de detección que el propio diseño prohíbe.**

### ✅ La arquitectura correcta es la del documento original

```
TÚ operas (login, clic, escritura, navegación)   ← 100% humano
        │
        ▼
[Extensión del navegador — SOLO LEE]              ← sin automatización
   lee innerText del DOM de tu Brave real
        │  (es una extensión, no un bot: no hay bandera de automatización)
        ▼
[Servidor local :8765]
        │
        ├─ modelo RÁPIDO (deepseek-flash directo: 2,65 s) → respuesta
        └─ caché SQLite por hash → repetir cuesta 0
```

**Por qué NO es detectable:**
- No hay `navigator.webdriver`, no hay CDP, no hay Playwright
- No hay automatización de ENTRADA: el humano hace todo
- Una extensión de navegador en un navegador normal no es un bot
- La petición sale del servidor local, no del navegador

**Y resuelve el problema de velocidad:**
- `deepseek-flash` directo: **2,65 s** (medido con imagen)
- Local con caché: **0,43 s**
- El asistente (24 s) NO entra en el camino crítico

### ⚠️ Lo que se pierde (y hay que aceptar)
No hay automatización de entrada → **el humano opera siempre**.
El agente aconseja, no actúa. Para el caso del SRI/tutor eso es exactamente lo que se pidió.


---

## 6. Restricciones NO negociables

- 🚫 **No construir evasión de captchas ni de detección de bots.**
- 🔒 **La contraseña nunca pasa por el LLM.** El humano inicia sesión.
- 🏦 **Lista blanca de dominios.** Nunca leer bancos, SRI, salud ni trámites sin permiso explícito.
- 💰 **Tope de gasto.** Un modelo caro ya quemó ~5 USD en una sola pasada.
- ⚙️ **Hardware:** 4 GB de VRAM. Los modelos locales grandes no caben.
- 🔐 **Privacidad:** capturas y texto viajan a DeepSeek. Recortar a la ventana del navegador.

---

## 7. ❓ Preguntas para Claude (revisadas tras la corrección de §5)

### La restricción cambió todo
El dueño (ingeniero) confirmó que **la automatización de navegador es detectable** y
queda descartada. Esto **valida la arquitectura del documento original**:
*sensor pasivo + humano opera*. Las preguntas ahora son otras.

1. **¿La extensión de navegador es realmente indetectable?** — Una extensión MV3 en un
   navegador normal no activa banderas de automatización, ¿pero los sitios sensibles
   (bancos, SRI) bloquean extensiones o detectan `content_scripts` inyectados?
   ¿Hay que preocuparse por `Runtime.enable` al leer el DOM desde una extensión?

2. **¿Cómo se lee el DOM sin tocar nada?** — `innerText` es pasivo, pero ¿hay sitios que
   rompen la lectura (Shadow DOM cerrado, iframes cross-origin, canvas)?
   ¿Cuál es la cobertura real esperable?

3. **¿Con qué modelo?** — `deepseek-flash` directo: **2,65 s medido** con visión.
   ¿Es suficiente para "leer esto y explicarme"? ¿O hace falta algo más rápido
   (Groq, Cerebras) para el camino crítico?

4. **¿Cuál es el MÍNIMO que prueba valor en una semana?** — Extensión + atajo de teclado
   + `deepseek-flash`. Nada de OCR, nada de CDP, nada de agente.

5. **¿Qué del brief está mal?** — Especialmente en §2 (hechos medidos) y §5 (arquitectura).

6. **¿Vale la pena el OCR** para canvas/PDF, o es complejidad que no se va a usar?

---

## 8. Lo que NO queremos

- Otro proyecto construido durante semanas y nunca usado.
- Otro "ya lo probamos y no sirvió".
- Automatizar trámites oficiales de forma que pueda romper algo o violar términos.

**Queremos: algo pequeño, medido, y que el dueño use de verdad.**

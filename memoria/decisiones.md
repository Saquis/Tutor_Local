# Decisiones — Tutor Local

## D-001 · Sensor pasivo, no agente (heredado del diseño)
**Fecha:** 2026-10-01
**Decisión:** El software NO navega ni hace clic. Solo lee lo que el humano ya abrió.
**Por qué:** elimina la superficie de detección de bots. Sin automatización de entrada no hay bot que detectar.
**Alternativa descartada:** agentes automatizadores (Browser Use, etc.) — disparan detección y violan ToS.

## D-002 · Texto, no píxeles
**Fecha:** 2026-10-01
**Decisión:** Usar `innerText` del DOM. OCR solo como fallback para canvas/PDF.
**Por qué:** 10 KB vs 2 MB (~100× menos bytes) y 5-10× menos latencia al primer token.
**Medido:** modelo local phi3:3.8b → 0.33 s al primer token. Agente remoto → ~24 s.

## D-003 · Modelo LOCAL para la ruta rápida
**Fecha:** 2026-10-01
**Decisión:** Ollama local (phi3:3.8b) para el resumen en streaming. Modelo grande solo async.
**Por qué:** medido. Local 0.33 s vs API remota 2.5 s vs agente 24 s. El objetivo es <1.5 s.
**Límite:** GPU RTX 3050 Ti con 4 GB VRAM → modelos de 3-4B máximo.

## D-004 · Ubicación del proyecto
**Fecha:** 2026-10-02
**Decisión:** `C:\Users\RYZEN 5 GAMER\Tutor_Local\` — hermano de `tinder_CaninoV1`.
**Por qué:** pedido explícito de Saquis. Misma convención (carpeta `memoria/`).

## D-005 · Blocklist de exámenes (no negociable)
**Fecha:** 2026-10-01
**Decisión:** El servidor se NIEGA a ayudar si detecta una página de examen/proctoring.
**Patrón:** `proctor|take[-_ ]?exam|exam[-_ ]?session|official[-_ ]?exam|pearsonvue|certiport|examity`
**Por qué:** decisión ética de diseño. No desactivar.

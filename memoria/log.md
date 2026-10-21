# Log — Tutor Local

## 2026-10-01 · Diseño y decisiones
- Se leyó y consolidó el doc de diseño (venía de 3 modelos distintos: Claude, Gemini, Z.ai).
- **Mediciones reales de latencia** (esto cambió el diseño):
  - phi3:3.8b local (Ollama, GPU) → **0.33–0.62 s** al primer token
  - DeepSeek Flash (API directa) → 2.5–2.9 s
  - Agente vía gateway → ~24 s ❌
- Conclusión: **la ruta rápida debe ser un modelo LOCAL**. El agente remoto es la capa profunda async.
- Se descartó "darle ojos al agente remoto" (capturas → agente): la latencia lo hace inútil en vivo.
- Hardware verificado: RTX 3050 Ti, **4 GB VRAM** → límite de 3-4B.

## 2026-10-02 · Creación del proyecto
- Carpeta creada por pedido de Saquis.
- Ubicación: `C:\Users\RYZEN 5 GAMER\Tutor_Local\`
- Estructura: `servidor/`, `extension/`, `ocr/`, `pruebas/`, `memoria/`
- README con arquitectura, reparto Windows/WSL y presupuesto de latencia.

### Próximo paso
- [ ] **Prueba del `innerText`** en una lección real (decide si el proyecto vive)

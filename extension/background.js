// Tutor Local — service worker
//
// Hace el fetch a localhost, lo que evita las restricciones de red
// local que tienen las páginas web. No lee nada por su cuenta:
// solo reenvía lo que el sensor (content.js) le pasa.

const SERVIDOR = "http://127.0.0.1:8765";

// ⚠️ Debe coincidir con TUTOR_TOKEN del servidor.
// Configúralo en config.js (ver config.example.js) — no lo hardcodees aquí.
import { TUTOR_TOKEN } from "./config.js";
const TOKEN = TUTOR_TOKEN;

chrome.runtime.onMessage.addListener((msg, _remitente, responder) => {
  if (msg?.type !== "ingest") return;

  fetch(`${SERVIDOR}/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-token": TOKEN,
    },
    body: JSON.stringify(msg.payload),
  })
    .then((r) => r.json())
    .then((d) => responder?.({ ok: true, respuesta: d }))
    .catch((e) => {
      console.warn("[tutor] backend no disponible:", e?.message || e);
      responder?.({ ok: false, error: String(e?.message || e) });
    });

  return true; // respuesta asíncrona
});

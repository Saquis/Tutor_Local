// Tutor Local — sensor pasivo
//
// REGLA DE ORO: solo LEE. No hace clic, no escribe, no navega,
// no inyecta interfaz. Tú navegas; esto únicamente lee lo abierto.
//
// Dos disparos:
//   1. Manual:  Ctrl+Shift+S  (funciona en cualquier página)
//   2. Auto:    al cambiar de lección, SOLO en los dominios listados

// Pon aquí tus plataformas de estudio. El auto-disparo solo ocurre en estas.
const DOMINIOS_AUTO = [
  // "skillbuilder.aws",
  // "www.udemy.com",
  // "app.pluralsight.com",
  // "www.coursera.org",
];

const esTop = window.top === window;
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

const esDominioDeCurso = () =>
  DOMINIOS_AUTO.some((d) => location.hostname.endsWith(d));

function extraer() {
  const seleccion = (window.getSelection() + "").trim();

  // innerText usa el árbol renderizado: respeta visibilidad
  // e incluye contenido de Shadow DOM.
  const texto = (document.body?.innerText || "")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
    .slice(0, 20000);

  return {
    url: location.href,
    titulo: document.title,
    texto,
    seleccion: seleccion.slice(0, 4000),
  };
}

function enviar(vivo) {
  const payload = { ...extraer(), live: vivo };
  chrome.runtime.sendMessage({ type: "ingest", payload }, (resp) => {
    if (chrome.runtime.lastError) {
      console.warn("[tutor] no se pudo contactar al service worker");
      return;
    }
    if (resp && !resp.ok) {
      console.warn("[tutor] backend:", resp.error);
    }
  });
}

// Espera a que una SPA termine de renderizar (longitud estable).
async function esperarEstable(maxMs = 8000) {
  let anterior = -1;
  let iguales = 0;
  const inicio = Date.now();

  while (Date.now() - inicio < maxMs) {
    const largo = document.body?.innerText?.length ?? 0;
    if (largo > 200 && largo === anterior) {
      if (++iguales >= 2) return true;
    } else {
      iguales = 0;
    }
    anterior = largo;
    await dormir(500);
  }
  return false;
}

if (esTop) {
  // ---- 1. Disparo manual ----
  addEventListener(
    "keydown",
    (e) => {
      if (e.ctrlKey && e.shiftKey && e.code === "KeyS") {
        e.preventDefault();
        enviar(true);
      }
    },
    { capture: true }
  );

  // ---- 2. Disparo automático (solo la lección que TÚ abriste) ----
  let ultima = "";
  let ocupado = false;

  setInterval(async () => {
    if (!esDominioDeCurso() || ocupado) return;

    const ahora = location.href + "|" + document.title;
    if (ahora === ultima) return;

    ocupado = true;
    if (await esperarEstable()) {
      ultima = ahora;
      enviar(false); // precómputo: no bloquea, se guarda en caché
    }
    ocupado = false;
  }, 800);
}

// Modo claro, oscuro o el del sistema (8.4), ANTES de pintar: así no hay un destello
// claro al abrir en oscuro. Lo mismo hace src/tema.ts. Va en archivo aparte (no en línea)
// para que la política de seguridad de contenido prohíba todo script en línea (v2.3 · C13).
(function () {
  try {
    var p = localStorage.getItem("cc-tema") || "sistema";
    var oscuro = p === "oscuro" || (p === "sistema" && matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.setAttribute("data-tema", oscuro ? "oscuro" : "claro");
  } catch (e) {
    document.documentElement.setAttribute("data-tema", "claro");
  }
})();

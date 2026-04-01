/* Floating TOC (right sidebar) toggle for MkDocs Material */
(function () {
  const STORAGE_KEY = "mkdocs.toc.hidden";
  const CLASS_HIDDEN = "toc-hidden";

  function hasSecondarySidebar() {
    return document.querySelector(".md-sidebar--secondary") !== null;
  }

  function applyState(hidden) {
    if (hidden) {
      document.body.classList.add(CLASS_HIDDEN);
    } else {
      document.body.classList.remove(CLASS_HIDDEN);
    }

    const button = document.getElementById("toc-toggle-button");
    if (button) {
      button.setAttribute("aria-pressed", hidden ? "true" : "false");
      button.title = hidden ? "Afficher la table des matières" : "Masquer la table des matières";
      const label = button.querySelector(".toc-toggle-label");
      if (label) {
        label.textContent = hidden ? "TOC +" : "TOC -";
      }
    }
  }

  function createButton() {
    if (document.getElementById("toc-toggle-button") || !hasSecondarySidebar()) {
      return;
    }

    const button = document.createElement("button");
    button.id = "toc-toggle-button";
    button.type = "button";
    button.className = "toc-toggle-fab";
    button.setAttribute("aria-controls", "__toc");
    button.setAttribute("aria-label", "Afficher ou masquer la table des matières");
    button.innerHTML = '<span class="toc-toggle-label">TOC -</span>';

    button.addEventListener("click", function () {
      const current = localStorage.getItem(STORAGE_KEY) === "1";
      const next = !current;
      localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      applyState(next);
    });

    document.body.appendChild(button);
  }

  function init() {
    createButton();
    applyState(localStorage.getItem(STORAGE_KEY) === "1");
  }

  document.addEventListener("DOMContentLoaded", init);
  document.addEventListener("navigation", init);
})();

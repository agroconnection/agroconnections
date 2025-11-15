// --------- CAMBIO DE PESTAÑAS ---------
const navButtons = document.querySelectorAll(".nav-link");
const sections = document.querySelectorAll(".page-section");

function showSection(id) {
  sections.forEach((sec) =>
    sec.classList.toggle("is-visible", sec.id === id)
  );

  navButtons.forEach((btn) =>
    btn.classList.toggle("active", btn.dataset.section === id)
  );

  // subir un poco la página cuando cambias de sección
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Menú principal
navButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.section;
    if (target) showSection(target);
  });
});

// Botones dentro de la página con data-section (hero, etc.)
document.querySelectorAll("[data-section]").forEach((el) => {
  if (!el.classList.contains("nav-link")) {
    el.addEventListener("click", (e) => {
      const target = el.dataset.section;
      if (target) {
        e.preventDefault();
        showSection(target);
      }
    });
  }
});


// --------- CAMBIO DE PESTAÑAS (SECCIONES) ---------

// Botones del menú
const navButtons = document.querySelectorAll(".nav-link");
// Todas las secciones principales
const sections = document.querySelectorAll(".page-section");

function showSection(sectionId) {
  // Oculta todas
  sections.forEach((sec) => sec.classList.remove("is-visible"));

  // Muestra la solicitada
  const target = document.getElementById(sectionId);
  if (target) {
    target.classList.add("is-visible");
  }

  // Actualiza el estado activo del menú
  navButtons.forEach((btn) => {
    if (btn.dataset.section === sectionId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
}

// Eventos para cada botón del menú
navButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.section;
    if (target) {
      showSection(target);
    }
  });
});

// --------- BOTONES QUE NAVEGAN ENTRE SECCIONES (Home) ---------
document.querySelectorAll("[data-section]").forEach((el) => {
  el.addEventListener("click", (e) => {
    // Si es botón normal (no nav-link) también navega
    if (!el.classList.contains("nav-link")) {
      const target = el.dataset.section;
      if (target) {
        e.preventDefault();
        showSection(target);
      }
    }
  });
});

// --------- FORMULARIO MULTIPASO ---------

const steps = document.querySelectorAll(".form-step");

function showStep(stepNumber) {
  steps.forEach((step) => {
    if (step.dataset.step === String(stepNumber)) {
      step.classList.add("is-visible");
    } else {
      step.classList.remove("is-visible");
    }
  });
}

// Botones "Siguiente"
document.querySelectorAll("[data-next-step]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const next = btn.dataset.nextStep;
    showStep(next);
  });
});

// Botones "Regresar"
document.querySelectorAll("[data-prev-step]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const prev = btn.dataset.prevStep;
    showStep(prev);
  });
});

// Envío del formulario (solo demostrativo)
const form = document.querySelector(".wizard-form");
if (form) {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    alert(
      "Tu registro se envió correctamente. En breve nos pondremos en contacto contigo."
    );
    form.reset();
    showStep(1);
    showSection("inicio");
  });
}

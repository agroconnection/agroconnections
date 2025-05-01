
function mostrar(id) {
  document.querySelectorAll('main section').forEach(s => s.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('active');
}

window.onload = function () {
  mostrar('inicio');

  const form = document.getElementById('registroForm');
  const resultado = document.getElementById('resultadoEvaluacion');
  const modal = document.getElementById('modalExito');
  const descarga = document.getElementById('descargaPDF');

  form.addEventListener('change', function () {
    const edad = parseInt(form.edad.value);
    const antecedentes = form.antecedentes.value;

    if (!edad || !antecedentes) {
      resultado.innerText = '';
      return;
    }

    if (antecedentes === "si") {
      resultado.innerText = "❌ No elegible: Tiene antecedentes en EE.UU.";
      resultado.style.color = "red";
    } else if (edad < 18 || edad > 45) {
      resultado.innerText = "⚠️ Revisión necesaria: Edad fuera del rango preferido.";
      resultado.style.color = "orange";
    } else {
      resultado.innerText = "✅ Candidato elegible.";
      resultado.style.color = "green";
    }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const edad = parseInt(form.edad.value);
    const antecedentes = form.antecedentes.value;

    if (antecedentes === "si") {
      alert("❌ No elegible: El sistema detectó antecedentes en EE.UU.");
      return;
    }

    if (edad < 18 || edad > 45) {
      alert("⚠️ Edad fuera del rango preferido (18-45 años). Registro no enviado.");
      return;
    }

    const formData = new FormData(form);
    fetch("https://script.google.com/macros/s/AKfycby3dUxdfD3512EAXkL8JN32nTzRQ2PBSR8DenUoJEIRzxRjb0mEMfa3kL2UCSR9Hyzc/exec", {
      method: "POST",
      body: formData
    })
    .then(res => res.text())
    .then(msg => {
      modal.style.display = "flex";
      descarga.style.display = "block";
      generarPDF();
      enviarCorreo(form.correo.value);
      enviarWhatsApp(form.nombre.value);
      form.reset();
    })
    .catch(err => alert("❌ Error al enviar formulario"));
  });
};

function generarPDF() {
  alert("📄 Aquí se genera y descarga el PDF con jsPDF (simulado).");
}

function enviarCorreo(correo) {
  console.log("✉️ Enviando correo a:", correo);
}

function enviarWhatsApp(nombre) {
  console.log("📲 Enviando WhatsApp a administración con registro de:", nombre);
}

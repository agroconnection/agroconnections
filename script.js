
document.getElementById("formularioContacto").addEventListener("submit", function(e) {
  e.preventDefault();

  const data = {
    nombre: this.nombre.value,
    edad: this.edad.value,
    perfil: this.perfil.value,
    telefono: this.telefono.value,
    correo: this.correo.value
  };

  fetch("https://script.google.com/macros/s/AKfycbxmRzVjB5JJEmpCiI-ndd-79dVfWO5mDKL_pixXaD0m6SK-GaooGJGgxqwpVFZ3fFaa/exec", {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json"
    }
  })
  .then(res => res.json())
  .then(res => {
    if (res.result === "success") {
      Swal.fire("¡Enviado!", "Tu información fue registrada exitosamente.", "success");
      this.reset();
    } else {
      Swal.fire("Error", "Hubo un problema al enviar tus datos.", "error");
    }
  })
  .catch(err => {
    Swal.fire("Error", "No se pudo conectar con el servidor.", "error");
    console.error(err);
  });
});

// Botón para subir al inicio
const btn = document.getElementById('btnSubir');
if (btn) {
  window.addEventListener('scroll', () => {
    btn.style.display = window.scrollY > 200 ? 'block' : 'none';
  });

  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

// Manejo del formulario de contacto
const formulario = document.getElementById('formularioContacto');
if (formulario) {
  formulario.addEventListener('submit', function(event) {
    event.preventDefault();
    alert('✅ Gracias por contactarnos. Te responderemos pronto.');
    const mensaje = document.getElementById("formMensaje");
    if (mensaje) mensaje.style.display = "block";
    formulario.reset();
  });
}

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

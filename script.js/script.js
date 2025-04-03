// Confirmación de envío del formulario
const formulario = document.getElementById('formularioContacto');
formulario.addEventListener('submit', function(event) {
  event.preventDefault();
  alert('✅ ¡Gracias por contactarnos! Nos comunicaremos contigo pronto.');
  formulario.reset();
});

// Mostrar botón "Volver arriba" al hacer scroll
const btnSubir = document.getElementById('btnSubir');
window.addEventListener('scroll', () => {
  if (window.scrollY > 300) {
    btnSubir.style.display = 'block';
  } else {
    btnSubir.style.display = 'none';
  }
});

// Scroll suave al hacer clic en el botón
btnSubir.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

console.log("¡Página cargada correctamente!");

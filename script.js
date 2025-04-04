const formulario = document.getElementById('formularioContacto');
formulario.addEventListener('submit', function(event) {
  event.preventDefault();
  alert('✅ Gracias por contactarnos. Te responderemos pronto.');
  formulario.reset();
});
const btn = document.getElementById('btnSubir');
window.addEventListener('scroll', () => {
  btn.style.display = window.scrollY > 200 ? 'block' : 'none';
});
btn.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});
// Registrar Service Worker (PWA)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

// Ocultar alertas automáticamente después de 4 segundos
document.querySelectorAll('.alerta').forEach(function(alerta) {
  setTimeout(function() {
    alerta.style.transition = 'opacity 0.5s ease';
    alerta.style.opacity = '0';
    setTimeout(function() { alerta.remove(); }, 500);
  }, 4000);
});

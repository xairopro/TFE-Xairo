// Wake Lock helper. Re-pídese ao recuperar visibilidade.
(function() {
  let wakeLock = null;
  async function request() {
    try {
      if ('wakeLock' in navigator) {
        wakeLock = await navigator.wakeLock.request('screen');
        wakeLock.addEventListener('release', () => { wakeLock = null; });
      }
    } catch (e) { /* unsupported */ }
  }
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') request();
  });
  window.addEventListener('load', request);
})();

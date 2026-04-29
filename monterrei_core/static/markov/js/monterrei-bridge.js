// Bridge para Monterrei: recibe postMessage do panel admin e dispara
// os controis internos do Markov.
//
// Protocolo:
//   {type: 'markov', action: 'set', id: '<element-id>', value: <any>}
//   {type: 'markov', action: 'click', id: '<button-id>'}
//   {type: 'markov', action: 'reset' | 'next' | 'auto'}  (atallos)
(function() {
  function setControl(id, value) {
    const el = document.getElementById(id);
    if (!el) { console.warn('[markov-bridge] id non atopado:', id); return; }
    if (el.tagName === 'INPUT' && el.type === 'color') {
      el.value = value;
      el.dispatchEvent(new Event('input', { bubbles: true }));
    } else if (el.tagName === 'INPUT' && (el.type === 'range' || el.type === 'number')) {
      el.value = String(value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    } else if (el.tagName === 'SELECT') {
      el.value = String(value);
      el.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      el.value = value;
    }
  }
  function clickControl(id) {
    const el = document.getElementById(id);
    if (!el) { console.warn('[markov-bridge] click id non atopado:', id); return; }
    el.click();
  }
  window.addEventListener('message', (e) => {
    const msg = e.data;
    if (!msg || msg.type !== 'markov') return;
    try {
      if (msg.action === 'set' && msg.id !== undefined) {
        setControl(msg.id, msg.value);
      } else if (msg.action === 'click' && msg.id !== undefined) {
        clickControl(msg.id);
      } else if (msg.action === 'reset') { clickControl('btn-reset'); }
      else if (msg.action === 'next')   { clickControl('btn-next'); }
      else if (msg.action === 'auto')   { clickControl('btn-auto'); }
      else if (msg.action === 'export') { clickControl('btn-export-png'); }
      else if (msg.action === 'batch' && Array.isArray(msg.items)) {
        for (const it of msg.items) {
          if (it.action === 'set') setControl(it.id, it.value);
          else if (it.action === 'click') clickControl(it.id);
        }
      }
    } catch (err) {
      console.error('[markov-bridge] erro:', err, msg);
    }
  });
  // Sinaliza ao parent que o iframe está listo
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({type: 'markov-ready'}, '*');
  }
  console.log('[markov-bridge] listo');
})();

// Musician + Director. Misma vista, comportamento condicional.
(function() {
  const SID = window.MSID;
  const sel = document.getElementById('inst-select');
  const stage = document.getElementById('stage');
  const label = document.getElementById('label');
  const suffix = document.getElementById('suffix');
  const barInfo = document.getElementById('bar-info');
  const selectorPanel = document.getElementById('selector');
  let isDirector = false;
  let registered = false;
  let showBar = true;
  let directorList = [];
  let movement = 0;

  const socket = io('/musician', { auth: { sid: SID } });

  function applyDirectorVisibility() {
    if (!isDirector) return;
    if (movement === 1 || movement === 3) {
      stage.style.background = '#000';
      suffix.textContent = '';
      label.textContent = 'DIRECTOR';
    }
  }

  socket.on('catalog', data => {
    showBar = data.show_bar;
    sel.innerHTML = '';
    const counts = data.occupied_count || {};
    data.instruments.forEach(i => {
      const opt = document.createElement('option');
      opt.value = i.id;
      const n = counts[i.id] || 0;
      // Se xa hai N ocupando este instrumento, mostra o índice que lle tocaría a este novo (N+1).
      // Non se mostra o texto "(ocupado)"; só o sufixo numérico.
      opt.textContent = n > 0 ? `${i.label} - ${n + 1}` : i.label;
      sel.appendChild(opt);
    });
  });

  document.getElementById('confirm').addEventListener('click', () => {
    socket.emit('register', { sid: SID, instrument_id: sel.value });
  });

  socket.on('registered', data => {
    registered = true;
    isDirector = data.is_director;
    label.textContent = data.instrument_label;
    selectorPanel.style.display = 'none';
    stage.style.display = 'flex';
    // Limpa calquera estado visual previo (importante tras un reset global ou
    // tras desasignación -- pódese chegar aquí coa clase 'fin' pegada).
    stage.classList.remove('playing', 'flash', 'fin');
    stage.style.background = '';
    suffix.textContent = '';
    suffix.style.whiteSpace = '';
    suffix.style.fontSize = '';
    if (isDirector) {
      stage.classList.add('director');
      suffix.style.fontSize = '1.4rem';
      label.textContent = 'DIRECTOR';
    }
  });

  socket.on('state:restore', data => {
    if (data && data.instrument_label) {
      isDirector = data.is_director;
      label.textContent = data.instrument_label;
      selectorPanel.style.display = 'none';
      stage.style.display = 'flex';
      registered = true;
      if (data.silenced) {
        stage.classList.add('fin');
        suffix.textContent = 'FIN';
      }
    }
  });

  socket.on('musician:play', data => {
    if (data.color === '#000' || data.color === '#000000') {
      stage.style.background = '#000';
      stage.classList.remove('playing');
    } else {
      stage.style.background = data.color;
      stage.classList.add('playing');
    }
    if (data.flash) {
      stage.classList.remove('flash'); void stage.offsetWidth; stage.classList.add('flash');
    }
    suffix.textContent = data.label_suffix || (data.playing ? 'TOCA' : '');
    if (data.label_suffix === 'FIN') {
      stage.classList.add('fin');
    } else {
      // Calquera evento posterior "sae" do estado FIN -- non pegues clase para sempre
      stage.classList.remove('fin');
    }
  });

  socket.on('settings:update', data => {
    if (data.show_bar !== undefined) showBar = data.show_bar;
    if (!showBar && !isDirector) barInfo.textContent = '';
  });

  socket.on('midi:bar', data => {
    if (!registered) return;
    if (!showBar && !isDirector) return;
    barInfo.textContent = `C. ${data.bar} · T. ${data.beat}`;
    if (data.in_clickin) barInfo.textContent = `Claqueta ${data.bar}/8`;
  });

  socket.on('director:update', data => {
    if (!isDirector) return;
    if (movement === 1 || movement === 3) return;   // director non ve nada en M1/M3
    if (data.event === 'instrument_activated') {
      directorList.push({ inst: data.instrument, group: data.group, t: Date.now() });
      directorList = directorList.slice(-30);
      const lines = directorList.slice().reverse().map(x => x.inst).join('\n');
      suffix.style.whiteSpace = 'pre';
      suffix.style.fontSize = '0.95rem';
      suffix.textContent = lines;
      stage.classList.remove('flash'); void stage.offsetWidth; stage.classList.add('flash');
    } else if (data.event === 'group_started') {
      directorList = [];
      suffix.textContent = `>> GRUPO ${data.group}`;
    } else if (data.event === 'blackout') {
      directorList = [];
      suffix.textContent = 'BLACKOUT';
    } else if (data.event === 'loop_changed') {
      // Mostramos LOOP X moi grande + lista completa de instrumentos do loop
      // ordenada pola orde da orquesta (vela envía o servidor).
      const lines = (data.assignments || []).map(m => m.instrument + (m.action === 'change' ? ' →' : '')).join('\n');
      const fullList = (data.instruments || []).join('  ·  ');
      suffix.style.whiteSpace = 'pre';
      suffix.style.fontSize = '0.85rem';
      suffix.textContent = lines + (fullList ? `\n\n--- INSTRUMENTACIÓN ---\n${fullList}` : '');
      // "LOOP X" enorme arriba
      label.style.fontSize = '5rem';
      label.style.color = data.color;
      label.style.textShadow = `0 0 18px ${data.color}`;
      label.style.letterSpacing = '0.2em';
      label.textContent = `LOOP ${data.loop.replace('L','')}`;
      stage.style.background = '#000';
      stage.classList.remove('flash'); void stage.offsetWidth; stage.classList.add('flash');
    }
  });

  socket.on('movement:changed', d => {
    movement = d.movement || 0;
    applyDirectorVisibility();
  });

  socket.on('reset:all', (data) => {
    // Volve á pantalla de selección de instrumento. Limíase TODO.
    registered = false;
    isDirector = false;
    directorList = [];
    movement = 0;
    stage.style.display = 'none';
    stage.classList.remove('playing', 'flash', 'fin', 'director');
    stage.style.background = '';
    label.textContent = '—';
    label.style.fontSize = '';
    label.style.color = '';
    label.style.textShadow = '';
    label.style.letterSpacing = '';
    suffix.textContent = '';
    suffix.style.whiteSpace = '';
    suffix.style.fontSize = '';
    barInfo.textContent = '';
    selectorPanel.style.display = '';
    if (data && data.clear_cookie) {
      // Borra cookie de sesión para forzar enquisa nova ao recargar
      document.cookie = 'monterrei_sid=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    }
  });
})();

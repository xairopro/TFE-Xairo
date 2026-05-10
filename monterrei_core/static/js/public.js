(function() {
  const SID = window.MSID;
  const socket = io('/public', { auth: { sid: SID } });
  const voting = document.getElementById('voting');
  const grid = document.getElementById('voting-grid');
  const timer = document.getElementById('timer');
  const idle = document.getElementById('idle');
  const shutdown = document.getElementById('shutdown');
  const shutdownBtn = document.getElementById('shutdown-btn');
  const cooldownEl = document.getElementById('shutdown-cooldown');
  const lastSilenced = document.getElementById('last-silenced');
  let endsAt = 0;
  let mySelected = null;
  let inQueue = false;  // true cando o usuario está en cola de apagado

  function showVoting(choices, colors) {
    voting.style.display = '';
    idle.style.display = 'none';
    shutdown.style.display = 'none';
    grid.innerHTML = '';
    choices.forEach(c => {
      const b = document.createElement('button');
      b.className = 'vote-btn'; b.dataset.loop = c;
      b.textContent = c;
      b.style.color = colors[c] || '#fff';
      b.addEventListener('click', () => {
        socket.emit('vote', { sid: SID, loop_id: c });
        document.querySelectorAll('.vote-btn').forEach(x => x.classList.remove('selected'));
        b.classList.add('selected');
        mySelected = c;
      });
      grid.appendChild(b);
    });
  }

  function showShutdown() {
    voting.style.display = 'none';
    idle.style.display = 'none';
    shutdown.style.display = 'flex';
  }

  function showIdle() {
    voting.style.display = 'none';
    shutdown.style.display = 'none';
    idle.style.display = '';
  }

  function showWinner(loop, color) {
    voting.style.display = 'none';
    shutdown.style.display = 'none';
    idle.style.display = '';
    if (!loop) return;
    idle.innerHTML = `
      <div style="font-size:0.8rem; color:#aaa; letter-spacing:0.2em; margin-bottom:0.6rem;">SAIU O LOOP</div>
      <div style="font-size:5rem; font-family:var(--mono); color:${color || '#fff'};
                  text-shadow:0 0 24px ${color || '#fff'}; letter-spacing:0.1em;">${loop}</div>
      <div style="margin-top:1.2rem; color:#888; font-size:0.85rem;">Agarda á seguinte quenda...</div>`;
    setTimeout(() => {
      idle.innerHTML = 'Agarda á seguinte quenda...';
    }, 6000);
  }

  shutdownBtn.addEventListener('click', () => {
    if (shutdownBtn.disabled) return;
    socket.emit('shutdown_click', { sid: SID });
    shutdownBtn.disabled = true;
    shutdownBtn.classList.add('pressed');
    cooldownEl.textContent = '...';
  });

  setInterval(() => {
    if (endsAt > 0) {
      const remaining = Math.max(0, endsAt - Date.now()/1000);
      const m = Math.floor(remaining/60), s = Math.floor(remaining%60);
      timer.textContent = `${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
    }
  }, 100);

  socket.on('m4:voting_open', d => { endsAt = d.ends_at; showVoting(d.choices, d.colors); });
  socket.on('m4:voting_close', d => {
    endsAt = 0;
    // Mostra durante uns segundos qué loop saíu ganándo
    showWinner(d.winner, d.color);
  });
  socket.on('m4:shutdown_mode', _d => { showShutdown(); });
  socket.on('public:update', d => {
    if (d.silenced) {
      lastSilenced.innerHTML = `<span class="who">Silenciaches a</span>${d.silenced}`;
    }
  });
  // Notificación a TODO o público cada vez que se apaga un instrumento
  socket.on('public:silenced', d => {
    if (!d || !d.instrument) return;
    lastSilenced.innerHTML = `<span class="who">Apagouse</span>${d.instrument}`;
    // Auto-clear atópase tras 4s para non sobrepoxer mensaxes
    clearTimeout(window.__silTimer);
    window.__silTimer = setTimeout(() => { lastSilenced.innerHTML = ''; }, 4000);
  });
  socket.on('vote_ack', _d => { /* visual feedback already applied */ });

  // Resposta ao pedido de apagado (inmediato ou en cola).
  socket.on('shutdown_ack', d => {
    const status = d && d.status;
    if (status === 'executed') {
      inQueue = false;
      cooldownEl.textContent = d.instrument ? `✓ ${d.instrument}` : '';
      setTimeout(() => {
        shutdownBtn.disabled = false;
        shutdownBtn.classList.remove('pressed');
        cooldownEl.textContent = '';
      }, 2000);
    } else if (status === 'queued') {
      inQueue = true;
      cooldownEl.textContent = `EN COLA #${d.position}`;
    } else if (status === 'already_queued') {
      inQueue = true;
      cooldownEl.textContent = `EN COLA #${d.position}`;
    } else {
      // rejected ou formato legado
      inQueue = false;
      shutdownBtn.disabled = false;
      shutdownBtn.classList.remove('pressed');
      cooldownEl.textContent = '';
    }
  });

  // Notificación persoal: o apagado en cola executouse.
  socket.on('shutdown_executed', d => {
    inQueue = false;
    shutdownBtn.disabled = false;
    shutdownBtn.classList.remove('pressed');
    cooldownEl.textContent = '';
    if (d && d.instrument) {
      lastSilenced.innerHTML = `<span class="who">Apagaches a</span>${d.instrument}`;
      clearTimeout(window.__mysilTimer);
      window.__mysilTimer = setTimeout(() => { lastSilenced.innerHTML = ''; }, 4000);
    }
  });

  // Aviso fullscreen "Comeza votación!"
  const voteAnnounce = document.getElementById('vote-announce');
  socket.on('public:vote_announce_show', d => {
    if (d && d.text && voteAnnounce) voteAnnounce.textContent = d.text;
    if (voteAnnounce) voteAnnounce.style.display = 'flex';
  });
  socket.on('public:vote_announce_hide', () => {
    if (voteAnnounce) voteAnnounce.style.display = 'none';
  });

  socket.on('state:restore', d => {
    if (d.shutdown_mode) showShutdown();
    else if (d.voting_open) showVoting(d.voting_choices || [], {});
    else showIdle();
  });

  socket.on('reset:all', (data) => {
    endsAt = 0;
    inQueue = false;
    mySelected = null;
    cooldownEl.textContent = '';
    shutdownBtn.disabled = false;
    shutdownBtn.classList.remove('pressed');
    lastSilenced.textContent = '';
    idle.innerHTML = 'Agarda á seguinte quenda...';
    showIdle();
    if (data && data.clear_cookie) {
      document.cookie = 'monterrei_sid=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    }
  });

  socket.on('reset:soft', () => {
    endsAt = 0;
    inQueue = false;
    mySelected = null;
    cooldownEl.textContent = '';
    shutdownBtn.disabled = false;
    shutdownBtn.classList.remove('pressed');
    lastSilenced.textContent = '';
    idle.innerHTML = 'Agarda á seguinte quenda...';
    showIdle();
  });

  // Heartbeat: detección de conexión 'colgada'
  let lastBeat = Date.now();
  socket.on('heartbeat', () => { lastBeat = Date.now(); });
  setInterval(() => {
    if (!socket.connected) return;
    if (Date.now() - lastBeat > 25000) {
      try { socket.disconnect(); socket.connect(); } catch (e) {}
      lastBeat = Date.now();
    }
  }, 3000);
})();

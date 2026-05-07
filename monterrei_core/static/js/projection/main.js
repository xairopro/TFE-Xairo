// Router de eventos Socket.IO para a vista de proxección.
(function() {
  const socket = io('/projection', {
    reconnection: true,
    reconnectionDelay: 500,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: Infinity,
  });
  const m1img = document.getElementById('m1-img');           // legacy (oculto)
  const m1vid = document.getElementById('m1-video');
  const previaImg = document.getElementById('previa-img');
  const m3frame = document.getElementById('m3-frame');
  const m4overlay = document.getElementById('m4-overlay');
  const loopName = document.getElementById('loop-name');
  const loopSubtitle = document.getElementById('loop-subtitle');
  const loopInstr = document.getElementById('loop-instruments');
  const feed = document.getElementById('shutdown-feed');
  const shutdownStack = document.getElementById('shutdown-stack');
  const qrOverlay = document.getElementById('qr-overlay');
  const qrBox = document.getElementById('qr-box');
  const qrSsid = document.getElementById('qr-ssid');
  const qrPass = document.getElementById('qr-pass');
  const qrFooter = document.getElementById('qr-footer');
  const qrUrlLabel = document.getElementById('qr-url-label');
  const clientsOverlay = document.getElementById('clients-overlay');
  const coMCount = document.getElementById('co-mcount');
  const coPCount = document.getElementById('co-pcount');
  const coStamp = document.getElementById('co-stamp');
  const votingOverlay = document.getElementById('voting-overlay');
  const votingTimer = document.getElementById('voting-timer');
  const votingCurrent = document.getElementById('voting-current');
  const votingCurrentName = document.getElementById('voting-current-name');
  const votingCurrentSub = document.getElementById('voting-current-sub');
  const votingPastLab = document.getElementById('voting-past-lab');
  const votingPastList = document.getElementById('voting-past-list');
  const voteAnnounceOverlay = document.getElementById('vote-announce-overlay');
  const voteAnnounceText = document.getElementById('vote-announce-text');
  const shutdownAnnounce = document.getElementById('shutdown-announce');
  const shutdownAnnounceText = document.getElementById('shutdown-announce-text');
  const aliveCounter = document.getElementById('alive-counter');
  const aliveCounterNum = document.getElementById('alive-counter-num');
  let votingEndsAt = 0;

  function hideStage() {
    m1img.style.display = 'none';
    m1vid.style.display = 'none';
    previaImg.style.display = 'none';
    m3frame.style.display = 'none';
    m4overlay.style.display = 'none';
    if (window.LorenzView) window.LorenzView.hide();
  }

  // -------- M1 (vídeo) --------
  socket.on('m1:video', d => {
    hideStage();
    if (d.action === 'play') {
      m1vid.src = d.src;
      m1vid.style.display = 'block';
      m1vid.play().catch(()=>{});
    } else {
      m1vid.pause();
    }
  });

  // -------- Previa (fotos + QR) --------
  socket.on('previa:slideshow', d => {
    hideStage();
    if (d && d.src) { previaImg.src = d.src; previaImg.style.display = 'block'; }
  });
  socket.on('previa:qr_show', d => {
    qrSsid.textContent = d.wifi_ssid || 'Monterrei';
    qrPass.textContent = d.wifi_pass || 'foliada7';
    qrFooter.textContent = d.footer || 'xairo.gal';
    qrUrlLabel.textContent = d.url || '';
    qrBox.innerHTML = d.svg || `<div style="padding:2rem; color:#000; font-family:monospace;">${d.url || ''}</div>`;
    qrOverlay.style.display = 'flex';
  });
  socket.on('previa:qr_hide', () => { qrOverlay.style.display = 'none'; });

  // -------- M2 (Lorenz) --------
  socket.on('m2:group_started', () => { hideStage(); if (window.LorenzView) window.LorenzView.show(); });
  socket.on('m2:tick', d => { if (window.LorenzView) window.LorenzView.onTick(d.px, d.py, d.active); });
  socket.on('m2:activated', () => { /* visual handled in onTick */ });
  socket.on('m2:blackout', () => {
    if (window.LorenzView) { window.LorenzView.blackout(); window.LorenzView.hide(); }
  });

  // -------- M3 (Markov) --------
  socket.on('m3:trigger', d => {
    if (d.action === 'start') { hideStage(); m3frame.style.display = 'block'; }
    else if (d.action === 'stop') { hideStage(); }
    else if (d.action === 'control' && m3frame.contentWindow) {
      m3frame.contentWindow.postMessage(Object.assign({type: 'markov'}, d.params || {}), '*');
    }
  });

  // -------- M4 --------
  socket.on('m4:loop_assigned', d => {
    hideStage();
    m4overlay.style.display = 'flex';
    loopName.textContent = `LOOP ${d.loop.replace('L','')}`;
    loopName.style.color = d.color;
    loopName.style.textShadow = `0 0 24px ${d.color}`;
    loopSubtitle.textContent = d.subtitle || '';
    loopSubtitle.style.color = d.color;
    loopSubtitle.style.textShadow = `0 0 14px ${d.color}`;
    loopInstr.textContent = d.instruments.join(' · ');
    // NON mostrar a banda (LorenzView) en M4: o fondo quédase negro.
  });
  socket.on('m4:shutdown_mode', () => {
    // Fondo totalmente negro: agocha o nome do loop e a banda.
    m4overlay.style.display = 'none';
    loopName.textContent = '—';
    loopSubtitle.textContent = '';
    loopInstr.textContent = '';
    if (window.LorenzView) window.LorenzView.hide();
    feed.style.display = '';
    votingOverlay.style.display = 'none';
    votingEndsAt = 0;
    aliveCounter.style.display = 'block';
  });
  socket.on('m4:musician_off', d => {
    const el = document.createElement('div');
    el.textContent = `${d.instrument} (${d.ip}) logged off`;
    feed.prepend(el);
    while (feed.children.length > 12) feed.removeChild(feed.lastChild);
  });
  // Stack: cada apagado xera o seu propio elemento, vive ~5s, nón se sobrescribe
  // co seguinte. Posición aleatoria entre 8 cantos/medios.
  const SHUT_SLOTS = [
    {top: '6vh',  left: '4vw',  align: 'flex-start', text: 'left'},
    {top: '6vh',  right: '4vw', align: 'flex-end',   text: 'right'},
    {bottom: '8vh', left: '4vw',  align: 'flex-start', text: 'left'},
    {bottom: '8vh', right: '4vw', align: 'flex-end',   text: 'right'},
    {top: '6vh',  left: '32vw', align: 'center',     text: 'center'},
    {bottom: '8vh', left: '32vw', align: 'center',    text: 'center'},
    {top: '38vh', left: '4vw',  align: 'flex-start', text: 'left'},
    {top: '38vh', right: '4vw', align: 'flex-end',   text: 'right'},
  ];
  socket.on('m4:musician_off_text', d => {
    const dur = d.duration_ms || 5000;
    const item = document.createElement('div');
    item.className = 'shutdown-item';
    const lab = document.createElement('div');
    lab.className = 'label'; lab.textContent = '— Apagouse —';
    const nm = document.createElement('div');
    nm.className = 'name'; nm.textContent = d.instrument || '';
    item.appendChild(lab); item.appendChild(nm);
    const s = SHUT_SLOTS[Math.floor(Math.random() * SHUT_SLOTS.length)];
    if (s.top !== undefined)    item.style.top = s.top;
    if (s.bottom !== undefined) item.style.bottom = s.bottom;
    if (s.left !== undefined)   item.style.left = s.left;
    if (s.right !== undefined)  item.style.right = s.right;
    item.style.alignItems = s.align;
    item.style.textAlign = s.text;
    item.style.animationDuration = (dur / 1000) + 's';
    shutdownStack.appendChild(item);
    setTimeout(() => { try { shutdownStack.removeChild(item); } catch(e){} }, dur + 200);
  });

  // -------- Splash 5s "O público apaga a banda" --------
  socket.on('projection:shutdown_announce', d => {
    if (d && d.text) shutdownAnnounceText.textContent = d.text;
    shutdownAnnounce.classList.remove('show');
    void shutdownAnnounce.offsetWidth;
    const dur = (d && d.duration_ms) || 5000;
    shutdownAnnounce.style.animationDuration = (dur / 1000) + 's';
    shutdownAnnounce.classList.add('show');
    setTimeout(() => shutdownAnnounce.classList.remove('show'), dur + 60);
  });

  // -------- Contador de músicos vivos (visible durante M4 shutdown) --------
  socket.on('projection:musicians_alive', d => {
    if (d && typeof d.count === 'number') {
      aliveCounterNum.textContent = d.count;
    }
  });

  // -------- Overlay de conectados (só contadores xigantes) --------
  function renderClients(d) {
    coMCount.textContent = d.musician_count || 0;
    coPCount.textContent = d.public_count || 0;
    if (coStamp) {
      const t = new Date();
      coStamp.textContent = `${t.toTimeString().slice(0,8)}`;
    }
  }
  socket.on('projection:clients_show', d => { renderClients(d); clientsOverlay.style.display = 'flex'; });
  socket.on('projection:clients_hide', () => { clientsOverlay.style.display = 'none'; });

  // -------- Overlay de votación (texto para o público) --------
  socket.on('m4:voting_open', d => {
    votingEndsAt = (d && d.ends_at) || 0;
    // Asegurarse de que o nome do loop anterior NON queda en pantalla.
    m4overlay.style.display = 'none';
    loopName.textContent = '—';
    loopSubtitle.textContent = '';
    loopInstr.textContent = '';
    // Panel lateral co loop que está soando agora (se hai un).
    if (d && d.current_loop) {
      const c = d.current_color || 'var(--neon-cyan)';
      votingCurrentName.textContent = `LOOP ${String(d.current_loop).replace('L','')}`;
      votingCurrentName.style.color = c;
      votingCurrentName.style.textShadow = `0 0 18px ${c}`;
      votingCurrentSub.textContent = d.current_subtitle || '';
      votingCurrent.classList.remove('empty');
    } else {
      votingCurrent.classList.add('empty');
    }
    // Histórico de loops xa saídos en votacións previas.
    while (votingPastList.firstChild) votingPastList.removeChild(votingPastList.firstChild);
    const past = (d && d.past_loops) || [];
    if (past.length) {
      votingPastLab.style.display = '';
      votingCurrent.classList.remove('empty');
      past.forEach(p => {
        const row = document.createElement('div');
        row.className = 'past-item';
        const nm = document.createElement('span');
        nm.className = 'nm';
        nm.textContent = `LOOP ${String(p.loop).replace('L','')}`;
        nm.style.color = p.color || 'var(--neon-cyan)';
        row.appendChild(nm);
        if (p.subtitle) {
          const sb = document.createElement('span');
          sb.className = 'sb';
          sb.textContent = p.subtitle;
          row.appendChild(sb);
        }
        votingPastList.appendChild(row);
      });
    } else {
      votingPastLab.style.display = 'none';
    }
    votingOverlay.style.display = 'flex';
  });
  socket.on('m4:voting_close', () => {
    votingOverlay.style.display = 'none';
    votingCurrent.classList.add('empty');
    while (votingPastList.firstChild) votingPastList.removeChild(votingPastList.firstChild);
    votingPastLab.style.display = 'none';
    votingEndsAt = 0;
  });

  // -------- Aviso de votación ("Comeza votación!") --------
  socket.on('projection:vote_announce_show', d => {
    if (d && d.text) voteAnnounceText.textContent = d.text;
    voteAnnounceOverlay.style.display = 'flex';
  });
  socket.on('projection:vote_announce_hide', () => {
    voteAnnounceOverlay.style.display = 'none';
  });
  setInterval(() => {
    if (!votingEndsAt) return;
    const r = Math.max(0, votingEndsAt - Date.now()/1000);
    const m = Math.floor(r/60), s = Math.floor(r%60);
    votingTimer.textContent = `${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
  }, 250);

  // -------- Reset --------
  function clearShowState() {
    hideStage();
    if (window.LorenzView) window.LorenzView.blackout();
    feed.style.display = 'none';
    feed.innerHTML = '';
    qrOverlay.style.display = 'none';
    clientsOverlay.style.display = 'none';
    while (shutdownStack.firstChild) shutdownStack.removeChild(shutdownStack.firstChild);
    votingOverlay.style.display = 'none';
    votingCurrent.classList.add('empty');
    while (votingPastList.firstChild) votingPastList.removeChild(votingPastList.firstChild);
    votingPastLab.style.display = 'none';
    voteAnnounceOverlay.style.display = 'none';
    shutdownAnnounce.classList.remove('show');
    aliveCounter.style.display = 'none';
    loopName.textContent = '—';
    loopSubtitle.textContent = '';
    loopInstr.textContent = '';
    votingEndsAt = 0;
  }
  socket.on('reset:all', (data) => {
    clearShowState();
    if (data && data.clear_cookie) {
      document.cookie = 'monterrei_sid=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    }
  });
  socket.on('reset:soft', () => clearShowState());

  // -------- Heartbeat: detección de conexión 'colgada' --------
  let lastBeat = Date.now();
  socket.on('heartbeat', () => { lastBeat = Date.now(); });
  setInterval(() => {
    if (!socket.connected) return;
    if (Date.now() - lastBeat > 25000) {
      try { socket.disconnect(); socket.connect(); } catch (e) {}
      lastBeat = Date.now();
    }
  }, 5000);
})();

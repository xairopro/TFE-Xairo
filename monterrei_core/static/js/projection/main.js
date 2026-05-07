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
  const loopInstr = document.getElementById('loop-instruments');
  const feed = document.getElementById('shutdown-feed');
  const qrOverlay = document.getElementById('qr-overlay');
  const qrBox = document.getElementById('qr-box');
  const qrSsid = document.getElementById('qr-ssid');
  const qrPass = document.getElementById('qr-pass');
  const qrFooter = document.getElementById('qr-footer');
  const qrUrlLabel = document.getElementById('qr-url-label');
  const shutdownText = document.getElementById('shutdown-text');
  const shutdownTextName = document.getElementById('shutdown-text-name');
  const clientsOverlay = document.getElementById('clients-overlay');
  const coMusicians = document.getElementById('co-musicians');
  const coPublic = document.getElementById('co-public');
  const coMCount = document.getElementById('co-mcount');
  const coPCount = document.getElementById('co-pcount');
  const coStamp = document.getElementById('co-stamp');
  const votingOverlay = document.getElementById('voting-overlay');
  const votingTimer = document.getElementById('voting-timer');
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
    loopInstr.textContent = d.instruments.join(' · ');
    if (window.LorenzView) window.LorenzView.show();
  });
  socket.on('m4:shutdown_mode', () => { feed.style.display = ''; votingOverlay.style.display = 'none'; votingEndsAt = 0; });
  socket.on('m4:musician_off', d => {
    const el = document.createElement('div');
    el.textContent = `${d.instrument} (${d.ip}) logged off`;
    feed.prepend(el);
    while (feed.children.length > 12) feed.removeChild(feed.lastChild);
  });
  // Overlay grande con fade ~3s
  socket.on('m4:musician_off_text', d => {
    shutdownTextName.textContent = d.instrument || '';
    shutdownText.classList.remove('show');
    void shutdownText.offsetWidth;
    shutdownText.style.animationDuration = ((d.duration_ms || 3000) / 1000) + 's';
    shutdownText.classList.add('show');
    setTimeout(() => shutdownText.classList.remove('show'), (d.duration_ms || 3000) + 60);
  });

  // -------- Overlay de conectados --------
  function renderClients(d) {
    coMCount.textContent = d.musician_count || 0;
    coPCount.textContent = d.public_count || 0;
    if (coStamp) {
      const t = new Date();
      coStamp.textContent = `${t.toTimeString().slice(0,8)}`;
    }
    coMusicians.innerHTML = '';
    (d.musicians || []).forEach(m => {
      const div = document.createElement('div');
      div.className = 'ip' + (m.connected ? '' : ' off') + (m.is_director ? ' dir' : '') + (m.silenced ? ' fin' : '');
      div.title = m.label;
      div.textContent = m.ip || '—';
      coMusicians.appendChild(div);
    });
    coPublic.innerHTML = '';
    (d.public || []).forEach(p => {
      const div = document.createElement('div');
      div.className = 'ip' + (p.connected ? '' : ' off');
      div.textContent = p.ip || '—';
      coPublic.appendChild(div);
    });
  }
  socket.on('projection:clients_show', d => { renderClients(d); clientsOverlay.style.display = 'flex'; });
  socket.on('projection:clients_hide', () => { clientsOverlay.style.display = 'none'; });

  // -------- Overlay de votación (texto para o público) --------
  socket.on('m4:voting_open', d => {
    votingEndsAt = (d && d.ends_at) || 0;
    votingOverlay.style.display = 'flex';
  });
  socket.on('m4:voting_close', () => {
    votingOverlay.style.display = 'none';
    votingEndsAt = 0;
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
    shutdownText.classList.remove('show');
    votingOverlay.style.display = 'none';
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

// Inxección de POSITIONS desde Python (servidas como /static/js/projection/positions.js)
// e router de eventos de socket á vista correcta.
(function() {
  const socket = io('/projection');
  const m1img = document.getElementById('m1-img');
  const m1vid = document.getElementById('m1-video');
  const m3frame = document.getElementById('m3-frame');
  const m4overlay = document.getElementById('m4-overlay');
  const loopName = document.getElementById('loop-name');
  const loopInstr = document.getElementById('loop-instruments');
  const feed = document.getElementById('shutdown-feed');

  function hideAll() {
    m1img.style.display = 'none';
    m1vid.style.display = 'none';
    m3frame.style.display = 'none';
    m4overlay.style.display = 'none';
    if (window.LorenzView) window.LorenzView.hide();
  }

  socket.on('m1:slideshow', d => {
    hideAll();
    if (d.src) { m1img.src = d.src; m1img.style.display = 'block'; }
  });
  socket.on('m1:video', d => {
    hideAll();
    if (d.action === 'play') {
      m1vid.src = d.src;
      m1vid.style.display = 'block';
      m1vid.play().catch(()=>{});
    } else {
      m1vid.pause();
    }
  });

  socket.on('m2:group_started', d => {
    hideAll();
    if (window.LorenzView) window.LorenzView.show();
  });
  socket.on('m2:tick', d => {
    if (window.LorenzView) window.LorenzView.onTick(d.px, d.py, d.active);
  });
  socket.on('m2:activated', d => { /* visual handled in onTick */ });
  socket.on('m2:blackout', d => {
    if (window.LorenzView) { window.LorenzView.blackout(); window.LorenzView.hide(); }
  });

  socket.on('m3:trigger', d => {
    if (d.action === 'start') {
      hideAll();
      m3frame.style.display = 'block';
    } else if (d.action === 'stop') {
      hideAll();
    } else if (d.action === 'control' && m3frame.contentWindow) {
      // Reenviar params tal cal ao bridge interno do Markov
      m3frame.contentWindow.postMessage(Object.assign({type: 'markov'}, d.params || {}), '*');
    }
  });

  socket.on('m4:loop_assigned', d => {
    hideAll();
    m4overlay.style.display = 'flex';
    loopName.textContent = `LOOP ${d.loop.replace('L','')}`;
    loopName.style.color = d.color;
    loopName.style.textShadow = `0 0 24px ${d.color}`;
    loopInstr.textContent = d.instruments.join(' · ');
    if (window.LorenzView) window.LorenzView.show();
  });

  socket.on('m4:shutdown_mode', d => {
    feed.style.display = '';
  });
  socket.on('m4:musician_off', d => {
    const el = document.createElement('div');
    el.textContent = `${d.instrument} (${d.ip}) logged off`;
    feed.prepend(el);
    while (feed.children.length > 12) feed.removeChild(feed.lastChild);
  });

  socket.on('reset:all', (data) => {
    hideAll();
    if (window.LorenzView) window.LorenzView.blackout();
    feed.style.display = 'none';
    feed.innerHTML = '';
    if (data && data.clear_cookie) {
      document.cookie = 'monterrei_sid=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    }
  });
})();

(function() {
  const socket = io('/admin');
  window.socket = socket;
  let previas = []; let imgIdx = 0;

  window.cmd = (c, args) => socket.emit('admin:cmd', { cmd: c, args: args || {} });
  window.openVoting = () => cmd('m4_open_voting', { seconds: parseInt(document.getElementById('vote-secs').value) });
  window.globalReset = () => {
    if (!confirm('Resetear TODOS os músicos e público?\nCadaquén volverá á pantalla inicial.')) return;
    cmd('global_reset');
  };
  window.prevImg = () => { if (!previas.length) return; imgIdx = (imgIdx - 1 + previas.length) % previas.length; cmd('m1_image', {index: imgIdx}); updateCounter(); };
  window.nextImg = () => { if (!previas.length) return; imgIdx = (imgIdx + 1) % previas.length; cmd('m1_image', {index: imgIdx}); updateCounter(); };
  function updateCounter() { document.getElementById('img-counter').textContent = previas.length ? `${imgIdx+1}/${previas.length}` : '— (carpeta baleira)'; }

  // Markov bridge: todólo control vai polo backend, que reenvía ó iframe en /projection.
  window.mk    = (action, items) => cmd('m3_control', { action, items });
  window.mkSet = (id, value) => cmd('m3_control', { action: 'set', id, value });

  window.applyColor = () => {
    const hex = document.getElementById('color-pick').value;
    const r = parseInt(hex.slice(1,3), 16), g = parseInt(hex.slice(3,5), 16), b = parseInt(hex.slice(5,7), 16);
    cmd('color_apply', {
      r, g, b, w: 0,
      effect: document.getElementById('color-effect').value,
      speed: parseFloat(document.getElementById('color-speed').value),
    });
  };

  function setLed(id, ok) {
    const el = document.getElementById(id);
    el.classList.remove('on','warn','err');
    el.classList.add(ok ? 'on' : 'err');
  }

  socket.on('state:snapshot', d => {
    setLed('led-midi', d.midi_connected);
    setLed('led-dmx', d.dmx_connected);
    document.getElementById('mus-count').textContent = d.musician_count;
    document.getElementById('pub-count').textContent = d.public_count;
    document.getElementById('show-bar').checked = d.show_bar;
    previas = d.previas || []; updateCounter();
  });
  socket.on('admin:update', d => {
    if (d.musician_count !== undefined) document.getElementById('mus-count').textContent = d.musician_count;
    if (d.public_count !== undefined) document.getElementById('pub-count').textContent = d.public_count;
    if (d.counts) renderVotes(d.counts);
  });
  socket.on('hw:status', d => {
    if (d.midi !== undefined) setLed('led-midi', d.midi);
    if (d.port) document.getElementById('midi-port').textContent = d.port;
  });
  socket.on('midi:bpm', d => { document.getElementById('bpm').textContent = d.bpm.toFixed(1); });
  socket.on('midi:bar', d => {
    document.getElementById('bar').textContent = d.in_clickin ? `clk${d.bar}` : `${d.bar}/T${d.beat} (P${d.pass})`;
  });
  socket.on('midi:status', d => { document.getElementById('midi-status').textContent = d.status; });

  function renderVotes(counts) {
    const tbody = document.querySelector('#votes-table tbody');
    tbody.innerHTML = '';
    Object.entries(counts).sort((a,b) => b[1]-a[1]).forEach(([k,v]) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${k}</td><td style="text-align:right;color:var(--neon-cyan);">${v}</td>`;
      tbody.appendChild(tr);
    });
  }

  // M2 progress (X/Y do grupo de Lorenz)
  socket.on('m2:progress', d => {
    const el = document.getElementById('m2-progress');
    if (!d.running || !d.group) { el.textContent = '—'; return; }
    el.textContent = `${d.active}/${d.total}  (${d.group})`;
  });

  // ----- Modal de clientes (IPs + desasignar) -----
  let clientsKind = 'musicians';
  window.openClients = (kind) => {
    clientsKind = kind || 'musicians';
    document.getElementById('clients-title').textContent =
      clientsKind === 'musicians' ? '>> CLIENTES MÚSICOS' : '>> CLIENTES PÚBLICO';
    document.querySelector('#clients-table tbody').innerHTML =
      '<tr><td colspan="4" class="dim">Cargando...</td></tr>';
    document.getElementById('clients-modal').style.display = '';
    cmd('list_clients');
  };
  window.closeClients = () => {
    document.getElementById('clients-modal').style.display = 'none';
  };
  window.unassignMusician = (sid, label) => {
    if (!confirm(`Desasignar instrumento de "${label}"?\nO seu teléfono volverá a pedir a enquisa.`)) return;
    cmd('unassign_musician', { sid });
    setTimeout(() => cmd('list_clients'), 250);
  };
  socket.on('admin:clients', d => {
    const tbody = document.querySelector('#clients-table tbody');
    tbody.innerHTML = '';
    const rows = clientsKind === 'musicians' ? (d.musicians || []) : (d.public || []);
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="dim">Sen clientes conectados.</td></tr>';
      return;
    }
    rows.forEach(c => {
      const tr = document.createElement('tr');
      if (clientsKind === 'musicians') {
        const status = [];
        if (c.is_director) status.push('director');
        if (c.silenced) status.push('FIN');
        if (!c.connected) status.push('off');
        tr.innerHTML = `
          <td>${c.instrument_label}</td>
          <td>${c.ip}</td>
          <td class="dim">${status.join(' · ') || 'ok'}</td>
          <td><button onclick="unassignMusician('${c.sid}', '${c.instrument_label.replace(/'/g,"\\'")}')">Desasignar</button></td>`;
      } else {
        tr.innerHTML = `
          <td class="dim">público</td>
          <td>${c.ip}</td>
          <td class="dim">${c.connected ? 'ok' : 'off'}</td>
          <td></td>`;
      }
      tbody.appendChild(tr);
    });
  });
})();

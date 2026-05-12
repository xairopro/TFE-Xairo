"use strict";
/**
 * Monterrei Simulator — lóxica do navegador
 * Comunícase co servidor local (localhost:3000) via Socket.IO.
 */

// ── Conexión co simulador local ───────────────────────────────────────────
const socket = io();

// ── Estado local ──────────────────────────────────────────────────────────
const musicians  = new Map();  // sid → { sid, state }
const publics    = new Map();  // sid → { sid, state }
let catalog      = [];
let autoVote     = true;
let autoShutdown = true;
let votingOpen   = false;
let votingData   = null;       // último payload de m4:voting_open
let shutdownMode = false;
let currentTab   = "musicians";
let logEntries   = [];
let logNewCount  = 0;
let modalSid     = null;

// ── Refs DOM ──────────────────────────────────────────────────────────────
const musicianGrid  = document.getElementById("musicians-grid");
const publicGrid    = document.getElementById("publics-grid");
const logBox        = document.getElementById("log-box");
const panelVote     = document.getElementById("panel-vote");
const panelShutdown = document.getElementById("panel-shutdown");
const loopButtons   = document.getElementById("loop-buttons");
const modal         = document.getElementById("modal");
const mScreen       = document.getElementById("m-screen");
const mGlow         = document.getElementById("m-glow");

// ── Utilidades ────────────────────────────────────────────────────────────
function sid8(sid) { return sid.slice(0, 8); }

function statusKey(state) {
  if (state.silenced)                       return "silenced";
  if (state.status === "registered") {
    return state.playing ? "active" : "registered";
  }
  return state.status;
}

function fmtTime(ts) {
  return new Date(ts).toTimeString().slice(0, 8);
}

// ── Renderizado de músicos ────────────────────────────────────────────────
function renderMusician(sid) {
  const m = musicians.get(sid);
  if (!m) return;
  const s = m.state;
  const color = s.color || "#445";

  let card = document.getElementById(`mc-${sid}`);
  if (!card) {
    card = document.createElement("div");
    card.className = "m-card";
    card.id = `mc-${sid}`;
    card.innerHTML = `
      <button class="btn-rm" data-rm="${sid}">✕</button>
      <div class="c-section" id="ms-${sid}"></div>
      <div class="c-title"   id="mt-${sid}"></div>
      <div><span class="pill" id="mp-${sid}"></span></div>
      <div class="c-loop"    id="ml-${sid}"></div>
      <div class="c-suffix"  id="mf-${sid}"></div>
      <div class="c-actions">
        <button class="btn-sm" id="mv-${sid}">Ver pantalla</button>
      </div>
    `;
    card.querySelector(`[data-rm="${sid}"]`).addEventListener("click", () => {
      socket.emit("remove_musician", { sid });
    });
    card.querySelector(`#mv-${sid}`).addEventListener("click", () => {
      openModal(sid);
    });
    musicianGrid.appendChild(card);
  }

  card.style.borderTopColor = color;
  card.classList.toggle("silenced", !!s.silenced);

  document.getElementById(`ms-${sid}`).textContent = s.section || "—";
  document.getElementById(`mt-${sid}`).textContent = s.instrument_label || sid8(sid);

  const pill = document.getElementById(`mp-${sid}`);
  const sk = statusKey(s);
  pill.textContent = sk;
  pill.className = `pill ${sk}`;

  document.getElementById(`ml-${sid}`).textContent =
    s.current_loop ? `LOOP ${s.current_loop}` : "";
  document.getElementById(`mf-${sid}`).textContent = s.suffix || "";

  // Actualiza modal se está aberto con este sid
  if (modalSid === sid) syncModal(sid);

  updateBadge("musicians");
}

function removeMusician(sid) {
  musicians.delete(sid);
  const card = document.getElementById(`mc-${sid}`);
  if (card) card.remove();
  if (modalSid === sid) closeModal();
  updateBadge("musicians");
}

// ── Renderizado de público ────────────────────────────────────────────────
function renderPublic(sid) {
  const p = publics.get(sid);
  if (!p) return;
  const s = p.state;

  let card = document.getElementById(`pc-${sid}`);
  if (!card) {
    card = document.createElement("div");
    card.className = "p-card";
    card.id = `pc-${sid}`;
    card.innerHTML = `
      <button class="btn-rm" data-rm="${sid}">✕</button>
      <div class="c-title">Público <small style="color:var(--muted)">${sid8(sid)}</small></div>
      <div><span class="pill" id="pp-${sid}"></span></div>
      <div id="pv-${sid}"></div>
      <div class="shutdowns-txt" id="pshut-${sid}"></div>
      <div class="c-actions">
        <button class="btn-sm" id="pvote-${sid}">Votar</button>
        <button class="btn-sm" id="pshutbtn-${sid}">Apagar</button>
      </div>
    `;
    card.querySelector(`[data-rm="${sid}"]`).addEventListener("click", () => {
      socket.emit("remove_public", { sid });
    });
    card.querySelector(`#pvote-${sid}`).addEventListener("click", () => {
      if (!votingData?.choices?.length) return;
      const choices = votingData.choices;
      const loop = choices[Math.floor(Math.random() * choices.length)];
      socket.emit("manual_vote", { sid, loop_id: loop });
    });
    card.querySelector(`#pshutbtn-${sid}`).addEventListener("click", () => {
      socket.emit("manual_shutdown", { sid });
    });
    publicGrid.appendChild(card);
  }

  const pill = document.getElementById(`pp-${sid}`);
  pill.textContent = s.status;
  pill.className   = `pill ${s.status === "connected" ? "connected" : s.status}`;

  const voteEl = document.getElementById(`pv-${sid}`);
  if (s.last_vote) {
    const color = votingData?.colors?.[s.last_vote] || "#666";
    voteEl.innerHTML = `<span class="vote-chip" style="background:${color}">${s.last_vote}</span>`;
  } else {
    voteEl.textContent = "";
  }

  const shutEl = document.getElementById(`pshut-${sid}`);
  shutEl.textContent = s.shutdown_clicks > 0
    ? `🔴 ${s.shutdown_clicks} apagados` : "";

  updateBadge("public");
}

function removePublic(sid) {
  publics.delete(sid);
  const card = document.getElementById(`pc-${sid}`);
  if (card) card.remove();
  updateBadge("public");
}

// ── Badges e contadores ───────────────────────────────────────────────────
function updateBadge(which) {
  if (which === "musicians") {
    const n = musicians.size;
    document.getElementById("badge-musicians").textContent = n;
    document.getElementById("musician-count").textContent  = `${n} conectados`;
  } else if (which === "public") {
    const n = publics.size;
    document.getElementById("badge-public").textContent = n;
    document.getElementById("public-count").textContent  = `${n} conectados`;
  }
}

// ── Logs ──────────────────────────────────────────────────────────────────
const filterMusician = document.getElementById("filter-musician");
const filterPublic   = document.getElementById("filter-public");

function addLog(entry) {
  logEntries.push(entry);
  if (logEntries.length > 1000) logEntries.shift();
  appendLogRow(entry);
  if (currentTab !== "logs") {
    logNewCount++;
    document.getElementById("badge-logs").textContent = logNewCount;
  }
}

function appendLogRow(entry) {
  if (entry.type === "musician" && !filterMusician.checked) return;
  if (entry.type === "public"   && !filterPublic.checked)   return;

  const div = document.createElement("div");
  div.className = "log-row";
  div.innerHTML =
    `<span class="log-ts">${fmtTime(entry.ts)}</span>` +
    `<span class="log-src ${entry.type}">${sid8(entry.source)}</span>` +
    `<span class="log-msg">${escHtml(entry.msg)}</span>`;
  logBox.appendChild(div);
  logBox.scrollTop = logBox.scrollHeight;
}

function rerenderLogs() {
  logBox.innerHTML = "";
  logEntries.forEach(appendLogRow);
  logBox.scrollTop = logBox.scrollHeight;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ── Panel de votación ─────────────────────────────────────────────────────
let countdownTimer = null;

function showVotingPanel(data) {
  panelVote.style.display = "block";
  document.getElementById("st-voting").className = "status-dot warn";

  // Botóns por loop
  loopButtons.innerHTML = "";
  (data.choices || []).forEach(lid => {
    const color = (data.colors || {})[lid] || "#888";
    const btn = document.createElement("button");
    btn.className = "loop-btn";
    btn.style.background = color;
    btn.textContent = lid;
    btn.addEventListener("click", () => socket.emit("vote_all", { loop_id: lid }));
    loopButtons.appendChild(btn);
  });

  // Countdown
  if (countdownTimer) clearInterval(countdownTimer);
  const endsAt = (data.ends_at || 0) * 1000;
  const tick = () => {
    const rem = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
    document.getElementById("vote-countdown").textContent = `${rem}s`;
    if (rem === 0) clearInterval(countdownTimer);
  };
  tick();
  countdownTimer = setInterval(tick, 250);
}

function hideVotingPanel() {
  panelVote.style.display = "none";
  document.getElementById("st-voting").className = "status-dot";
  if (countdownTimer) clearInterval(countdownTimer);
}

// ── Panel de apagado ──────────────────────────────────────────────────────
function showShutdownPanel(active) {
  panelShutdown.style.display = active ? "block" : "none";
  document.getElementById("st-shutdown").className =
    active ? "status-dot danger" : "status-dot";
}

// ── Modal pantalla de músico ──────────────────────────────────────────────
function openModal(sid) {
  modalSid = sid;
  syncModal(sid);
  modal.style.display = "flex";
}

function syncModal(sid) {
  const m = musicians.get(sid);
  if (!m) return;
  const s  = m.state;
  const sk = statusKey(s);
  const color = s.color || "#334";

  mScreen.style.borderColor = s.playing ? color : "var(--border)";
  mGlow.style.background    = color;
  mGlow.style.opacity       = s.playing ? "0.14" : "0.04";

  const instrEl = document.getElementById("m-instrument");
  instrEl.textContent  = s.instrument_label || sid8(sid);
  instrEl.style.color  = s.playing ? color : "#fff";

  document.getElementById("m-statustxt").textContent = sk.toUpperCase();

  const sufEl = document.getElementById("m-suffix");
  sufEl.textContent = s.suffix || (s.current_loop ? `LOOP ${s.current_loop}` : "");
  sufEl.style.color = color;
}

function closeModal() {
  modal.style.display = "none";
  modalSid = null;
}

document.getElementById("m-close").addEventListener("click", closeModal);
modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

// ── Abas ──────────────────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    currentTab = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`tab-${currentTab}`).classList.add("active");
    if (currentTab === "logs") {
      logNewCount = 0;
      document.getElementById("badge-logs").textContent = 0;
    }
  });
});

// ── Controis da sidebar ───────────────────────────────────────────────────
document.getElementById("btn-add-musicians").addEventListener("click", () => {
  const count = Math.max(1, parseInt(document.getElementById("musician-n").value) || 1);
  socket.emit("add_musicians", { count });
});

document.getElementById("btn-remove-all-musicians").addEventListener("click", () => {
  if (musicians.size === 0) return;
  if (confirm(`Desconectar os ${musicians.size} músicos virtuais?`))
    socket.emit("remove_all_musicians");
});

document.getElementById("btn-add-publics").addEventListener("click", () => {
  const count = Math.max(1, parseInt(document.getElementById("public-n").value) || 1);
  socket.emit("add_publics", { count });
});

document.getElementById("btn-remove-all-publics").addEventListener("click", () => {
  if (publics.size === 0) return;
  if (confirm(`Desconectar os ${publics.size} clientes de público virtuais?`))
    socket.emit("remove_all_publics");
});

document.getElementById("auto-vote").addEventListener("change", (e) => {
  autoVote = e.target.checked;
  socket.emit("set_auto_vote", { value: autoVote });
});

document.getElementById("auto-shutdown").addEventListener("change", (e) => {
  autoShutdown = e.target.checked;
  socket.emit("set_auto_shutdown", { value: autoShutdown });
});

document.getElementById("btn-vote-random").addEventListener("click", () => {
  socket.emit("vote_all", { loop_id: null });
});

document.getElementById("btn-shutdown-stagger").addEventListener("click", () => {
  socket.emit("manual_shutdown", {});
});

document.getElementById("btn-shutdown-force").addEventListener("click", () => {
  socket.emit("force_shutdown_all");
});

document.getElementById("btn-clear-logs").addEventListener("click", () => {
  logEntries = [];
  logBox.innerHTML = "";
  logNewCount = 0;
  document.getElementById("badge-logs").textContent = 0;
});

filterMusician.addEventListener("change", rerenderLogs);
filterPublic.addEventListener("change", rerenderLogs);

// ── Eventos Socket.IO (servidor simulador → navegador) ────────────────────

socket.on("connect", () => {
  document.getElementById("st-server").className = "status-dot on";
});

socket.on("disconnect", () => {
  document.getElementById("st-server").className = "status-dot";
});

socket.on("init", (data) => {
  catalog      = data.catalog || [];
  autoVote     = data.autoVote;
  autoShutdown = data.autoShutdown;
  votingOpen   = data.votingOpen;
  votingData   = data.votingData;
  shutdownMode = data.shutdownMode;

  document.getElementById("auto-vote").checked     = autoVote;
  document.getElementById("auto-shutdown").checked = autoShutdown;

  (data.musicians || []).forEach(({ sid, state }) => {
    musicians.set(sid, { sid, state });
    renderMusician(sid);
  });

  (data.publics || []).forEach(({ sid, state }) => {
    publics.set(sid, { sid, state });
    renderPublic(sid);
  });

  if (votingOpen && votingData) showVotingPanel(votingData);
  showShutdownPanel(shutdownMode);
});

socket.on("musician_added", ({ sid, state }) => {
  musicians.set(sid, { sid, state });
  renderMusician(sid);
});

socket.on("musician_update", ({ sid, state }) => {
  const m = musicians.get(sid);
  if (m) m.state = state;
  renderMusician(sid);
});

socket.on("musician_removed", ({ sid }) => removeMusician(sid));

socket.on("public_added", ({ sid, state }) => {
  publics.set(sid, { sid, state });
  renderPublic(sid);
});

socket.on("public_update", ({ sid, state }) => {
  const p = publics.get(sid);
  if (p) p.state = state;
  renderPublic(sid);
});

socket.on("public_removed", ({ sid }) => removePublic(sid));

socket.on("catalog", (data) => {
  catalog = data;
});

socket.on("voting_open", (data) => {
  votingOpen = true;
  votingData = data;
  showVotingPanel(data);
  // Refresca chips de voto en tarxetas de público
  for (const sid of publics.keys()) renderPublic(sid);
});

socket.on("voting_close", () => {
  votingOpen = false;
  hideVotingPanel();
});

socket.on("shutdown_mode", (data) => {
  shutdownMode = !!data.active;
  showShutdownPanel(shutdownMode);
});

socket.on("musician_off", (data) => {
  // Flash visual na tab de músicos
  const label = data.instrument_label || data.instrument_id || "—";
  // O log xa o manexou o servidor
  void label;
});

socket.on("midi_bpm", (data) => {
  const bpm = typeof data === "number" ? data : (data?.bpm ?? data);
  if (bpm) document.getElementById("bpm-badge").textContent = `${Math.round(bpm)} BPM`;
});

socket.on("log", (entry) => addLog(entry));

"use strict";
/**
 * Monterrei Simulator — servidor local
 * Corre en localhost:3000 e actúa como intermediario entre o navegador de
 * control e o servidor Monterrei real, creando clientes Socket.IO virtuais
 * tanto para músicos (/musician en porto 8000) como para o público (/public
 * en porto 8001).
 */

const express  = require("express");
const http     = require("http");
const { Server }   = require("socket.io");
const { io: ioClient } = require("socket.io-client");
const { v4: uuidv4 }   = require("uuid");
const path     = require("path");

// ── Servidores ────────────────────────────────────────────────────────────────
const app    = express();
const server = http.createServer(app);
const uiSrv  = new Server(server, { cors: { origin: "*" } });

app.use(express.static(path.join(__dirname, "public")));

const MUSICIAN_URL = "http://192.168.1.126:8000";
const PUBLIC_URL   = "http://192.168.1.126:8001";

// ── Estado compartido ─────────────────────────────────────────────────────────
let catalog      = [];       // instrumentos recibidos do servidor
let votingOpen   = false;
let votingData   = null;     // payload completo do último m4:voting_open
let shutdownMode = false;
let autoVote     = true;
let autoShutdown = true;

// Maps  cookie_sid → { sid, socket, state, ... }
const musicians = new Map();
const publics   = new Map();

// ── Helpers UI ────────────────────────────────────────────────────────────────
function broadcast(event, data) {
  uiSrv.emit(event, data);
}

function addLog(source, type, msg, extra = null) {
  broadcast("log", { ts: Date.now(), source, type, msg, extra });
}

// ── Músicos virtuais ──────────────────────────────────────────────────────────
function connectMusician(sid, instrIdx) {
  const socket = ioClient(`${MUSICIAN_URL}/musician`, {
    auth: { sid },
    reconnection: true,
    reconnectionDelay: 2000,
  });

  const m = {
    sid,
    socket,
    instrIdx,
    state: {
      status:           "connecting",
      instrument_id:    null,
      instrument_label: null,
      section:          null,
      color:            null,
      playing:          false,
      suffix:           null,
      current_loop:     null,
      silenced:         false,
      is_director:      false,
    },
  };
  musicians.set(sid, m);
  broadcast("musician_added", { sid, state: m.state });

  socket.on("connect", () => {
    m.state.status = "connected";
    addLog(sid, "musician", "Conectado ao servidor Monterrei");
    broadcast("musician_update", { sid, state: m.state });
  });

  socket.on("catalog", (data) => {
    // Garda catálogo global a primeira vez
    if (!catalog.length && data.instruments?.length) {
      catalog = data.instruments;
      broadcast("catalog", catalog);
    }
    // Escolle instrumento por índice cíclico (exclúe director)
    const available = (data.instruments || catalog).filter(i => i.id !== "director");
    if (!available.length) return;
    const instr = available[instrIdx % available.length];
    socket.emit("register", { sid, instrument_id: instr.id });
    addLog(sid, "musician", `Rexistrando como "${instr.label}"`);
  });

  socket.on("registered", (data) => {
    m.state.status           = "registered";
    m.state.instrument_id    = data.instrument_id;
    m.state.instrument_label = data.instrument_label;
    m.state.is_director      = data.is_director;
    // Sección desde catálogo (o id pode ter sufixo -2, -3, …)
    const baseId = (data.instrument_id || "").split("-")[0];
    const cat    = catalog.find(i => i.id === baseId);
    if (cat) m.state.section = cat.section;
    addLog(sid, "musician", `Rexistrado: ${data.instrument_label}`);
    broadcast("musician_update", { sid, state: m.state });
  });

  socket.on("musician:play", (data) => {
    if (data.playing !== undefined) m.state.playing = data.playing;
    if (data.color)                 m.state.color   = data.color;
    if (data.suffix !== undefined)  m.state.suffix  = data.suffix;
    addLog(sid, "musician",
      `play → playing=${data.playing} color=${data.color} suffix=${data.suffix}`);
    broadcast("musician_update", { sid, state: m.state });
  });

  socket.on("m4:loop_assigned", (data) => {
    m.state.current_loop = data.loop_id || data.loop || null;
    if (data.color)            m.state.color  = data.color;
    if (data.suffix !== undefined) m.state.suffix = data.suffix;
    addLog(sid, "musician", `Loop asignado: ${m.state.current_loop}`);
    broadcast("musician_update", { sid, state: m.state });
  });

  socket.on("m4:musician_off", (data) => {
    // Comproba se este músico é o afectado
    const isMe = data.sid === sid
      || data.instrument_id === m.state.instrument_id
      || data.instrument_id === (m.state.instrument_id || "").split("-")[0];
    if (isMe) {
      m.state.silenced = true;
      m.state.playing  = false;
      m.state.color    = "#333333";
      m.state.suffix   = "SILENCIADO";
      addLog(sid, "musician", "⚠ SILENCIADO polo público");
      broadcast("musician_update", { sid, state: m.state });
    }
    // Retransmite o evento globalmente para o UI
    broadcast("musician_off", data);
  });

  socket.on("m4:voting_open", (data) => {
    votingOpen = true;
    votingData = data;
    broadcast("voting_open", data);
    addLog(sid, "musician",
      `Votación aberta (round ${data.round}): ${(data.choices || []).join(", ")}`);
  });

  socket.on("m4:voting_close", (data) => {
    votingOpen = false;
    broadcast("voting_close", data);
    addLog(sid, "musician", "Votación pechada");
  });

  socket.on("m4:shutdown_mode", (data) => {
    shutdownMode = !!data.active;
    broadcast("shutdown_mode", data);
    addLog(sid, "musician", `Modo apagado: ${data.active}`);
  });

  socket.on("state:restore", (data) => {
    if (data.instrument_label) {
      m.state.status           = "registered";
      m.state.instrument_id    = data.instrument_id;
      m.state.instrument_label = data.instrument_label;
      m.state.is_director      = data.is_director;
      m.state.current_loop     = data.current_loop;
      m.state.silenced         = data.silenced;
    }
    addLog(sid, "musician", "State restore recibido");
    broadcast("musician_update", { sid, state: m.state });
  });

  socket.on("midi:bpm", (d) => broadcast("midi_bpm", d));
  socket.on("midi:bar", (d) => broadcast("midi_bar", d));

  socket.on("disconnect", (reason) => {
    m.state.status = "disconnected";
    addLog(sid, "musician", `Desconectado (${reason})`);
    broadcast("musician_update", { sid, state: m.state });
  });

  socket.on("connect_error", (err) => {
    m.state.status = "error";
    addLog(sid, "musician", `Error de conexión: ${err.message}`);
    broadcast("musician_update", { sid, state: m.state });
  });

  socket.on("error", (err) => {
    addLog(sid, "musician", `Error socket: ${JSON.stringify(err)}`);
  });

  return m;
}

function disconnectMusician(sid) {
  const m = musicians.get(sid);
  if (!m) return;
  m.socket.disconnect();
  musicians.delete(sid);
  broadcast("musician_removed", { sid });
}

// ── Público virtual ───────────────────────────────────────────────────────────
const shutdownTimers = new Map();

function connectPublic(sid) {
  const socket = ioClient(`${PUBLIC_URL}/public`, {
    auth: { sid },
    reconnection: true,
    reconnectionDelay: 2000,
  });

  const p = {
    sid,
    socket,
    state: {
      status:           "connecting",
      last_vote:        null,
      shutdown_clicks:  0,
    },
  };
  publics.set(sid, p);
  broadcast("public_added", { sid, state: p.state });

  socket.on("connect", () => {
    p.state.status = "connected";
    addLog(sid, "public", "Conectado ao servidor Monterrei");
    broadcast("public_update", { sid, state: p.state });
    // Se xa hai votación ou apagado activos, actúa
    if (votingOpen && autoVote)     doVote(sid);
    if (shutdownMode && autoShutdown) scheduleShutdown(sid);
  });

  socket.on("m4:voting_open", (data) => {
    votingOpen = true;
    votingData = data;
    broadcast("voting_open", data);
    if (autoVote) doVote(sid);
  });

  socket.on("m4:voting_close", (data) => {
    votingOpen = false;
    broadcast("voting_close", data);
  });

  socket.on("m4:shutdown_mode", (data) => {
    shutdownMode = !!data.active;
    broadcast("shutdown_mode", data);
    if (data.active && autoShutdown) scheduleShutdown(sid);
  });

  socket.on("vote_ack", (data) => {
    addLog(sid, "public", `Voto ACK: ${data.loop_id}  ok=${data.ok}`);
    broadcast("public_update", { sid, state: p.state });
  });

  socket.on("shutdown_ack", (data) => {
    addLog(sid, "public", `Shutdown ACK: ${JSON.stringify(data)}`);
    // Programa seguinte click se o modo continúa
    if (shutdownMode && autoShutdown) scheduleShutdown(sid);
  });

  socket.on("state:restore", (data) => {
    if (data.voting_open && autoVote)     doVote(sid);
    if (data.shutdown_mode && autoShutdown) scheduleShutdown(sid);
    addLog(sid, "public", "State restore recibido");
  });

  socket.on("disconnect", (reason) => {
    p.state.status = "disconnected";
    addLog(sid, "public", `Desconectado (${reason})`);
    broadcast("public_update", { sid, state: p.state });
  });

  socket.on("connect_error", (err) => {
    p.state.status = "error";
    addLog(sid, "public", `Error de conexión: ${err.message}`);
    broadcast("public_update", { sid, state: p.state });
  });

  return p;
}

function disconnectPublic(sid) {
  const p = publics.get(sid);
  if (!p) return;
  p.socket.disconnect();
  const t = shutdownTimers.get(sid);
  if (t) { clearTimeout(t); shutdownTimers.delete(sid); }
  publics.delete(sid);
  broadcast("public_removed", { sid });
}

function doVote(sid, loopId = null) {
  const p = publics.get(sid);
  if (!p || !votingOpen) return;
  const choices = votingData?.choices || [];
  if (!choices.length) return;
  const loop = loopId || choices[Math.floor(Math.random() * choices.length)];
  p.state.last_vote = loop;
  p.socket.emit("vote", { sid, loop_id: loop });
  addLog(sid, "public", `Votou: ${loop}`);
  broadcast("public_update", { sid, state: p.state });
}

function scheduleShutdown(sid) {
  if (shutdownTimers.has(sid)) return;       // evita duplicados
  const delay = 600 + Math.random() * 4000;  // 0.6 – 4.6 s de atraso aleatorio
  const t = setTimeout(() => {
    shutdownTimers.delete(sid);
    doShutdownClick(sid);
  }, delay);
  shutdownTimers.set(sid, t);
}

function doShutdownClick(sid) {
  const p = publics.get(sid);
  if (!p) return;
  if (!shutdownMode) return;
  p.state.shutdown_clicks++;
  p.socket.emit("shutdown_click", { sid });
  addLog(sid, "public", `Shutdown click #${p.state.shutdown_clicks}`);
  broadcast("public_update", { sid, state: p.state });
}

// ── API para o navegador de control ──────────────────────────────────────────
uiSrv.on("connection", (client) => {
  // Envía estado actual ao conectarse
  client.emit("init", {
    musicians:    [...musicians.entries()].map(([sid, m]) => ({ sid, state: m.state })),
    publics:      [...publics.entries()].map(([sid, p])   => ({ sid, state: p.state })),
    catalog,
    autoVote,
    autoShutdown,
    votingOpen,
    votingData,
    shutdownMode,
  });

  // ── Músicos ──
  client.on("add_musicians", ({ count }) => {
    const startIdx = musicians.size;
    for (let i = 0; i < count; i++) connectMusician(uuidv4(), startIdx + i);
  });

  client.on("remove_musician", ({ sid }) => disconnectMusician(sid));

  client.on("remove_all_musicians", () => {
    for (const sid of [...musicians.keys()]) disconnectMusician(sid);
  });

  // ── Público ──
  client.on("add_publics", ({ count }) => {
    for (let i = 0; i < count; i++) connectPublic(uuidv4());
  });

  client.on("remove_public", ({ sid }) => disconnectPublic(sid));

  client.on("remove_all_publics", () => {
    for (const sid of [...publics.keys()]) disconnectPublic(sid);
  });

  // ── Configuración ──
  client.on("set_auto_vote",     ({ value }) => { autoVote     = value; });
  client.on("set_auto_shutdown", ({ value }) => { autoShutdown = value; });

  // ── Votación manual ──
  client.on("manual_vote", ({ sid, loop_id }) => doVote(sid, loop_id || null));

  // Vota para todos con un loop concreto (ou aleatorio se loop_id é null)
  client.on("vote_all", ({ loop_id }) => {
    for (const sid of publics.keys()) doVote(sid, loop_id || null);
  });

  // ── Shutdown manual ──
  client.on("manual_shutdown", ({ sid }) => {
    if (sid) {
      doShutdownClick(sid);
    } else {
      // Todos con atraso aleatorio escalonado
      for (const s of publics.keys()) scheduleShutdown(s);
    }
  });

  client.on("force_shutdown_all", () => {
    for (const sid of publics.keys()) doShutdownClick(sid);
  });
});

// ── Arranque ──────────────────────────────────────────────────────────────────
server.listen(3000, () => {
  console.log("╔══════════════════════════════════════════════╗");
  console.log("║   MONTERREI SIMULATOR                        ║");
  console.log("║   http://localhost:3000                      ║");
  console.log("╠══════════════════════════════════════════════╣");
  console.log(`║   Músicos  →  ${MUSICIAN_URL}      ║`);
  console.log(`║   Público  →  ${PUBLIC_URL}         ║`);
  console.log("╚══════════════════════════════════════════════╝");
});

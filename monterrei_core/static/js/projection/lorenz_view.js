// Render do mapa da banda + traxectoria de Lorenz na proxección.
//
// Topografía: 4 semicírculos (S1..S4) ao redor do director, raios crecentes.
// Os instrumentos están dispostos sobre o arco de cada semicírculo.
// Mostramos os arcos como liñas tenues e os instrumentos como puntos cos seus
// nomes. Os instrumentos activos brillan en verde neón.
window.LorenzView = (function() {
  const canvas = document.getElementById('m2-canvas');
  const ctx = canvas.getContext('2d');
  const POSITIONS = window.BAND_POSITIONS || {};
  const SEMICIRCLES = window.BAND_SEMICIRCLES || {};
  const SEMI_RADIUS = window.BAND_SEMI_RADIUS || {};
  const LABELS = window.BAND_LABELS || {};
  const GROUPS = window.BAND_GROUPS || {};
  const GROUP_COLORS = window.BAND_GROUP_COLORS || {
    G1: '#2f7dff',
    G2: '#22c86f',
    G3: '#ff59b0',
  };
  let active = new Set();
  let trail = [];

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  // Mapeo coordenadas normalizadas -> pantalla.
  // O director está abaixo no centro; os semicírculos abren cara arriba.
  // x ∈ [-1,1] mapea a horizontal; y ∈ [0,1] mapea a vertical (cara arriba).
  function geom() {
    const cx = canvas.width / 2;
    const cy = canvas.height * 0.92;            // director case abaixo
    const r  = Math.min(canvas.width / 2.1, canvas.height * 0.85);
    return { cx, cy, r };
  }
  function toScreen(x, y) {
    const g = geom();
    return [g.cx + x * g.r, g.cy - y * g.r];
  }

  function drawArcs() {
    const g = geom();
    ctx.lineWidth = 1.5;
    Object.entries(SEMI_RADIUS).forEach(([sem, rNorm]) => {
      const rPx = rNorm * g.r;
      ctx.beginPath();
      // π (esq) -> 0 (der). En coordenadas canvas y crece cara abaixo, así que
      // un semicírculo "cara arriba" debúxase con startAngle=π, endAngle=2π.
      ctx.arc(g.cx, g.cy, rPx, Math.PI, 2 * Math.PI);
      ctx.strokeStyle = 'rgba(120,140,170,0.22)';
      ctx.stroke();
      // Etiqueta do semicírculo á esquerda
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.fillStyle = 'rgba(120,140,170,0.45)';
      ctx.textAlign = 'right';
      ctx.fillText(sem, g.cx - rPx - 6, g.cy - 4);
    });
    // Marca do director
    ctx.beginPath();
    ctx.arc(g.cx, g.cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,174,10,0.9)';
    ctx.fill();
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.fillStyle = 'rgba(255,174,10,0.7)';
    ctx.textAlign = 'center';
    ctx.fillText('DIRECTOR', g.cx, g.cy + 16);
  }

  function drawInstruments() {
    Object.entries(POSITIONS).forEach(([id, pos]) => {
      const [sx, sy] = toScreen(pos[0], pos[1]);
      const isActive = active.has(id);
      const group = GROUPS[id];
      const baseColor = GROUP_COLORS[group] || 'rgba(170,190,220,0.7)';
      ctx.beginPath();
      ctx.arc(sx, sy, isActive ? 11 : 6, 0, Math.PI * 2);
      if (isActive) {
        ctx.shadowBlur = 20; ctx.shadowColor = '#ff2a55';
        ctx.fillStyle = '#ff2a55';
      } else {
        ctx.fillStyle = baseColor;
        ctx.globalAlpha = 0.72;
      }
      ctx.fill(); ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
      ctx.font = isActive ? 'bold 11px JetBrains Mono, monospace'
                          : '10px JetBrains Mono, monospace';
      ctx.fillStyle = isActive ? '#fff' : 'rgba(180,200,220,0.55)';
      ctx.textAlign = 'center';
      const text = LABELS[id] || id;
      ctx.fillText(text, sx, sy - 12);
    });
  }

  function drawLegend() {
    const items = [
      ['G1', GROUP_COLORS.G1 || '#2f7dff'],
      ['G2', GROUP_COLORS.G2 || '#22c86f'],
      ['G3', GROUP_COLORS.G3 || '#ff59b0'],
      ['ACTIVO', '#ff2a55'],
    ];
    let x = 26;
    const y = 28;
    ctx.font = '11px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    items.forEach(([name, col]) => {
      ctx.beginPath();
      ctx.arc(x, y, 6, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();
      ctx.fillStyle = 'rgba(225,235,245,0.9)';
      ctx.fillText(name, x + 11, y + 4);
      x += 96;
    });
  }

  function drawTrail() {
    if (trail.length > 1) {
      ctx.beginPath();
      const [sx0, sy0] = toScreen(trail[0][0], trail[0][1]);
      ctx.moveTo(sx0, sy0);
      for (let i = 1; i < trail.length; i++) {
        const [sx, sy] = toScreen(trail[i][0], trail[i][1]);
        ctx.lineTo(sx, sy);
      }
      ctx.strokeStyle = 'rgba(255,174,10,0.6)';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    if (trail.length >= 2) {
      const [sx, sy] = toScreen(trail[trail.length - 1][0], trail[trail.length - 1][1]);
      const [px, py] = toScreen(trail[trail.length - 2][0], trail[trail.length - 2][1]);
      const ang = Math.atan2(sy - py, sx - px);
      ctx.save();
      ctx.translate(sx, sy); ctx.rotate(ang);
      ctx.beginPath();
      ctx.moveTo(0, 0); ctx.lineTo(-12, 5); ctx.lineTo(-12, -5); ctx.closePath();
      ctx.fillStyle = '#ffae0a'; ctx.fill();
      ctx.restore();
    }
  }

  function draw() {
    // Fade suave (efecto traza)
    ctx.fillStyle = 'rgba(0,0,0,0.18)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawArcs();
    drawInstruments();
    drawLegend();
    drawTrail();
    requestAnimationFrame(draw);
  }
  draw();

  return {
    show() { canvas.style.display = 'block'; },
    hide() { canvas.style.display = 'none'; },
    onTick(px, py, activeIds) {
      // px,py veñen normalizados a [-1,1] desde o motor de Lorenz.
      // Reescalamos py a [0,1] para que case dentro do mapa de semicírculos.
      const ny = (py + 1) / 2;          // [-1,1] -> [0,1]
      const nx = px;                     // x igual
      trail.push([nx, ny]);
      if (trail.length > 600) trail = trail.slice(-600);
      active = new Set(activeIds);
    },
    blackout() { trail = []; active = new Set(); },
  };
})();

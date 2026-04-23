// ── Escalas musicais ──
export const SCALES = {
    diatonic: {
        name: 'Diatónica (7 notas)',
        notes: ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si'],
        size: 7,
    },
    octatonic: {
        name: 'Octatónica (8 notas)',
        notes: ['Do', 'Re', 'Mib', 'Fa', 'Solb', 'Lab', 'La', 'Si'],
        size: 8,
    },
};

// ── Pesos de transición por defecto (movementos relativos en graos da escala) ──
export const DEFAULT_TRANSITIONS = {
    '-1': 30,
    '+1': 22,
    '0':  14,
    '-2': 9,
    '+6': 6,
    '+2': 5,
    '-5': 4,
    '+5': 2,
    '+3': 2,
    '-3': 2,
    '+4': 1,
    '-4': 1,
    '-6': 1,
    '+7': 1,
};

// Intervalos que se mostran nos sliders (os 8 principais)
export const SLIDER_INTERVALS = ['-1', '+1', '0', '-2', '+6', '+2', '-5', '+5'];

// ── Estilos de nodo dispoñibles ──
export const NODE_STYLES = {
    circle:   { name: 'Círculo Brillante' },
    ring:     { name: 'Anel Oco' },
    diamond:  { name: 'Diamante Neón' },
    hexagon:  { name: 'Hexágono' },
    star:     { name: 'Estrela' },
    solid:    { name: 'Punto Sólido (Sen Glow)' },
};

// ── Parámetros por defecto ──
export const DEFAULTS = {
    noisePercent: 15,
    ossiaOpenChance: 25,
    ossiaCloseChance: 30,
    autoPlayInterval: 800,
    canvasWidth: 1920,
    canvasHeight: 1080,
    nodeRadius: 14,
    stepSpacing: 130,
    pitchSpacing: 32,
    maxBranches: 4,
    startDegree: 0,
    nodeStyle: 'circle',
};

// ── Paleta de cores (hex para PixiJS) ──
export const COLORS = {
    background: 0x06061a,
    normalNode: 0x00ffcc,
    normalEdge: 0x00ffcc,
    noiseNode: 0xff2244,
    noiseEdge: 0xff2244,
    ossiaNode: 0xcc44ff,
    ossiaEdge: 0x00ccff,
    mergeEdge: 0x8888ff,
    gridLine: 0x151540,
    nodeCore: 0xffffff,
};

// ── Modos de visualización ──
export const VIZ_MODES = {
    interactive: { name: 'Xerador Interactivo' },
    machine:     { name: 'A Máquina Pensando' },
};

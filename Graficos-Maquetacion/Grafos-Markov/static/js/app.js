import * as PIXI from 'pixi.js';
import { GlowFilter, AdvancedBloomFilter } from 'pixi-filters';
import { SCALES, DEFAULT_TRANSITIONS, DEFAULTS, COLORS } from './config.js';
import { MarkovEngine } from './markov.js';
import { GraphRenderer } from './graph.js';
import { UIController } from './ui.js';

async function main() {
    // 1. Crear aplicación PixiJS
    const app = new PIXI.Application();
    await app.init({
        width: DEFAULTS.canvasWidth,
        height: DEFAULTS.canvasHeight,
        backgroundColor: COLORS.background,
        antialias: true,
        resolution: window.devicePixelRatio || 1,
        autoDensity: true,
        preserveDrawingBuffer: true,
    });

    // 2. Montar canvas no DOM
    document.getElementById('canvas-container').appendChild(app.canvas);

    // 3. Inicializar motor Markov
    const engine = new MarkovEngine({
        scale: SCALES.diatonic,
        transitions: DEFAULT_TRANSITIONS,
        noisePercent: DEFAULTS.noisePercent,
        ossiaOpenChance: DEFAULTS.ossiaOpenChance,
        ossiaCloseChance: DEFAULTS.ossiaCloseChance,
    });

    // 4. Inicializar renderer
    const renderer = new GraphRenderer(app, PIXI, GlowFilter, AdvancedBloomFilter);

    // 5. Crear nodo raíz co grao inicial
    const startDegreeSlider = document.getElementById('slider-start-y');
    const startDegree = startDegreeSlider ? parseInt(startDegreeSlider.value) : 0;
    const initResult = engine.initialize(startDegree);
    renderer.addNodes(initResult.newNodes);

    // 6. Inicializar controis
    const ui = new UIController(engine, renderer);

    // 7. Loop de animación
    app.ticker.add((delta) => {
        renderer.animate(delta);
    });

    console.log('Grafo Futurista de Markov — inicializado correctamente');
}

main().catch((err) => {
    console.error('Erro ao inicializar a aplicación:', err);
    document.body.innerHTML = `
        <div style="color: #ff4466; padding: 40px; font-family: monospace; background: #040414; height: 100vh;">
            <h1 style="color: #00ffcc;">Erro ao cargar</h1>
            <p style="margin-top: 20px;">${err.message}</p>
            <p style="margin-top: 10px; color: #888;">Verifica a consola do navegador para máis detalles.</p>
        </div>
    `;
});

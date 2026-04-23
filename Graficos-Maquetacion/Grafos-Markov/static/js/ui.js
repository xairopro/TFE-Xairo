import { SLIDER_INTERVALS, DEFAULTS, SCALES, DEFAULT_TRANSITIONS } from './config.js';

export class UIController {
    constructor(engine, renderer) {
        this.engine   = engine;
        this.renderer = renderer;
        this.autoPlayTimer = null;
        this.isPlaying     = false;
        // Contexto pendente para o modo "A Máquina Pensando" (delay node appearance)
        this._pendingStep  = null;

        this._bind();
        this._syncColorPickers();
    }

    _bind() {
        // ── Playback ──
        document.getElementById('btn-next').addEventListener('click', () => this.doStep());
        document.getElementById('btn-auto').addEventListener('click', () => this.toggleAutoPlay());
        document.getElementById('btn-reset').addEventListener('click', () => this.reset());

        // ── Exportar PNG ──
        document.getElementById('btn-export-png').addEventListener('click', () => {
            this.renderer.exportPNG();
        });

        // ── Zoom ──
        document.getElementById('btn-zoom-in').addEventListener('click', () => {
            this.renderer.zoomBy(1.25);
        });
        document.getElementById('btn-zoom-out').addEventListener('click', () => {
            this.renderer.zoomBy(1 / 1.25);
        });
        document.getElementById('btn-zoom-reset').addEventListener('click', () => {
            this.renderer.resetView();
        });

        // ── Velocidade ──
        this._bindSlider('slider-speed', (val) => {
            if (this.isPlaying) {
                clearInterval(this.autoPlayTimer);
                this.autoPlayTimer = setInterval(() => this.doStep(), val);
            }
        });

        // ── Ruído e Ossia ──
        this._bindSlider('slider-noise',       (val) => this.engine.setNoisePercent(val));
        this._bindSlider('slider-ossia-open',  (val) => this.engine.setOssiaOpenChance(val));
        this._bindSlider('slider-ossia-close', (val) => this.engine.setOssiaCloseChance(val));

        // ── Probabilidades de transición ──
        for (const interval of SLIDER_INTERVALS) {
            const el = document.getElementById(`slider-t-${interval}`);
            if (el) el.addEventListener('input', () => this._recalcTransitions());
        }

        // ── Escala ──
        document.getElementById('select-scale').addEventListener('change', (e) => {
            this.engine.setScaleSize(SCALES[e.target.value].size);
        });

        // ── Resolución ──
        document.getElementById('select-resolution').addEventListener('change', (e) => {
            const [w, h] = e.target.value.split('x').map(Number);
            this.renderer.resize(w, h);
        });

        // ── Estilo de nodo ──
        document.getElementById('select-node-style').addEventListener('change', (e) => {
            const style = e.target.value;
            this.renderer.setNodeStyle(style);
            const solidRow = document.getElementById('color-solid-row');
            if (solidRow) solidRow.style.display = style === 'solid' ? 'flex' : 'none';
        });

        // ── Color pickers: nodos ──
        this._bindColorPicker('color-normal', 'normal');
        this._bindColorPicker('color-noise',  'noise');
        this._bindColorPicker('color-ossia',  'ossia');
        document.getElementById('color-solid').addEventListener('input', (e) => {
            this.renderer.setSolidColor(e.target.value);
        });

        // ── Color pickers: arestas ──
        this._bindEdgeColorPicker('color-edge-normal', 'normal');
        this._bindEdgeColorPicker('color-edge-noise',  'noise');
        this._bindEdgeColorPicker('color-edge-ossia',  'ossia');
        this._bindEdgeColorPicker('color-edge-merge',  'merge');

        // ── Modo de visualización ──
        const vizSelect = document.getElementById('select-viz-mode');
        if (vizSelect) {
            vizSelect.addEventListener('change', (e) => {
                const mode = e.target.value;
                this.engine.setVizMode(mode);
                this._updateVizModeUI(mode);
                this.reset();
            });
        }

        // ── Altura inicial ──
        this._bindSlider('slider-start-y', () => { /* aplícase ao reiniciar */ });

        // ── Atallos de teclado ──
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
            if (e.code === 'Space')  { e.preventDefault(); this.doStep(); }
            if (e.code === 'KeyP')   this.toggleAutoPlay();
            if (e.code === 'KeyR')   this.reset();
            if (e.code === 'Equal' || e.code === 'NumpadAdd')      this.renderer.zoomBy(1.25);
            if (e.code === 'Minus'  || e.code === 'NumpadSubtract') this.renderer.zoomBy(1/1.25);
            if (e.code === 'Digit0' || e.code === 'Numpad0')        this.renderer.resetView();
        });

        // Inicializar visibilidade segundo modo actual
        this._updateVizModeUI(this.engine.vizMode || 'interactive');
    }

    // Mostrar/ocultar controis segundo o modo de visualización
    _updateVizModeUI(mode) {
        const interactiveControls = document.getElementById('interactive-controls');
        const concertHint = document.getElementById('concert-mode-hint');
        // Ambos modos amosan os controis interactivos completos
        if (interactiveControls) {
            interactiveControls.style.display = 'block';
        }
        if (concertHint) {
            concertHint.style.display = mode === 'machine' ? 'block' : 'none';
            const hintText = concertHint.querySelector('.hint');
            if (hintText && mode === 'machine') {
                hintText.textContent = 'As liñas candidatas aparecen antes de cada paso: a máquina delibera antes de actuar.';
            }
        }
    }

    // Sincronizar os color pickers co estado inicial do renderer
    _syncColorPickers() {
        ['normal', 'noise', 'ossia', 'solid'].forEach(type => {
            const el = document.getElementById(`color-${type}`);
            if (el) el.value = this.renderer.getColorCSS(type);
        });
        // Sincronizar pickers de arestas
        ['normal', 'noise', 'ossia', 'merge'].forEach(type => {
            const el = document.getElementById(`color-edge-${type}`);
            if (el) el.value = this.renderer.getColorCSS(`edge-${type}`);
        });
        const solidRow = document.getElementById('color-solid-row');
        if (solidRow) solidRow.style.display = 'none';
    }

    _bindColorPicker(id, type) {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('input', (e) => {
            this.renderer.setNodeColor(type, e.target.value);
        });
    }

    _bindEdgeColorPicker(id, type) {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('input', (e) => {
            this.renderer.setEdgeColor(type, e.target.value);
        });
    }

    _bindSlider(id, callback) {
        const slider = document.getElementById(id);
        const valEl  = document.getElementById(id + '-val');
        if (!slider) return;
        slider.addEventListener('input', () => {
            const val = parseFloat(slider.value);
            if (valEl) valEl.textContent = val;
            callback(val);
        });
    }

    _recalcTransitions() {
        const raw = {};
        let sum = 0;
        for (const interval of SLIDER_INTERVALS) {
            const el = document.getElementById(`slider-t-${interval}`);
            if (!el) continue;
            const val = parseFloat(el.value);
            raw[interval] = val;
            sum += val;
        }
        for (const interval of SLIDER_INTERVALS) {
            const labelEl = document.getElementById(`label-t-${interval}`);
            if (labelEl && sum > 0)
                labelEl.textContent = ((raw[interval] / sum) * 100).toFixed(1) + '%';
        }
        const full = { ...raw };
        for (const [k, v] of Object.entries(DEFAULT_TRANSITIONS))
            if (!(k in full)) full[k] = v;
        this.engine.setTransitions(full);
    }

    _getStartDegree() {
        const el = document.getElementById('slider-start-y');
        return el ? parseInt(el.value) : 0;
    }

    doStep() {
        // Se quedou un nodo pendente do paso anterior (modo machine), engadilo agora
        if (this._pendingStep) {
            clearTimeout(this._pendingStep.timeout);
            this.renderer.addNodes(this._pendingStep.nodes);
            this.renderer.addEdges(this._pendingStep.edges, this._pendingStep.nodesById);
            this._pendingStep = null;
        }

        const result = this.engine.tick();
        document.getElementById('step-counter').textContent = `PASO: ${result.step}`;

        // Modo B: "A Máquina Pensando" — thinking animation ANTES de aparecer o nodo
        if (this.engine.vizMode === 'machine' && result.thinkingPaths) {
            this.renderer.showThinkingPaths(result.thinkingPaths);
            // Capturar referencias antes do timeout para evitar colisión con snap do engine
            const nodesSnap    = result.newNodes;
            const edgesSnap    = result.newEdges;
            const byIdSnap     = this.engine.nodesById;
            const tid = setTimeout(() => {
                this.renderer.addNodes(nodesSnap);
                this.renderer.addEdges(edgesSnap, byIdSnap);
                this._pendingStep = null;
            }, 650);
            this._pendingStep = { nodes: nodesSnap, edges: edgesSnap, nodesById: byIdSnap, timeout: tid };
            return;
        }

        // Modo A e C: engadir nodos/arestas inmediatamente
        this.renderer.addNodes(result.newNodes);
        this.renderer.addEdges(result.newEdges, this.engine.nodesById);

        // Modo C: "O Multiverso Ossia" — disolución de ramas (array de eventos)
        if (result.ossiaEvents) {
            for (const ev of result.ossiaEvents) {
                if (ev.type === 'close') {
                    this.renderer.dissolveOssiaBranch(ev.branchId);
                }
            }
        }
    }

    toggleAutoPlay() {
        const btn = document.getElementById('btn-auto');
        if (this.isPlaying) {
            clearInterval(this.autoPlayTimer);
            this.isPlaying = false;
            btn.classList.remove('active');
            btn.textContent = 'Auto-Play';
        } else {
            const speed = parseFloat(document.getElementById('slider-speed').value);
            this.autoPlayTimer = setInterval(() => this.doStep(), speed);
            this.isPlaying = true;
            btn.classList.add('active');
            btn.textContent = 'Pausa';
        }
    }

    reset() {
        if (this.isPlaying) this.toggleAutoPlay();
        // Cancelar nodos pendentes do modo machine
        if (this._pendingStep) {
            clearTimeout(this._pendingStep.timeout);
            this._pendingStep = null;
        }
        const scaleKey = document.getElementById('select-scale').value;
        const result = this.engine.reset({
            scale:            SCALES[scaleKey],
            transitions:      DEFAULT_TRANSITIONS,
            noisePercent:     parseFloat(document.getElementById('slider-noise').value),
            ossiaOpenChance:  parseFloat(document.getElementById('slider-ossia-open').value),
            ossiaCloseChance: parseFloat(document.getElementById('slider-ossia-close').value),
        }, this._getStartDegree());

        // Preservar o modo de visualización despois do reset
        const vizSelect = document.getElementById('select-viz-mode');
        if (vizSelect) {
            this.engine.setVizMode(vizSelect.value);
        }

        this.renderer.clear();
        this.renderer.addNodes(result.newNodes);
        document.getElementById('step-counter').textContent = 'PASO: 0';
    }
}

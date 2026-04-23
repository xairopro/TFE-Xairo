import { COLORS, DEFAULTS } from './config.js';

// ── Utilidades de conversión de cor ──
function cssToHex(css) {
    return parseInt(css.replace('#', ''), 16);
}
function hexToCSS(hex) {
    return '#' + hex.toString(16).padStart(6, '0');
}

// ── Renderer do Grafo con PixiJS ──

export class GraphRenderer {
    constructor(pixiApp, PIXI, GlowFilter, AdvancedBloomFilter) {
        this.app = pixiApp;
        this.PIXI = PIXI;
        this.GlowFilter = GlowFilter;
        this.AdvancedBloomFilter = AdvancedBloomFilter;

        this.canvasW = DEFAULTS.canvasWidth;
        this.canvasH = DEFAULTS.canvasHeight;
        this.stepSpacing = DEFAULTS.stepSpacing;
        this.pitchSpacing = DEFAULTS.pitchSpacing;
        this.nodeRadius = DEFAULTS.nodeRadius;
        this.nodeStyle = DEFAULTS.nodeStyle;

        // Cores mutables en tempo real (copia de COLORS)
        this.nodeColors = {
            normalNode: COLORS.normalNode,
            normalEdge: COLORS.normalEdge,
            noiseNode:  COLORS.noiseNode,
            noiseEdge:  COLORS.noiseEdge,
            ossiaNode:  COLORS.ossiaNode,
            ossiaEdge:  COLORS.ossiaEdge,
            mergeEdge:  COLORS.mergeEdge,
        };

        // Cor do estilo Punto Sólido (sen glow)
        this.solidColor = COLORS.normalNode;

        this.nodeSprites = new Map();
        this.edgeGraphics = [];
        this.particles = [];

        // Cámara automática
        this.autoCameraX = 0;
        this.targetAutoCameraX = 0;
        // Offset manual de panning
        this.panOffsetX = 0;
        this.panOffsetY = 0;
        this.lastStep = 0;
        // Control manual: cando o usuario fai zoom/pan, desactiva o auto-scroll
        this._userHasControl = false;

        // Zoom
        this.zoomLevel = 1.0;

        // Estado do drag
        this._isPanning = false;
        this._panStartX = 0;
        this._panStartY = 0;
        this._panStartOffsetX = 0;
        this._panStartOffsetY = 0;

        // ── Thinking lines (Modo B) ──
        this._thinkingLines = [];

        // ── Ossia dissolution particles (Modo C) ──
        this._dissolvingBranches = new Map(); // branchId → { nodeIds, startTime }

        this._init();
    }

    _init() {
        this.worldContainer = new this.PIXI.Container();
        this.app.stage.addChild(this.worldContainer);

        this.gridLayer     = new this.PIXI.Container();
        this.edgeLayer     = new this.PIXI.Container();
        this.thinkingLayer = new this.PIXI.Container(); // Nova capa para liñas de pensamento
        this.nodeLayer     = new this.PIXI.Container();
        this.particleLayer = new this.PIXI.Container();

        this.worldContainer.addChild(this.gridLayer);
        this.worldContainer.addChild(this.edgeLayer);
        this.worldContainer.addChild(this.thinkingLayer);
        this.worldContainer.addChild(this.nodeLayer);
        this.worldContainer.addChild(this.particleLayer);

        // Bloom global (desactivado para estilo sólido)
        this.bloom = null;
        try {
            this.bloom = new this.AdvancedBloomFilter({
                threshold: 0.25,
                bloomScale: 1.0,
                brightness: 1.1,
                blur: 4,
                quality: 3,
            });
            this.app.stage.filters = [this.bloom];
        } catch (e) {
            console.warn('AdvancedBloomFilter non dispoñible:', e);
        }

        this._drawGrid();
        this._setupInteraction();
    }

    // ── Interacción: panning + zoom ──
    _setupInteraction() {
        const canvas = this.app.canvas;

        // ── DRAG (panning) ──
        canvas.addEventListener('pointerdown', (e) => {
            this._isPanning = true;
            this._panStartX = e.clientX;
            this._panStartY = e.clientY;
            this._panStartOffsetX = this.panOffsetX;
            this._panStartOffsetY = this.panOffsetY;
            canvas.style.cursor = 'grabbing';
        });

        canvas.addEventListener('pointermove', (e) => {
            if (!this._isPanning) return;
            const rect = canvas.getBoundingClientRect();
            const scaleX = this.canvasW / rect.width;
            const scaleY = this.canvasH / rect.height;
            this.panOffsetX = this._panStartOffsetX + (e.clientX - this._panStartX) * scaleX;
            this.panOffsetY = this._panStartOffsetY + (e.clientY - this._panStartY) * scaleY;
            this._userHasControl = true;
        });

        const endPan = () => {
            this._isPanning = false;
            canvas.style.cursor = 'grab';
        };
        canvas.addEventListener('pointerup', endPan);
        canvas.addEventListener('pointerleave', endPan);

        // ── WHEEL (zoom centrado no cursor) ──
        canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
            const oldZoom = this.zoomLevel;
            const newZoom = Math.max(0.1, Math.min(6.0, oldZoom * factor));

            const rect = canvas.getBoundingClientRect();
            const mx = (e.clientX - rect.left) * (this.canvasW / rect.width);
            const my = (e.clientY - rect.top)  * (this.canvasH / rect.height);

            const curCX = this.worldContainer.x;
            const curCY = this.worldContainer.y;
            const wx = (mx - curCX) / oldZoom;
            const wy = (my - curCY) / oldZoom;

            const newCX = mx - wx * newZoom;
            const newCY = my - wy * newZoom;

            this.zoomLevel  = newZoom;
            this.panOffsetX = newCX - this.autoCameraX;
            this.panOffsetY = newCY;
            this._userHasControl = true;
            this._updateZoomDisplay();
        }, { passive: false });

        canvas.style.cursor = 'grab';
    }

    _updateZoomDisplay() {
        const el = document.getElementById('zoom-display');
        if (el) el.textContent = Math.round(this.zoomLevel * 100) + '%';
    }

    // Restablecer vista: zoom 1 + sen offset + retomar auto-scroll
    resetView() {
        this.zoomLevel = 1.0;
        this.panOffsetX = 0;
        this.panOffsetY = 0;
        this._userHasControl = false;
        if (this.lastStep > 0) {
            const rightEdge = this.lastStep * this.stepSpacing + 150;
            this.targetAutoCameraX = -(rightEdge - this.canvasW * 0.7 + 200);
        } else {
            this.targetAutoCameraX = 0;
        }
        this.autoCameraX = this.targetAutoCameraX;
        this.worldContainer.scale.set(1);
        this.worldContainer.x = this.autoCameraX;
        this.worldContainer.y = 0;
        this._updateZoomDisplay();
    }

    // Zoom con botóns (centrado no canvas)
    zoomBy(factor) {
        const oldZoom = this.zoomLevel;
        const newZoom = Math.max(0.1, Math.min(6.0, oldZoom * factor));
        const cx = this.canvasW / 2;
        const cy = this.canvasH / 2;
        const curCX = this.worldContainer.x;
        const curCY = this.worldContainer.y;
        const wx = (cx - curCX) / oldZoom;
        const wy = (cy - curCY) / oldZoom;
        const newCX = cx - wx * newZoom;
        const newCY = cy - wy * newZoom;
        this.zoomLevel  = newZoom;
        this.panOffsetX = newCX - this.autoCameraX;
        this.panOffsetY = newCY;
        this._userHasControl = true;
        this._updateZoomDisplay();
    }

    _drawGrid() {
        const g = new this.PIXI.Graphics();
        const width  = 15000;
        const height = this.canvasH;
        const centerY = height / 2;

        for (let x = 100; x < width; x += this.stepSpacing) {
            g.moveTo(x, 0); g.lineTo(x, height);
        }
        for (let x = 100; x > -5000; x -= this.stepSpacing) {
            g.moveTo(x, 0); g.lineTo(x, height);
        }
        for (let i = -50; i <= 50; i++) {
            const y = centerY - i * this.pitchSpacing;
            g.moveTo(-5000, y); g.lineTo(width, y);
        }
        g.stroke({ width: 0.5, color: COLORS.gridLine, alpha: 0.25 });
        this.gridLayer.addChild(g);
    }

    _toPixel(step, scaleDegree) {
        return {
            x: step * this.stepSpacing + 150,
            y: (this.canvasH / 2) - (scaleDegree * this.pitchSpacing),
        };
    }

    _nodeColor(type) {
        switch (type) {
            case 'noise': return this.nodeColors.noiseNode;
            case 'ossia': return this.nodeColors.ossiaNode;
            default:      return this.nodeColors.normalNode;
        }
    }

    _edgeColor(type) {
        switch (type) {
            case 'noise': return this.nodeColors.noiseEdge;
            case 'ossia': return this.nodeColors.ossiaEdge;
            case 'merge': return this.nodeColors.mergeEdge;
            default:      return this.nodeColors.normalEdge;
        }
    }

    // ── Debuxar forma de nodo ──
    _drawNodeShape(graphics, radius, color, alpha, style) {
        switch (style) {
            case 'ring':
                graphics.circle(0, 0, radius);
                graphics.stroke({ width: 2.5, color, alpha });
                graphics.circle(0, 0, radius * 0.3);
                graphics.fill({ color, alpha: alpha * 0.8 });
                break;

            case 'diamond': {
                const r = radius * 1.1;
                graphics.moveTo(0, -r).lineTo(r, 0).lineTo(0, r).lineTo(-r, 0).closePath();
                graphics.fill({ color, alpha });
                break;
            }

            case 'hexagon': {
                const r = radius * 1.05;
                for (let i = 0; i < 6; i++) {
                    const a = (Math.PI / 3) * i - Math.PI / 6;
                    if (i === 0) graphics.moveTo(Math.cos(a) * r, Math.sin(a) * r);
                    else         graphics.lineTo(Math.cos(a) * r, Math.sin(a) * r);
                }
                graphics.closePath();
                graphics.fill({ color, alpha });
                break;
            }

            case 'star': {
                const op = radius * 1.2, ip = radius * 0.5;
                for (let i = 0; i < 10; i++) {
                    const a = (Math.PI / 5) * i - Math.PI / 2;
                    const r = i % 2 === 0 ? op : ip;
                    if (i === 0) graphics.moveTo(Math.cos(a) * r, Math.sin(a) * r);
                    else         graphics.lineTo(Math.cos(a) * r, Math.sin(a) * r);
                }
                graphics.closePath();
                graphics.fill({ color, alpha });
                break;
            }

            case 'solid':
                graphics.circle(0, 0, radius);
                graphics.fill({ color: this.solidColor, alpha: 1.0 });
                break;

            default: // 'circle'
                graphics.circle(0, 0, radius);
                graphics.fill({ color, alpha });
                break;
        }
    }

    // ── Engadir nodos ──
    addNodes(nodes) {
        const isSolid = this.nodeStyle === 'solid';

        for (const node of nodes) {
            const pos   = this._toPixel(node.step, node.scaleDegree);
            const color = isSolid ? this.solidColor : this._nodeColor(node.type);
            const style = this.nodeStyle;

            const container = new this.PIXI.Container();
            container.position.set(pos.x, pos.y);

            // Forma principal
            const outer = new this.PIXI.Graphics();
            this._drawNodeShape(outer, this.nodeRadius, color, 0.85, style);
            container.addChild(outer);

            // Núcleo brillante (non para anel nin sólido)
            const core = new this.PIXI.Graphics();
            if (style !== 'ring' && style !== 'solid') {
                core.circle(0, 0, this.nodeRadius * 0.3);
                core.fill({ color: COLORS.nodeCore, alpha: 0.65 });
            }
            container.addChild(core);

            // Anel exterior (só estilos con bordo)
            const ring = new this.PIXI.Graphics();
            if (style === 'circle' || style === 'ring') {
                ring.circle(0, 0, this.nodeRadius * 1.3);
                ring.stroke({ width: 1, color, alpha: 0.25 });
            }
            container.addChild(ring);

            // GlowFilter: NON para o estilo sólido
            let glowFilter = null;
            if (!isSolid) {
                try {
                    glowFilter = new this.GlowFilter({
                        distance: 18,
                        outerStrength: 3.5,
                        innerStrength: 0,
                        color,
                        quality: 0.3,
                    });
                    container.filters = [glowFilter];
                } catch (_) { /* sen glow se falla */ }
            }

            this.nodeLayer.addChild(container);
            this.nodeSprites.set(node.id, {
                container, outer, core, ring, glowFilter,
                color,
                nodeType: node.type,
                nodeStyle: style,
                createdAt: performance.now(),
                step: node.step,
                branchId: node.branchId,
            });

            this._spawnParticles(pos.x, pos.y, color, node.type === 'noise' ? 12 : 8);
            this.lastStep = Math.max(this.lastStep, node.step);
        }
    }

    // ── Cambiar estilo de nodo en tempo real ──
    setNodeStyle(style) {
        this.nodeStyle = style;
        const isSolid = style === 'solid';

        if (this.bloom) {
            this.app.stage.filters = isSolid ? [] : [this.bloom];
        }

        for (const [, info] of this.nodeSprites) {
            info.nodeStyle = style;
            const color = isSolid ? this.solidColor : this._nodeColor(info.nodeType);
            info.color = color;

            info.outer.clear();
            this._drawNodeShape(info.outer, this.nodeRadius, color, 0.85, style);

            info.core.clear();
            if (style !== 'ring' && style !== 'solid') {
                info.core.circle(0, 0, this.nodeRadius * 0.3);
                info.core.fill({ color: COLORS.nodeCore, alpha: 0.65 });
            }

            info.ring.clear();
            if (style === 'circle' || style === 'ring') {
                info.ring.circle(0, 0, this.nodeRadius * 1.3);
                info.ring.stroke({ width: 1, color, alpha: 0.25 });
            }

            if (isSolid) {
                if (info.glowFilter) {
                    info.container.filters = [];
                    info.glowFilter = null;
                }
            } else {
                if (!info.glowFilter) {
                    try {
                        info.glowFilter = new this.GlowFilter({
                            distance: 18, outerStrength: 3.5,
                            innerStrength: 0, color, quality: 0.3,
                        });
                        info.container.filters = [info.glowFilter];
                    } catch (_) { /* ignore */ }
                } else {
                    info.glowFilter.color = color;
                    info.container.filters = [info.glowFilter];
                }
            }
        }
    }

    // ── Cambiar cor dun tipo de nodo en tempo real ──
    setNodeColor(type, cssHex) {
        const hex = cssToHex(cssHex);
        if (type === 'normal') {
            this.nodeColors.normalNode = hex;
        } else if (type === 'noise') {
            this.nodeColors.noiseNode = hex;
        } else if (type === 'ossia') {
            this.nodeColors.ossiaNode = hex;
        }
        if (this.nodeStyle === 'solid') return;
        for (const [, info] of this.nodeSprites) {
            if (info.nodeType !== type) continue;
            info.color = hex;
            info.outer.clear();
            this._drawNodeShape(info.outer, this.nodeRadius, hex, 0.85, info.nodeStyle);
            info.ring.clear();
            if (info.nodeStyle === 'circle' || info.nodeStyle === 'ring') {
                info.ring.circle(0, 0, this.nodeRadius * 1.3);
                info.ring.stroke({ width: 1, color: hex, alpha: 0.25 });
            }
            if (info.glowFilter) info.glowFilter.color = hex;
        }
    }

    // ── Cambiar cor das arestas en tempo real ──
    setEdgeColor(type, cssHex) {
        const hex = cssToHex(cssHex);
        if (type === 'normal') {
            this.nodeColors.normalEdge = hex;
        } else if (type === 'noise') {
            this.nodeColors.noiseEdge = hex;
        } else if (type === 'ossia') {
            this.nodeColors.ossiaEdge = hex;
        } else if (type === 'merge') {
            this.nodeColors.mergeEdge = hex;
        }
        // As arestas non se redebujan en tempo real (só se aplica ás novas)
    }

    // ── Cambiar cor do estilo sólido ──
    setSolidColor(cssHex) {
        this.solidColor = cssToHex(cssHex);
        if (this.nodeStyle !== 'solid') return;
        for (const [, info] of this.nodeSprites) {
            info.color = this.solidColor;
            info.outer.clear();
            this._drawNodeShape(info.outer, this.nodeRadius, this.solidColor, 0.85, 'solid');
        }
    }

    // Devolver as cores actuais como CSS hex
    getColorCSS(type) {
        switch (type) {
            case 'normal': return hexToCSS(this.nodeColors.normalNode);
            case 'noise':  return hexToCSS(this.nodeColors.noiseNode);
            case 'ossia':  return hexToCSS(this.nodeColors.ossiaNode);
            case 'solid':  return hexToCSS(this.solidColor);
            case 'edge-normal': return hexToCSS(this.nodeColors.normalEdge);
            case 'edge-noise':  return hexToCSS(this.nodeColors.noiseEdge);
            case 'edge-ossia':  return hexToCSS(this.nodeColors.ossiaEdge);
            case 'edge-merge':  return hexToCSS(this.nodeColors.mergeEdge);
        }
        return '#ffffff';
    }

    // ── Engadir arestas ──
    addEdges(edges, nodesById) {
        for (const edge of edges) {
            const src = nodesById.get(edge.sourceId);
            const tgt = nodesById.get(edge.targetId);
            if (!src || !tgt) continue;

            const p1    = this._toPixel(src.step, src.scaleDegree);
            const p2    = this._toPixel(tgt.step, tgt.scaleDegree);
            const color = this._edgeColor(edge.type);
            const g     = new this.PIXI.Graphics();

            if      (edge.type === 'noise') this._drawGlitchLine(g, p1, p2, color);
            else if (edge.type === 'merge') this._drawDashedLine(g, p1, p2, color, 0.4);
            else if (edge.type === 'ossia') this._drawCurvedLine(g, p1, p2, color, 0.5, 1.5);
            else {
                g.moveTo(p1.x, p1.y).lineTo(p2.x, p2.y);
                g.stroke({ width: 2, color, alpha: 0.75 });
            }

            this.edgeLayer.addChild(g);
            this.edgeGraphics.push(g);
        }
    }

    _drawGlitchLine(g, p1, p2, color) {
        const segs = 10;
        const dx = (p2.x - p1.x) / segs, dy = (p2.y - p1.y) / segs, j = 8;
        g.moveTo(p1.x, p1.y);
        for (let i = 1; i < segs; i++)
            g.lineTo(p1.x + dx*i + (Math.random()-.5)*j, p1.y + dy*i + (Math.random()-.5)*j);
        g.lineTo(p2.x, p2.y);
        g.stroke({ width: 2.5, color, alpha: 0.9 });
        g.moveTo(p1.x, p1.y);
        for (let i = 1; i < segs; i++)
            g.lineTo(p1.x + dx*i + (Math.random()-.5)*j*.5, p1.y + dy*i + (Math.random()-.5)*j*.5);
        g.lineTo(p2.x, p2.y);
        g.stroke({ width: 1, color: 0xffaaaa, alpha: 0.5 });
    }

    _drawDashedLine(g, p1, p2, color, alpha) {
        const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
        const dL = 8, gL = 6;
        const steps = Math.floor(dist / (dL + gL));
        const dx = (p2.x - p1.x) / dist, dy = (p2.y - p1.y) / dist;
        for (let i = 0; i < steps; i++) {
            const s = i * (dL + gL);
            g.moveTo(p1.x + dx*s, p1.y + dy*s);
            g.lineTo(p1.x + dx*(s+dL), p1.y + dy*(s+dL));
        }
        g.stroke({ width: 1.5, color, alpha });
    }

    _drawCurvedLine(g, p1, p2, color, alpha, width) {
        const mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2;
        g.moveTo(p1.x, p1.y);
        g.quadraticCurveTo(mx, my - (p2.y - p1.y) * 0.3 - 15, p2.x, p2.y);
        g.stroke({ width, color, alpha });
    }

    // ── "Thinking lines" para Modo B ──
    showThinkingPaths(thinkingPaths) {
        // Limpar thinking lines anteriores
        this.clearThinkingLines();

        const now = performance.now();
        for (const path of thinkingPaths) {
            const srcInfo = this.nodeSprites.get(path.fromNodeId);
            if (!srcInfo) continue;
            const srcPos = { x: srcInfo.container.x, y: srcInfo.container.y };
            const tgtPos = this._toPixel(path.targetStep, path.targetDegree);

            const g = new this.PIXI.Graphics();
            g.moveTo(srcPos.x, srcPos.y);
            g.lineTo(tgtPos.x, tgtPos.y);

            if (path.isChosen) {
                // Liña elixida: xeometría opaca, visibilidade via container.alpha
                g.stroke({ width: 2.5, color: this.nodeColors.normalEdge, alpha: 1.0 });
            } else {
                // Liña descartada: xeometría opaca, visibilidade via container.alpha
                g.stroke({ width: 1.5, color: 0x4466aa, alpha: 1.0 });
            }
            g.alpha = 0; // Empezar invisible; animado via container.alpha

            this.thinkingLayer.addChild(g);
            this._thinkingLines.push({
                graphic: g,
                isChosen: path.isChosen,
                createdAt: now,
                fromPos: srcPos,
                toPos: tgtPos,
            });
        }
    }

    clearThinkingLines() {
        for (const tl of this._thinkingLines) {
            this.thinkingLayer.removeChild(tl.graphic);
            tl.graphic.destroy();
        }
        this._thinkingLines = [];
    }

    // ── Disolución de rama ossia (Modo C) ──
    dissolveOssiaBranch(branchId) {
        // Recoller todos os nodos e arestas desa rama para o efecto de partículas
        const nodeIds = [];
        for (const [id, info] of this.nodeSprites) {
            if (info.branchId === branchId) {
                nodeIds.push(id);
            }
        }

        if (nodeIds.length === 0) return;
        this._dissolvingBranches.set(branchId, {
            nodeIds,
            startTime: performance.now(),
            duration: 1200,
        });
    }

    // ── Partículas ──
    _spawnParticles(x, y, color, count) {
        for (let i = 0; i < count; i++) {
            const p = new this.PIXI.Graphics();
            p.circle(0, 0, 1.5 + Math.random() * 1.5);
            p.fill({ color, alpha: 1 });
            p.position.set(x, y);
            const angle = (Math.PI * 2 * i) / count + (Math.random() - .5) * .5;
            const speed = 50 + Math.random() * 40;
            p._vx = Math.cos(angle) * speed;
            p._vy = Math.sin(angle) * speed;
            p._life  = 1.0;
            p._decay = 0.015 + Math.random() * 0.01;
            this.particleLayer.addChild(p);
            this.particles.push(p);
        }
    }

    // Partículas de disolución ("cinsas dixitais")
    _spawnDissolutionParticles(x, y, color, count) {
        for (let i = 0; i < count; i++) {
            const p = new this.PIXI.Graphics();
            const size = 0.5 + Math.random() * 2.0;
            p.circle(0, 0, size);
            p.fill({ color, alpha: 0.8 });
            p.position.set(x, y);
            const angle = Math.random() * Math.PI * 2;
            const speed = 15 + Math.random() * 60;
            p._vx = Math.cos(angle) * speed;
            p._vy = Math.sin(angle) * speed - 10; // Lixeiramente cara arriba
            p._life  = 1.0;
            p._decay = 0.008 + Math.random() * 0.012;
            this.particleLayer.addChild(p);
            this.particles.push(p);
        }
    }

    // ── Animación por frame ──
    animate(ticker) {
        const now = performance.now();
        const dt  = (ticker.deltaTime || 1) / 60;

        // 1. Cámara automática
        if (!this._userHasControl) {
            const rightEdge = this.lastStep * this.stepSpacing + 150;
            const viewW     = this.canvasW / this.zoomLevel;
            const margin    = viewW * 0.3;
            if (rightEdge > viewW - margin + Math.abs(this.targetAutoCameraX)) {
                this.targetAutoCameraX = -(rightEdge - viewW + margin + 200);
            }
            this.autoCameraX += (this.targetAutoCameraX - this.autoCameraX) * 0.08;
        }

        // 2. Aplicar posición + escala ao contedor
        this.worldContainer.scale.set(this.zoomLevel);
        this.worldContainer.x = this.autoCameraX + this.panOffsetX;
        this.worldContainer.y = this.panOffsetY;

        // 3. Animación de nodos (pulso de nacemento + respiración ambiental)
        const isSolid = this.nodeStyle === 'solid';
        for (const [id, info] of this.nodeSprites) {
            const age = now - info.createdAt;
            if (age < 700) {
                const t = age / 700;
                info.container.scale.set(1.0 + 0.6 * Math.sin(t * Math.PI) * (1 - t));
                if (info.glowFilter) info.glowFilter.outerStrength = 3.5 + 5.0 * (1 - t);
            } else if (!isSolid) {
                info.container.scale.set(1.0 + 0.025 * Math.sin(now * 0.002 + id * 1.7));
                if (info.glowFilter)
                    info.glowFilter.outerStrength = 3.0 + 0.5 * Math.sin(now * 0.003 + id * 2.3);
            } else {
                info.container.scale.set(1.0);
            }
        }

        // 4. Animación das "thinking lines" (Modo B)
        for (let i = this._thinkingLines.length - 1; i >= 0; i--) {
            const tl = this._thinkingLines[i];
            const age = now - tl.createdAt;

            if (tl.isChosen) {
                // Fase 1 (0-300ms): aparecer tenue
                // Fase 2 (300-700ms): iluminarse con forza
                // Fase 3 (700-1500ms): permanecer completamente visible antes de limpar
                if (age < 300) {
                    tl.graphic.alpha = 0.35 * (age / 300);
                } else if (age < 700) {
                    const t2 = (age - 300) / 400;
                    // Só container.alpha controla visibilidade; xeometría alpha=1.0
                    tl.graphic.alpha = 0.35 + 0.65 * t2;
                    // Redibujar con máis grosor cada frame (ilumínase progresivamente)
                    tl.graphic.clear();
                    tl.graphic.moveTo(tl.fromPos.x, tl.fromPos.y);
                    tl.graphic.lineTo(tl.toPos.x, tl.toPos.y);
                    tl.graphic.stroke({
                        width: 2.5 + 2 * t2,
                        color: this.nodeColors.normalEdge,
                        alpha: 1.0,
                    });
                } else if (age > 1500) {
                    this.thinkingLayer.removeChild(tl.graphic);
                    tl.graphic.destroy();
                    this._thinkingLines.splice(i, 1);
                }
            } else {
                // Liñas non elixidas: aparecer bastante visibles e desvanecer lentamente
                if (age < 400) {
                    tl.graphic.alpha = 0.45 * (age / 400);
                } else if (age < 1400) {
                    const fadeT = (age - 400) / 1000;
                    tl.graphic.alpha = 0.45 * (1 - fadeT);
                } else {
                    this.thinkingLayer.removeChild(tl.graphic);
                    tl.graphic.destroy();
                    this._thinkingLines.splice(i, 1);
                }
            }
        }

        // 5. Animación de disolución de ramas ossia (Modo C)
        for (const [branchId, dissolve] of this._dissolvingBranches) {
            const elapsed = now - dissolve.startTime;
            const progress = Math.min(1, elapsed / dissolve.duration);

            for (const nodeId of dissolve.nodeIds) {
                const info = this.nodeSprites.get(nodeId);
                if (!info) continue;

                // Facer desaparecer progresivamente
                info.container.alpha = 1 - progress;
                // Escala lixeiramente reducida
                info.container.scale.set(1.0 - progress * 0.3);

                // Emitir partículas de cinsa durante a disolución
                if (progress > 0.2 && progress < 0.8 && Math.random() < 0.15) {
                    this._spawnDissolutionParticles(
                        info.container.x, info.container.y,
                        0x888899, 2
                    );
                }
            }

            if (progress >= 1) {
                // Explosión final de partículas
                for (const nodeId of dissolve.nodeIds) {
                    const info = this.nodeSprites.get(nodeId);
                    if (!info) continue;
                    this._spawnDissolutionParticles(
                        info.container.x, info.container.y,
                        info.color, 10
                    );
                    // Eliminar o nodo
                    info.container.destroy({ children: true });
                    this.nodeSprites.delete(nodeId);
                }
                this._dissolvingBranches.delete(branchId);
            }
        }

        // 6. Partículas
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.x += p._vx * dt;
            p.y += p._vy * dt;
            p._vx *= 0.96; p._vy *= 0.96;
            p._life -= p._decay;
            p.alpha = Math.max(0, p._life);
            if (p._life <= 0) {
                this.particleLayer.removeChild(p);
                p.destroy();
                this.particles.splice(i, 1);
            }
        }
    }

    // ── Exportar PNG con fondo transparente ──
    async exportPNG() {
        const savedFilters = this.app.stage.filters;
        this.app.stage.filters = [];
        this.gridLayer.visible = false;
        this.thinkingLayer.visible = false;
        this.app.renderer.background.alpha = 0;
        this.app.render();

        let dataURL;
        try {
            if (this.app.renderer.extract) {
                const canvas = await this.app.renderer.extract.canvas(this.app.stage);
                dataURL = canvas.toDataURL('image/png');
            } else {
                dataURL = this.app.canvas.toDataURL('image/png');
            }
        } catch (e) {
            console.warn('Extract fallback:', e);
            dataURL = this.app.canvas.toDataURL('image/png');
        }

        this.app.stage.filters = savedFilters;
        this.gridLayer.visible = true;
        this.thinkingLayer.visible = true;
        this.app.renderer.background.alpha = 1;

        const link = document.createElement('a');
        link.download = `markov-graph-${Date.now()}.png`;
        link.href = dataURL;
        link.click();
    }

    // ── Limpar todo ──
    clear() {
        for (const [, info] of this.nodeSprites)
            info.container.destroy({ children: true });
        this.nodeSprites.clear();

        for (const g of this.edgeGraphics) g.destroy();
        this.edgeGraphics = [];

        for (const p of this.particles) p.destroy();
        this.particles = [];

        this.clearThinkingLines();
        this._dissolvingBranches.clear();

        this.autoCameraX = 0;
        this.targetAutoCameraX = 0;
        this.panOffsetX = 0;
        this.panOffsetY = 0;
        this.lastStep = 0;
        this._userHasControl = false;
        this.zoomLevel = 1.0;
        this.worldContainer.scale.set(1);
        this.worldContainer.x = 0;
        this.worldContainer.y = 0;
        this._updateZoomDisplay();
    }

    // ── Resize ──
    resize(w, h) {
        this.canvasW = w;
        this.canvasH = h;
        this.app.renderer.resize(w, h);
        const old = [...this.gridLayer.children];
        this.gridLayer.removeChildren();
        for (const c of old) c.destroy();
        this._drawGrid();
    }
}

import { DEFAULT_TRANSITIONS, DEFAULTS } from './config.js';

// ── Estruturas de datos ──

class GraphNode {
    constructor(id, step, scaleDegree, type, branchId) {
        this.id = id;
        this.step = step;
        this.scaleDegree = scaleDegree;
        this.type = type;       // 'normal' | 'noise' | 'ossia'
        this.branchId = branchId;
    }
}

class GraphEdge {
    constructor(sourceId, targetId, type, interval) {
        this.sourceId = sourceId;
        this.targetId = targetId;
        this.type = type;       // 'normal' | 'noise' | 'ossia' | 'merge'
        this.interval = interval;
    }
}

class Branch {
    constructor(id, currentDegree, isOssia = false) {
        this.id = id;
        this.currentDegree = currentDegree;
        this.isActive = true;
        this.lastNodeId = null;
        this.isOssia = isOssia;
    }
}

// ── Utilidades ──

function weightedRandom(weights) {
    const entries = Object.entries(weights);
    let total = 0;
    for (const [, w] of entries) total += w;
    if (total <= 0) return parseInt(entries[0][0]);

    let r = Math.random() * total;
    for (const [key, w] of entries) {
        r -= w;
        if (r <= 0) return parseInt(key);
    }
    return parseInt(entries[entries.length - 1][0]);
}

// ── Motor Markov ──

export class MarkovEngine {
    constructor(config) {
        this.scaleSize = config.scale.size;
        this.transitions = { ...config.transitions };
        this.noisePercent = config.noisePercent;
        this.ossiaOpenChance = config.ossiaOpenChance;
        this.ossiaCloseChance = config.ossiaCloseChance;
        this.maxBranches = DEFAULTS.maxBranches;

        this.nodes = [];
        this.edges = [];
        this.branches = [];
        this.currentStep = 0;
        this._nextId = 0;
        this._nextBranchId = 1;
        this.nodesById = new Map();

        // Modo de visualización: 'interactive' | 'machine'
        this.vizMode = 'interactive';
    }

    _genId() {
        return this._nextId++;
    }

    setVizMode(mode) {
        this.vizMode = mode;
    }

    // Inicializar co nodo raíz
    initialize(startDegree = 0) {
        this.nodes = [];
        this.edges = [];
        this.branches = [];
        this.currentStep = 0;
        this._nextId = 0;
        this._nextBranchId = 1;
        this.nodesById = new Map();

        const root = new GraphNode(this._genId(), 0, startDegree, 'normal', 0);
        this.nodes.push(root);
        this.nodesById.set(root.id, root);

        const mainBranch = new Branch(0, startDegree, false);
        mainBranch.lastNodeId = root.id;
        this.branches.push(mainBranch);

        return { newNodes: [root], newEdges: [], step: 0 };
    }

    // ── Tick do modo interactivo (o orixinal) ──
    _tickInteractive() {
        this.currentStep++;
        const newNodes = [];
        const newEdges = [];
        const branchesToAdd = [];

        const activeBranches = this.branches.filter(b => b.isActive);

        for (const branch of activeBranches) {
            const isNoise = Math.random() * 100 < this.noisePercent;
            let interval, newDegree;

            if (isNoise) {
                interval = Math.floor(Math.random() * 17) - 8;
                newDegree = branch.currentDegree + interval;
            } else {
                interval = weightedRandom(this.transitions);
                newDegree = branch.currentDegree + interval;
            }

            const nodeType = isNoise ? 'noise' : (branch.isOssia ? 'ossia' : 'normal');
            const node = new GraphNode(
                this._genId(), this.currentStep, newDegree, nodeType, branch.id
            );
            newNodes.push(node);
            this.nodesById.set(node.id, node);

            const edgeType = isNoise ? 'noise' : (branch.isOssia ? 'ossia' : 'normal');
            const edge = new GraphEdge(branch.lastNodeId, node.id, edgeType, interval);
            newEdges.push(edge);

            branch.currentDegree = newDegree;
            branch.lastNodeId = node.id;

            const totalActive = activeBranches.length + branchesToAdd.length;
            if (Math.random() * 100 < this.ossiaOpenChance && totalActive < this.maxBranches) {
                const newBranch = new Branch(this._nextBranchId++, newDegree, true);
                newBranch.lastNodeId = node.id;
                branchesToAdd.push(newBranch);
            }

            if (branch.isOssia && Math.random() * 100 < this.ossiaCloseChance) {
                branch.isActive = false;
                const mainBranch = this.branches.find(b => b.id === 0);
                if (mainBranch && mainBranch.lastNodeId !== null) {
                    const mergeEdge = new GraphEdge(
                        node.id, mainBranch.lastNodeId, 'merge', 0
                    );
                    newEdges.push(mergeEdge);
                }
            }
        }

        for (const b of branchesToAdd) {
            this.branches.push(b);
        }

        this.nodes.push(...newNodes);
        this.edges.push(...newEdges);

        return { newNodes, newEdges, step: this.currentStep };
    }

    // ── Tick do modo "A Máquina Pensando" ──
    // Idéntico ao interactivo (ossias, ruído e probabilidades incluídos),
    // pero devolve tamén thinkingPaths para a animación visual de cálculo.
    _tickMachine() {
        this.currentStep++;
        const newNodes      = [];
        const newEdges      = [];
        const branchesToAdd = [];
        const thinkingPaths = [];

        const activeBranches = this.branches.filter(b => b.isActive);

        for (const branch of activeBranches) {
            const isNoise = Math.random() * 100 < this.noisePercent;
            let interval, newDegree;

            if (isNoise) {
                interval  = Math.floor(Math.random() * 17) - 8;
                newDegree = branch.currentDegree + interval;
            } else {
                interval  = weightedRandom(this.transitions);
                newDegree = branch.currentDegree + interval;
            }

            // Candidatos visuais: 8 intervalos cardinais.
            // Se o intervalo real non está entre eles, substitúe o último.
            const cardinals = [-3, -2, -1, 0, +1, +2, +3, +4];
            const showIntervals = cardinals.includes(interval)
                ? cardinals
                : [...cardinals.slice(0, 7), interval];

            for (const iv of showIntervals) {
                thinkingPaths.push({
                    fromNodeId:   branch.lastNodeId,
                    targetDegree: branch.currentDegree + iv,
                    targetStep:   this.currentStep,
                    interval:     iv,
                    isChosen:     iv === interval,
                });
            }

            const nodeType = isNoise ? 'noise' : (branch.isOssia ? 'ossia' : 'normal');
            const node = new GraphNode(
                this._genId(), this.currentStep, newDegree, nodeType, branch.id
            );
            newNodes.push(node);
            this.nodesById.set(node.id, node);

            const edgeType = isNoise ? 'noise' : (branch.isOssia ? 'ossia' : 'normal');
            const edge = new GraphEdge(branch.lastNodeId, node.id, edgeType, interval);
            newEdges.push(edge);

            branch.currentDegree = newDegree;
            branch.lastNodeId    = node.id;

            // Ossias funcionan igual que no modo interactivo
            const totalActive = activeBranches.length + branchesToAdd.length;
            if (Math.random() * 100 < this.ossiaOpenChance && totalActive < this.maxBranches) {
                const newBranch = new Branch(this._nextBranchId++, newDegree, true);
                newBranch.lastNodeId = node.id;
                branchesToAdd.push(newBranch);
            }

            if (branch.isOssia && Math.random() * 100 < this.ossiaCloseChance) {
                branch.isActive = false;
                const mainBranch = this.branches.find(b => b.id === 0);
                if (mainBranch && mainBranch.lastNodeId !== null) {
                    const mergeEdge = new GraphEdge(node.id, mainBranch.lastNodeId, 'merge', 0);
                    newEdges.push(mergeEdge);
                }
            }
        }

        for (const b of branchesToAdd) this.branches.push(b);
        this.nodes.push(...newNodes);
        this.edges.push(...newEdges);

        return { newNodes, newEdges, step: this.currentStep, thinkingPaths };
    }

    // Avanzar un paso temporal (despacha segundo o modo)
    tick() {
        return this.vizMode === 'machine'
            ? this._tickMachine()
            : this._tickInteractive();
    }

    // Actualizar parámetros en tempo real
    setNoisePercent(val) { this.noisePercent = val; }
    setOssiaOpenChance(val) { this.ossiaOpenChance = val; }
    setOssiaCloseChance(val) { this.ossiaCloseChance = val; }
    setTransitions(t) { this.transitions = { ...t }; }
    setScaleSize(size) { this.scaleSize = size; }

    reset(config, startDegree = 0) {
        this.scaleSize = config.scale.size;
        this.transitions = { ...config.transitions };
        this.noisePercent = config.noisePercent;
        this.ossiaOpenChance = config.ossiaOpenChance;
        this.ossiaCloseChance = config.ossiaCloseChance;
        return this.initialize(startDegree);
    }
}

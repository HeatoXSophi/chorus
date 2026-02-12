
/**
 * Chorus Studio - Visual Editor (Canvas API)
 */

const studio = {
    canvas: null,
    ctx: null,
    nodes: [],
    connections: [],

    // State
    draggingNode: null,
    dragOffset: { x: 0, y: 0 },
    wiringState: null, // { sourceNodeId: 'a', startX, startY, currentX, currentY, snapNodeId: null }
    currentGraphId: null,
    graphName: 'Mi Nuevo Agente',

    // Config
    nodeWidth: 160,
    nodeHeight: 80,
    nodeRadius: 8,
    colors: {
        nodeBg: '#1a1a24',
        nodeBorder: '#3b82f6',
        text: '#ffffff',
        connector: '#5a5a70',
        connectorActive: '#7c5cfc',
        running: '#facc15', // Yellow
        success: '#4ade80', // Green
        error: '#f87171'    // Red
    },

    init() {
        this.canvas = document.getElementById('studio-canvas');
        if (!this.canvas) return;

        this.ctx = this.canvas.getContext('2d');

        // Handle resize
        window.addEventListener('resize', () => this.resize());
        this.resize();

        // Handle Interactions
        this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.canvas.addEventListener('mouseleave', (e) => this.handleMouseUp(e));

        // Handle Drag & Drop from Sidebar
        this.canvas.addEventListener('dragover', (e) => e.preventDefault());
        this.canvas.addEventListener('drop', (e) => this.handleDrop(e));

        // Toolbar Buttons
        const btnRun = document.getElementById('btn-studio-run');
        if (btnRun) btnRun.addEventListener('click', () => this.runPipeline());

        const btnSave = document.getElementById('btn-studio-save');
        if (btnSave) btnSave.addEventListener('click', () => this.saveGraph());

        const btnConfirmRun = document.getElementById('btn-confirm-run');
        if (btnConfirmRun) btnConfirmRun.addEventListener('click', () => this.executePipeline());

        // Initialize Palette Dragging
        document.querySelectorAll('.palette-item').forEach(item => {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('type', item.dataset.type);
                e.dataTransfer.setData('label', item.dataset.label);
            });
        });

        // Initial Data (The "Hello World" requested)
        this.nodes = [
            { id: 'a', label: '📝 Agent A', x: 100, y: 100 },
            { id: 'b', label: '🤖 Agent B', x: 400, y: 100 }
        ];

        this.connections = [
            { from: 'a', to: 'b' }
        ];

        // Start Loop
        this.render();
        console.log("🎨 Studio initialized with Canvas API");

        // Fetch Real Agents
        this.fetchAgents();
    },

    async fetchAgents() {
        const container = document.getElementById('palette-agents');
        if (!container) return;

        try {
            // Wait a bit for API to be ready if needed, or check window.api
            if (!window.api) {
                console.warn("API not found, retrying in 1s...");
                setTimeout(() => this.fetchAgents(), 1000);
                return;
            }

            const { data, error } = await api.agents.list();
            if (error) throw error;

            container.innerHTML = ''; // Clear loading

            data.forEach(agent => {
                const item = document.createElement('div');
                item.className = 'palette-item';
                item.draggable = true;
                item.dataset.type = 'agent';
                item.dataset.label = agent.name;
                item.dataset.price = agent.cost_per_task || 0;
                item.dataset.id = agent.id;

                item.innerHTML = `
                    <span class="p-icon">🤖</span>
                    <div class="p-info">
                        <span class="p-label" title="${agent.name}">${agent.name}</span>
                        <small style="display:block; font-size:10px; color:#aaa; margin-bottom:4px; max-width:110px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${agent.description || ''}">
                            ${agent.description || "No description"}
                        </small>
                        <div class="p-price">${agent.cost_per_call || 0}</div>
                    </div>
                `;

                // Drag Handler
                item.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('type', 'agent');
                    e.dataTransfer.setData('label', agent.name);
                    e.dataTransfer.setData('price', agent.cost_per_task || 0);
                    e.dataTransfer.setData('agentId', agent.id);
                });

                container.appendChild(item);
            });

        } catch (err) {
            container.innerHTML = `<div style="padding:10px; color:red; font-size:11px">Failed to load agents</div>`;
            console.error(err);
        }
    },

    // ── Execution Engine ─────────────────────────────────────────────

    runPipeline() {
        const modal = document.getElementById('modal-run');
        if (modal) modal.classList.add('active');
    },

    async executePipeline() {
        // 1. Close Modal & Get Input
        const modal = document.getElementById('modal-run');
        const inputRaw = document.getElementById('run-input').value;
        modal.classList.remove('active');

        let inputData;
        try {
            inputData = inputRaw.trim().startsWith('{') ? JSON.parse(inputRaw) : { text: inputRaw };
        } catch (e) {
            inputData = { text: inputRaw };
        }

        // 2. Find Start Node (First node created or one without inputs)
        // For now, let's just take the first one in the array as "Start" or seek root.
        const startNode = this.getStartNode();
        if (!startNode) {
            alert("No hay nodos para ejecutar.");
            return;
        }

        console.log("🚀 Starting Pipeline...", startNode);

        // Open Result Modal
        const resModal = document.getElementById('modal-result');
        const stepsContainer = document.getElementById('pipeline-steps');
        const finalOutput = document.getElementById('pipeline-output');

        if (resModal) resModal.classList.add('active');
        stepsContainer.innerHTML = '';
        finalOutput.innerText = 'Ejecutando...';

        // 3. Execution Loop
        let currentNode = startNode;
        let currentInput = inputData;
        let stepCount = 1;

        this.resetExecutionState();

        while (currentNode) {
            // Visual Interaction
            currentNode.status = 'running';
            this.render();

            // Add Step to UI
            const stepId = `step-${stepCount}`;
            stepsContainer.innerHTML += `
                <div class="step-item" id="${stepId}">
                    <div class="step-header">
                        <span class="step-num">${stepCount}</span>
                        <span class="step-agent">${currentNode.label}</span>
                        <span class="step-status">⏳</span>
                    </div>
                </div>`;

            // Execute Agent
            try {
                // Find agent endpoint (real lookup needed in future, for now mock/demo)
                // If it's a real marketplace agent, we need its endpoint from the ID?
                // For this demo, we can just use the 'skill' or assume it's one of our local demo agents if applicable.

                // Let's use the API.sendJob logic
                // But wait, the node might not have the full endpoint url if dragged from palette?
                // The palette data had 'agentId'. We might need to fetch details or assume endpoint structure.

                // HACK for Demo: If label has "Echo", route to EchoBot. If "Calc", route to SuperCalc.
                // In production, we'd look up the agent's endpoint by ID.
                let endpoint = "http://localhost:8000"; // Default to local demo
                let skill = "unknown";

                if (currentNode.label.includes("Echo")) {
                    endpoint = "http://localhost:54321"; // Changes per port assignment in demo
                    skill = "echo";
                } else if (currentNode.label.includes("Calc")) {
                    endpoint = "http://localhost:54321";
                    skill = "calculator";
                } else {
                    // Fallback to what we have in DB if possible? 
                    // For now let's try to infer from data attributes if we stored them (we didn't store endpoint yet in node)
                    // Let's just simulate specific agents for the "Show"
                    endpoint = "http://localhost:8000";
                }

                // If we are strictly using the supabase_demo.py agents:
                // They run on random ports. The studio doesn't know them easily unless we query Registry.
                // Let's query registry for this agent name to get endpoint!
                const { agents } = await api.discover(null); // Fetch all online
                const agentData = agents.find(a => a.agent_name === currentNode.label || currentNode.label.includes(a.agent_name));

                if (agentData) {
                    endpoint = agentData.api_endpoint;
                    skill = agentData.skills[0].skill_name;
                }

                console.log(`Sending job to ${currentNode.label} (${endpoint})...`);

                const result = await api.sendJob(endpoint, skill, currentInput, 10.0);

                // Update UI Step
                const stepEl = document.getElementById(stepId);

                if (result.status === 'SUCCESS') {
                    currentNode.status = 'success';
                    currentInput = result.output_data; // Output becomes next Input

                    stepEl.classList.add('success');
                    stepEl.querySelector('.step-status').innerText = '✅';
                    stepEl.innerHTML += `<div class="step-output">${JSON.stringify(result.output_data)}</div>`;
                } else {
                    throw new Error(result.error_message || "Unknown Error");
                }

            } catch (err) {
                currentNode.status = 'error';
                console.error(err);
                document.getElementById(stepId).innerHTML += `<div class="step-error">${err.message}</div>`;
                finalOutput.innerText = "❌ Pipeline Failed";
                this.render();
                return; // Stop execution
            }

            this.render();
            stepCount++;

            // Find Next Node
            const connection = this.connections.find(c => c.from === currentNode.id);
            if (connection) {
                currentNode = this.nodes.find(n => n.id === connection.to);
            } else {
                currentNode = null; // End of line
            }

            // Artificial delay for visual effect
            await new Promise(r => setTimeout(r, 1000));
        }

        finalOutput.innerText = JSON.stringify(currentInput, null, 2);
    },

    getStartNode() {
        // A node is a start node if it has NO incoming connections.
        return this.nodes.find(n => !this.connections.some(c => c.to === n.id));
    },

    resetExecutionState() {
        this.nodes.forEach(n => delete n.status);
        this.render();
    },

    resize() {
        const parent = this.canvas.parentElement;
        this.canvas.width = parent.clientWidth;
        this.canvas.height = parent.clientHeight;
        this.render();
    },

    // ── Interaction ──────────────────────────────────────────────────

    getMousePos(e) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    },

    handleMouseDown(e) {
        const pos = this.getMousePos(e);

        // 1. Check for Output Port click (Right side)
        const portNode = this.getNodeAtPort(pos.x, pos.y, 'output');
        if (portNode) {
            this.wiringState = {
                sourceNodeId: portNode.id,
                startX: portNode.x + this.nodeWidth,
                startY: portNode.y + this.nodeHeight / 2,
                currentX: pos.x,
                currentY: pos.y
            };
            return;
        }

        // 2. Check for Node click (Dragging)
        // Check if clicking a node (reverse iteration to pick top-most)
        for (let i = this.nodes.length - 1; i >= 0; i--) {
            const node = this.nodes[i];
            if (
                pos.x >= node.x &&
                pos.x <= node.x + this.nodeWidth &&
                pos.y >= node.y &&
                pos.y <= node.y + this.nodeHeight
            ) {
                this.draggingNode = node;
                this.dragOffset = {
                    x: pos.x - node.x,
                    y: pos.y - node.y
                };
                return;
            }
        }
    },

    handleMouseMove(e) {
        const pos = this.getMousePos(e);

        // Wiring Mode
        if (this.wiringState) {
            this.wiringState.currentX = pos.x;
            this.wiringState.currentY = pos.y;
            this.render();
            return;
        }

        // Dragging Mode
        if (this.draggingNode) {
            this.draggingNode.x = pos.x - this.dragOffset.x;
            this.draggingNode.y = pos.y - this.dragOffset.y;
            this.render();
        }
    },

    handleMouseUp(e) {
        // End Wiring
        if (this.wiringState) {
            const pos = this.getMousePos(e);
            // Check if dropped on Input Port (Left side)
            const targetNode = this.getNodeAtPort(pos.x, pos.y, 'input');

            if (targetNode && targetNode.id !== this.wiringState.sourceNodeId) {
                // Create Connection
                this.connections.push({
                    from: this.wiringState.sourceNodeId,
                    to: targetNode.id
                });
            }
            this.wiringState = null;
            this.render();
            return;
        }

        this.draggingNode = null;
    },

    handleDrop(e) {
        e.preventDefault();
        const pos = this.getMousePos(e);
        const type = e.dataTransfer.getData('type');
        const label = e.dataTransfer.getData('label');
        const price = e.dataTransfer.getData('price');

        if (type && label) {
            this.addNode(pos.x, pos.y, label, type, price);
        }
    },

    addNode(x, y, label, type, price = 0) {
        const id = Math.random().toString(36).substr(2, 9);
        this.nodes.push({
            id,
            x,
            y,
            label,
            type,
            price: parseFloat(price)
        });
        this.render();
    },

    // Check if x,y is near a port type ('input' or 'output')
    getNodeAtPort(x, y, type) {
        const PORT_RADIUS = 15; // Hitbox size
        for (let i = this.nodes.length - 1; i >= 0; i--) {
            const node = this.nodes[i];
            let px, py;

            if (type === 'output') {
                px = node.x + this.nodeWidth;
                py = node.y + this.nodeHeight / 2;
            } else {
                px = node.x;
                py = node.y + this.nodeHeight / 2;
            }

            const dist = Math.sqrt((x - px) ** 2 + (y - py) ** 2);
            if (dist <= PORT_RADIUS) return node;
        }
        return null;
    },

    // ── Drawing Functions ────────────────────────────────────────────

    drawNode(node) {
        const { ctx } = this;
        const x = node.x;
        const y = node.y;
        const w = this.nodeWidth;
        const h = this.nodeHeight;
        const r = this.nodeRadius;

        // Shadow
        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctx.shadowBlur = 10;
        ctx.shadowOffsetY = 4;

        // Box
        ctx.fillStyle = this.colors.nodeBg;
        ctx.beginPath();
        ctx.roundRect(x, y, w, h, r);
        ctx.fill();

        // Border
        ctx.shadowColor = 'transparent'; // Reset shadow for border

        // Status Colors
        if (node.status === 'running') ctx.strokeStyle = this.colors.running;
        else if (node.status === 'success') ctx.strokeStyle = this.colors.success;
        else if (node.status === 'error') ctx.strokeStyle = this.colors.error;
        else ctx.strokeStyle = this.colors.nodeBorder;

        ctx.lineWidth = node.status ? 4 : 2; // Thicker if active
        ctx.stroke();

        // Header (Top bar)
        ctx.fillStyle = nodeId === this.wiringState?.sourceNodeId ? 'rgba(124, 92, 252, 0.3)' : 'rgba(59, 130, 246, 0.1)';
        if (node.status === 'running') ctx.fillStyle = 'rgba(250, 204, 21, 0.2)';

        ctx.beginPath();
        ctx.roundRect(x, y, w, 30, [r, r, 0, 0]);
        ctx.fill();

        // Text
        ctx.fillStyle = this.colors.text;
        ctx.font = '600 14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(node.label, x + w / 2, y + 15);

        // Price Tag (Top Right)
        if (node.price > 0) {
            ctx.fillStyle = '#4ade80';
            ctx.font = '600 10px Inter, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(node.price + ' ₵', x + w - 8, y + 10);
            // Reset for body text
            ctx.textAlign = 'center';
        }

        // Body Text placeholder
        ctx.fillStyle = '#9898aa';
        ctx.font = '400 12px Inter, sans-serif';
        ctx.fillText("Input -> Output", x + w / 2, y + 50);

        // Ports (dots)
        this.drawPort(x + w, y + h / 2); // Output (Right)
        this.drawPort(x, y + h / 2);     // Input (Left)
    },

    drawPort(x, y) {
        const { ctx } = this;
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#fff';
        ctx.fill();
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 1;
        ctx.stroke();
    },

    drawConnector(nodeA, nodeB) {
        const { ctx } = this;

        // Calculate start (right side of A) and end (left side of B)
        const startX = nodeA.x + this.nodeWidth;
        const startY = nodeA.y + this.nodeHeight / 2;
        const endX = nodeB.x;
        const endY = nodeB.y + this.nodeHeight / 2;

        // Bezier Control Points (curved line)
        const cp1x = startX + (endX - startX) / 2;
        const cp1y = startY;
        const cp2x = endX - (endX - startX) / 2;
        const cp2y = endY;

        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, endX, endY);

        ctx.strokeStyle = this.colors.connector;
        ctx.lineWidth = 3;
        ctx.stroke();
    },

    render() {
        const { ctx, canvas } = this;
        // Clear
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw Connections
        this.connections.forEach(conn => {
            const nodeA = this.nodes.find(n => n.id === conn.from);
            const nodeB = this.nodes.find(n => n.id === conn.to);
            if (nodeA && nodeB) this.drawConnector(nodeA, nodeB);
        });

        // Draw Temporary Wire & Snap Higlight
        if (this.wiringState) {
            const { startX, startY, currentX, currentY, snapNodeId } = this.wiringState;

            // Draw Wire
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            // Simple curve to mouse
            const cp1x = startX + (currentX - startX) / 2;
            ctx.bezierCurveTo(cp1x, startY, cp1x, currentY, currentX, currentY);
            ctx.strokeStyle = this.colors.connectorActive;
            ctx.lineWidth = 3;
            ctx.setLineDash([5, 5]);
            ctx.stroke();
            ctx.setLineDash([]);

            // Draw Snap Highlight Ring
            if (snapNodeId) {
                ctx.beginPath();
                ctx.arc(currentX, currentY, 10, 0, Math.PI * 2);
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 3;
                ctx.stroke();

                ctx.beginPath();
                ctx.arc(currentX, currentY, 14, 0, Math.PI * 2);
                ctx.strokeStyle = this.colors.connectorActive;
                ctx.lineWidth = 2;
                ctx.stroke();
            }
        }

        // Draw Nodes
        this.nodes.forEach(node => this.drawNode(node));

        // Request next frame (optional if static)
        // requestAnimationFrame(() => this.render());
    }
};

// Initialize when tab is opened
document.addEventListener('DOMContentLoaded', () => {
    // Only init if we are on proper page or just run it
    // For SPA, we might need to hook into navigation events
    // But for now, let's look for the canvas
    if (document.getElementById('studio-canvas')) {
        studio.init();
    }

    // Also listen for sidebar clicks to resize canvas when shown
    document.querySelectorAll('.nav-item[data-page="studio"]').forEach(btn => {
        btn.addEventListener('click', () => {
            setTimeout(() => studio.resize(), 50);
        });
    });
});

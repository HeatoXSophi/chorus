
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

    // Config
    nodeWidth: 160,
    nodeHeight: 80,
    nodeRadius: 8,
    colors: {
        nodeBg: '#1a1a24',
        nodeBorder: '#3b82f6',
        text: '#ffffff',
        connector: '#5a5a70',
        connectorActive: '#7c5cfc'
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
                        <span class="p-label">${agent.name}</span>
                        <div class="p-price">${agent.cost_per_task || 0}</div>
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
        ctx.strokeStyle = this.colors.nodeBorder;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Header (Top bar)
        ctx.fillStyle = 'rgba(59, 130, 246, 0.1)';
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

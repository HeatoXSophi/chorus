
/**
 * Chorus Studio - Visual Editor (Canvas API)
 */

const studio = {
    canvas: null,
    ctx: null,
    nodes: [],
    connections: [],

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
    },

    resize() {
        const parent = this.canvas.parentElement;
        this.canvas.width = parent.clientWidth;
        this.canvas.height = parent.clientHeight;
        this.render();
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

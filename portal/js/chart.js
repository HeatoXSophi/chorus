/**
 * 🎵 Chorus Portal — Lightweight Chart Renderer
 * Pure Canvas chart — no dependencies needed
 */

class MiniChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.data = [];
        this.animated = false;
        this.animProgress = 0;
        this.resizeObserver = new ResizeObserver(() => this.draw());
        this.resizeObserver.observe(this.canvas.parentElement);
    }

    setData(data) {
        this.data = data;
        this.animated = false;
        this.animProgress = 0;
        this.animate();
    }

    animate() {
        if (this.animProgress >= 1) {
            this.animated = true;
            this.draw();
            return;
        }
        this.animProgress = Math.min(1, this.animProgress + 0.04);
        this.draw();
        requestAnimationFrame(() => this.animate());
    }

    draw() {
        if (!this.canvas || !this.ctx) return;
        const parent = this.canvas.parentElement;
        const dpr = window.devicePixelRatio || 1;
        const w = parent.clientWidth;
        const h = parent.clientHeight;

        this.canvas.width = w * dpr;
        this.canvas.height = h * dpr;
        this.canvas.style.width = w + 'px';
        this.canvas.style.height = h + 'px';
        this.ctx.scale(dpr, dpr);

        const ctx = this.ctx;
        const data = this.data;
        if (!data.length) return;

        const pad = { top: 20, right: 20, bottom: 30, left: 50 };
        const chartW = w - pad.left - pad.right;
        const chartH = h - pad.top - pad.bottom;

        const maxVal = Math.max(...data.map(d => d.value), 1) * 1.15;
        const minVal = 0;

        ctx.clearRect(0, 0, w, h);

        // Grid lines
        const gridLines = 4;
        for (let i = 0; i <= gridLines; i++) {
            const y = pad.top + (chartH / gridLines) * i;
            const val = maxVal - (maxVal - minVal) * (i / gridLines);

            ctx.beginPath();
            ctx.strokeStyle = 'rgba(255,255,255,0.04)';
            ctx.lineWidth = 1;
            ctx.moveTo(pad.left, y);
            ctx.lineTo(w - pad.right, y);
            ctx.stroke();

            ctx.fillStyle = 'rgba(255,255,255,0.3)';
            ctx.font = '11px Inter';
            ctx.textAlign = 'right';
            ctx.fillText(val.toFixed(1), pad.left - 8, y + 4);
        }

        // X labels
        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.font = '11px Inter';
        ctx.textAlign = 'center';
        const labelStep = Math.max(1, Math.floor(data.length / 6));
        data.forEach((d, i) => {
            if (i % labelStep === 0) {
                const x = pad.left + (chartW / (data.length - 1) || 0) * i;
                ctx.fillText(d.label, x, h - 8);
            }
        });

        // Build points
        const points = data.map((d, i) => ({
            x: pad.left + (chartW / (data.length - 1) || 0) * i,
            y: pad.top + chartH - (d.value / maxVal) * chartH,
        }));

        // Animated progress
        const progress = this.animProgress;

        // Gradient fill
        const gradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + chartH);
        gradient.addColorStop(0, `rgba(124, 92, 252, ${0.25 * progress})`);
        gradient.addColorStop(1, 'rgba(124, 92, 252, 0)');

        ctx.beginPath();
        ctx.moveTo(points[0].x, pad.top + chartH);
        points.forEach((p, i) => {
            const effectiveY = pad.top + chartH - (pad.top + chartH - p.y) * progress;
            if (i === 0) {
                ctx.lineTo(p.x, effectiveY);
            } else {
                const prev = points[i - 1];
                const prevY = pad.top + chartH - (pad.top + chartH - prev.y) * progress;
                const cpx = (prev.x + p.x) / 2;
                ctx.bezierCurveTo(cpx, prevY, cpx, effectiveY, p.x, effectiveY);
            }
        });
        ctx.lineTo(points[points.length - 1].x, pad.top + chartH);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        // Line
        ctx.beginPath();
        points.forEach((p, i) => {
            const effectiveY = pad.top + chartH - (pad.top + chartH - p.y) * progress;
            if (i === 0) {
                ctx.moveTo(p.x, effectiveY);
            } else {
                const prev = points[i - 1];
                const prevY = pad.top + chartH - (pad.top + chartH - prev.y) * progress;
                const cpx = (prev.x + p.x) / 2;
                ctx.bezierCurveTo(cpx, prevY, cpx, effectiveY, p.x, effectiveY);
            }
        });
        ctx.strokeStyle = '#7c5cfc';
        ctx.lineWidth = 2.5;
        ctx.stroke();

        // Dots
        if (progress >= 1) {
            points.forEach(p => {
                ctx.beginPath();
                ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
                ctx.fillStyle = '#7c5cfc';
                ctx.fill();
                ctx.beginPath();
                ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(124,92,252,0.3)';
                ctx.lineWidth = 2;
                ctx.stroke();
            });
        }
    }

    generateDemoData(days = 7) {
        const data = [];
        const now = new Date();
        let cumulative = 0;
        for (let i = days - 1; i >= 0; i--) {
            const d = new Date(now);
            d.setDate(d.getDate() - i);
            const label = d.toLocaleDateString('es', { day: 'numeric', month: 'short' });
            cumulative += Math.random() * 0.5 + 0.05;
            data.push({ label, value: parseFloat(cumulative.toFixed(2)) });
        }
        return data;
    }
}

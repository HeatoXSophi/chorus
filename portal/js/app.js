/**
 * 🎵 Chorus Portal — Main Application
 * SPA routing, auth flow, dashboard logic, and interactive features
 */

// ── App State ────────────────────────────────────────────────
const state = {
    user: null,     // { name, email, ownerId }
    balance: 0,
    connected: false,
};

// ── Initialization ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    initNavigation();
    initModals();
    initQuickActions();
    initMarketplaceSearch();
});

// ================================================================
// AUTH FLOW
// ================================================================

function initAuth() {
    // Check if already logged in via session
    try {
        API.getCurrentUser().then(user => {
            if (user) {
                const name = user.user_metadata.full_name || user.email.split('@')[0];
                loginUserSuccess(user, name);
            }
        }).catch(err => console.warn("Session check failed:", err));
    } catch (e) {
        console.error("Auth init error:", e);
    }

    // Toggle login/register
    const linkReg = document.getElementById('show-register');
    if (linkReg) linkReg.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('login-form').classList.remove('active');
        document.getElementById('register-form').classList.add('active');
    });

    const linkLogin = document.getElementById('show-login');
    if (linkLogin) linkLogin.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('register-form').classList.remove('active');
        document.getElementById('login-form').classList.add('active');
    });

    // Google Login - Coming Soon
    const btnGoogle = document.querySelector('.btn-google');
    if (btnGoogle) btnGoogle.addEventListener('click', (e) => {
        e.preventDefault();
        alert('🚧 Próximamente: Iniciar sesión con Google.\n\nPor ahora, por favor usa tu Email y Contraseña.');
    });

    // Login
    const btnLogin = document.getElementById('btn-login');
    if (btnLogin) btnLogin.addEventListener('click', async () => {
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value.trim();

        if (!email || !password) { alert('Ingresa email y contraseña'); return; }

        const originalText = btnLogin.innerHTML;
        btnLogin.querySelector('span').textContent = 'Conectando...';
        btnLogin.disabled = true;

        try {
            const user = await API.login(email, password);

            if (user._error) {
                // Check for unconfirmed email
                if (user.message.includes("Email not confirmed")) {
                    const wantResend = confirm("⚠️ Tu cuenta existe pero no has confirmado tu email.\n\n¿Quieres que te reenviemos el correo de confirmación?");
                    if (wantResend) {
                        await API.resendConfirmation(email);
                        alert("✅ Correo reenviado. Por favor revisa tu bandeja de entrada (y Spam).");
                    }
                } else {
                    alert(`Error de inicio de sesión: ${user.message}`);
                }
                btnLogin.innerHTML = originalText;
                btnLogin.disabled = false;
            } else {
                const name = user.user_metadata.full_name || email.split('@')[0];
                loginUserSuccess(user, name);
                btnLogin.innerHTML = originalText;
                btnLogin.disabled = false;
            }
        } catch (error) {
            console.error(error);
            alert(`Error inesperado: ${error.message || error}`);
            btnLogin.innerHTML = originalText;
            btnLogin.disabled = false;
        }
    });

    // Register
    const btnRegister = document.getElementById('btn-register');
    if (btnRegister) btnRegister.addEventListener('click', async () => {
        const name = document.getElementById('reg-name').value.trim() || 'User';
        const email = document.getElementById('reg-email').value.trim();
        const password = document.getElementById('reg-password').value.trim();

        if (!email || !password) { alert('Ingresa todos los campos'); return; }
        if (password.length < 6) { alert('La contraseña debe tener al menos 6 caracteres'); return; }

        const originalText = btnRegister.innerHTML;
        btnRegister.querySelector('span').textContent = 'Creando cuenta...';
        btnRegister.disabled = true;

        try {
            // 1. Register
            const user = await API.register(email, password, name);

            if (user._error) {
                alert(`Error de registro: ${user.message}`);
                btnRegister.innerHTML = originalText;
                btnRegister.disabled = false;
                return;
            }

            // 2. Alert & Auto-login attempt
            alert('¡Cuenta creada exitosamente! Intentando iniciar sesión...');

            const loggedIn = await API.login(email, password);

            if (!loggedIn._error) {
                loginUserSuccess(loggedIn, name);
            } else {
                alert("Cuenta creada. Por favor inicia sesión manual.");
                // Switch to login
                document.getElementById('register-form').classList.remove('active');
                document.getElementById('login-form').classList.add('active');
            }

            btnRegister.innerHTML = originalText;
            btnRegister.disabled = false;

        } catch (error) {
            console.error(error);
            alert(`Error de sistema: ${error.message || "No se pudo conectar con Supabase"}`);
            btnRegister.innerHTML = originalText;
            btnRegister.disabled = false;
        }
    });

    // Logout
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) btnLogout.addEventListener('click', async () => {
        try {
            await API.logout();
        } catch (e) { console.error(e); }

        state.user = null;
        state.balance = 0;
        state.connected = false;
        document.getElementById('app-screen').classList.remove('active');
        document.getElementById('auth-screen').classList.add('active');
    });
}

async function loginUserSuccess(user, name) {
    try {
        state.user = {
            name: name,
            email: user.email,
            ownerId: user.id
        };
        state.connected = true;

        // Switch screens
        document.getElementById('auth-screen').classList.remove('active');
        document.getElementById('app-screen').classList.add('active');

        // Update UI
        const avatar = document.getElementById('user-avatar');
        if (avatar) avatar.textContent = name[0].toUpperCase();

        const nameLabel = document.getElementById('user-name-sidebar');
        if (nameLabel) nameLabel.textContent = name;

        // Load dashboard
        await refreshDashboard();
    } catch (e) {
        console.error("Login UI update failed:", e);
        alert("Error cargando el dashboard.");
    }
}

// ================================================================
// NAVIGATION
// ================================================================

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            navigateTo(page);
        });
    });
}

function navigateTo(page) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`[data-page="${page}"]`)?.classList.add('active');

    // Update pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`)?.classList.add('active');

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        wallet: 'Billetera',
        agents: 'Mis Agentes',
        marketplace: 'Marketplace',
        studio: 'Chorus Studio',
    };
    document.getElementById('page-title').textContent = titles[page] || page;

    // Load page data
    if (page === 'dashboard') refreshDashboard();
    if (page === 'wallet') refreshWallet();
    if (page === 'agents') refreshAgents();
    if (page === 'marketplace') refreshMarketplace();
}

// ================================================================
// DASHBOARD
// ================================================================

let earningsChart = null;

async function refreshDashboard() {
    if (!state.user) return;

    try {
        // Fetch all data in parallel
        const [balance, economy, skills, health, audit] = await Promise.all([
            API.getBalance(state.user.ownerId).catch(() => 0),
            API.getEconomy().catch(() => ({})),
            API.getSkills().catch(() => ({})),
            API.checkHealth().catch(() => ({})),
            API.getAudit(state.user.ownerId).catch(() => ({ transactions: [] })),
        ]);

        state.balance = balance;

        // Update stats
        document.getElementById('stat-balance').textContent = `Ƈ ${balance.toFixed(2)}`;
        document.getElementById('stat-agents').textContent = health.agentsOnline;
        document.getElementById('stat-skills').textContent = health.totalSkills;
        document.getElementById('stat-volume').textContent = `Ƈ ${(economy.total_volume || 0).toFixed(2)}`;

        // Update sidebar balance
        document.getElementById('user-balance-sidebar').textContent = `Ƈ ${balance.toFixed(2)}`;

        // Chart
        if (!earningsChart) {
            earningsChart = new MiniChart('earnings-chart');
        }

        // Build chart from audit data or generate demo data
        const txns = audit?.transactions || [];
        if (txns.length > 0) {
            const chartData = txns.slice(-14).map((tx, i) => ({
                label: tx.timestamp ? new Date(tx.timestamp).toLocaleDateString('es', { day: 'numeric', month: 'short' }) : `#${i + 1}`,
                value: tx.amount,
            }));
            // Make cumulative
            let cum = 0;
            chartData.forEach(d => { cum += d.value; d.value = cum; });
            earningsChart.setData(chartData);
        } else {
            earningsChart.setData(earningsChart.generateDemoData(7));
        }

        // Recent transactions
        renderTransactions('recent-transactions', txns.slice(-6).reverse(), true);
    } catch (error) {
        console.error("Dashboard refresh failed:", error);
    }
}

// ================================================================
// WALLET
// ================================================================

async function refreshWallet() {
    if (!state.user) return;

    try {
        const [balance, audit] = await Promise.all([
            API.getBalance(state.user.ownerId).catch(() => 0),
            API.getAudit(state.user.ownerId).catch(() => ({ transactions: [] })),
        ]);

        state.balance = balance;
        document.getElementById('wallet-balance').textContent = `Ƈ ${balance.toFixed(2)}`;
        document.getElementById('wallet-balance-usd').textContent = `≈ $${(balance * 0.10).toFixed(2)} USD`;
        document.getElementById('user-balance-sidebar').textContent = `Ƈ ${balance.toFixed(2)}`;

        const txns = audit?.transactions || [];
        renderWalletTable('wallet-transactions', txns.reverse());
    } catch (error) {
        console.error("Wallet refresh failed:", error);
    }
}

function renderTransactions(containerId, transactions, compact = false) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!transactions.length) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📜</span>
                <p>Sin transacciones aún</p>
                <p class="empty-sub">Contrata un agente para empezar</p>
            </div>`;
        return;
    }

    container.innerHTML = transactions.map(tx => {
        const isSent = tx.from_owner === state.user?.ownerId;
        const icon = isSent ? '↗️' : '↙️';
        const direction = isSent ? 'sent' : 'received';
        const label = isSent ? `→ ${tx.to_owner}` : `← ${tx.from_owner}`;
        const sign = isSent ? '-' : '+';

        return `
            <div class="tx-item">
                <div class="tx-icon ${direction}">${icon}</div>
                <div class="tx-details">
                    <span class="tx-label">${label}</span>
                    <span class="tx-sub">Job: ${tx.job_id?.slice(0, 8) || 'N/A'}...</span>
                </div>
                <span class="tx-amount ${direction}">${sign}Ƈ ${tx.amount.toFixed(2)}</span>
            </div>`;
    }).join('');
}

function renderWalletTable(containerId, transactions) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!transactions.length) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">💰</span>
                <p>Sin transacciones</p>
            </div>`;
        return;
    }

    container.innerHTML = `
        <table class="tx-table">
            <thead>
                <tr>
                    <th>Tipo</th>
                    <th>De / Para</th>
                    <th>Monto</th>
                    <th>Job ID</th>
                    <th>Fecha</th>
                </tr>
            </thead>
            <tbody>
                ${transactions.map(tx => {
        const isSent = tx.from_owner === state.user?.ownerId;
        const type = isSent ? '↗ Enviada' : '↙ Recibida';
        const party = isSent ? tx.to_owner : tx.from_owner;
        const sign = isSent ? '-' : '+';
        const cls = isSent ? 'sent' : 'received';
        const date = tx.timestamp
            ? new Date(tx.timestamp).toLocaleDateString('es', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
            : 'Reciente';

        return `<tr>
                        <td><span class="tx-amount ${cls}" style="font-size:12px">${type}</span></td>
                        <td>${party}</td>
                        <td class="tx-amount ${cls}">${sign}Ƈ ${tx.amount.toFixed(2)}</td>
                        <td class="mono">${tx.job_id?.slice(0, 12) || 'N/A'}...</td>
                        <td style="color:var(--text-muted)">${date}</td>
                    </tr>`;
    }).join('')}
            </tbody>
        </table>`;
}

// ================================================================
// AGENTS
// ================================================================

async function refreshAgents() {
    if (!state.user) return;

    try {
        const allAgents = await API.discoverAll().catch(() => []);
        const myAgents = allAgents.filter(a => a.owner_id === state.user.ownerId);

        const grid = document.getElementById('my-agents-grid');
        const placeholder = document.getElementById('agent-card-placeholder');

        // Show owned agents
        const existingCards = grid.querySelectorAll('.agent-card:not(.agent-card-empty)');
        existingCards.forEach(c => c.remove());

        if (myAgents.length === 0) {
            if (placeholder) placeholder.style.display = '';
        } else {
            if (placeholder) placeholder.style.display = 'none';
            myAgents.forEach(agent => {
                const skills = agent.skills || [];
                const skill = skills[0] || {};
                const rep = agent.reputation_score || 50;
                const cost = skill.cost_per_call || 0;
                const repStats = agent._rep_stats || {};

                const card = document.createElement('div');
                card.className = 'agent-card';
                card.innerHTML = `
                <div class="agent-card-header">
                    <div class="agent-avatar" style="background:var(--accent-glow)">🤖</div>
                    <div>
                        <div class="agent-name">${agent.agent_name}</div>
                        <div class="agent-skill-badge">${skill.skill_name || 'N/A'}</div>
                    </div>
                </div>
                <div class="agent-stats">
                    <div class="agent-stat">
                        <span class="label">Reputación</span>
                        <span class="value" style="color:var(--accent)">${rep.toFixed(1)}</span>
                    </div>
                    <div class="agent-stat">
                        <span class="label">Precio</span>
                        <span class="value">Ƈ ${cost.toFixed(2)}</span>
                    </div>
                    <div class="agent-stat">
                        <span class="label">Estado</span>
                        <span class="value" style="color:var(--green);font-size:12px">${agent.status || 'online'}</span>
                    </div>
                </div>
                <div class="agent-status-badge online">
                    <span class="dot"></span>
                    <span>En línea — ${agent.api_endpoint || ''}</span>
                </div>`;
                grid.insertBefore(card, placeholder);
            });
        }

        // Also show ALL agents the user could see
        const otherAgents = allAgents.filter(a => a.owner_id !== state.user?.ownerId);
        // (These will show in marketplace)
    } catch (error) {
        console.error("Agents refresh failed:", error);
    }
}

// ================================================================
// MARKETPLACE
// ================================================================

let allMarketAgents = [];
let activeSkillFilter = null;

async function refreshMarketplace() {
    try {
        const [allAgents, skills] = await Promise.all([
            API.discoverAll().catch(() => []),
            API.getSkills().catch(() => ({})),
        ]);

        allMarketAgents = allAgents;

        // Render skill chips
        const chipsContainer = document.getElementById('skills-chips');
        chipsContainer.innerHTML = `
        <button class="skill-chip active" data-skill="all">Todos</button>
        ${(skills.skills || []).map(s => `<button class="skill-chip" data-skill="${s}">${s}</button>`).join('')}
    `;

        chipsContainer.querySelectorAll('.skill-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                chipsContainer.querySelectorAll('.skill-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                const skill = chip.dataset.skill;
                activeSkillFilter = skill === 'all' ? null : skill;
                renderMarketplaceAgents(filterAgents());
            });
        });

        renderMarketplaceAgents(allAgents);

        // Populate hire modal skill select
        const hireSkill = document.getElementById('hire-skill');
        if (hireSkill) {
            hireSkill.innerHTML = `<option value="">Selecciona una habilidad...</option>` +
                (skills.skills || []).map(s => `<option value="${s}">${s}</option>`).join('');
        }
    } catch (error) {
        console.error("Marketplace refresh failed:", error);
    }
}

function filterAgents() {
    let agents = allMarketAgents;
    if (activeSkillFilter) {
        agents = agents.filter(a =>
            (a.skills || []).some(s => s.skill_name === activeSkillFilter)
        );
    }
    const search = document.getElementById('marketplace-search')?.value.toLowerCase() || '';
    if (search) {
        agents = agents.filter(a =>
            a.agent_name.toLowerCase().includes(search) ||
            (a.skills || []).some(s => s.skill_name.toLowerCase().includes(search))
        );
    }
    return agents;
}

function renderMarketplaceAgents(agents) {
    const container = document.getElementById('marketplace-agents');

    if (!agents.length) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1">
                <span class="empty-icon">🌐</span>
                <p>No hay agentes disponibles</p>
                <p class="empty-sub">Publica tus agentes con el SDK o espera a que otros se conecten</p>
            </div>`;
        return;
    }

    container.innerHTML = agents.map(agent => {
        const skills = agent.skills || [];
        const skill = skills[0] || {};
        const rep = agent.reputation_score || 50;
        const cost = skill.cost_per_call || 0;

        return `
            <div class="mp-agent-card" data-agent-id="${agent.agent_id}">
                <div class="mp-header">
                    <div class="mp-avatar">🤖</div>
                    <div>
                        <div class="mp-name">${agent.agent_name}</div>
                        <div class="mp-owner">by ${agent.owner_id}</div>
                    </div>
                </div>
                <div class="agent-skill-badge">${skill.skill_name || 'N/A'}</div>
                <p class="mp-desc">
                    ${agent.description || "Sin descripción disponible."}
                </p>
                <div class="mp-footer">
                    <span class="mp-cost">Ƈ ${cost.toFixed(2)}</span>
                    <div class="mp-rep">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                        ${rep.toFixed(1)}
                    </div>
                    <button class="mp-hire-btn" onclick="hireFromMarketplace('${agent.agent_id}', '${skill.skill_name || ''}', '${agent.api_endpoint || ''}', '${agent.owner_id}')">
                        Contratar
                    </button>
                </div>
            </div>`;
    }).join('');
}

function initMarketplaceSearch() {
    const searchInput = document.getElementById('marketplace-search');
    if (searchInput) {
        let timer;
        searchInput.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => renderMarketplaceAgents(filterAgents()), 200);
        });
    }
}

// ================================================================
// MODALS
// ================================================================

function initModals() {
    // Close modals
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal-overlay').classList.remove('active');
        });
    });
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.classList.remove('active');
        });
    });

    // Deposit modal triggers
    ['btn-add-funds', 'btn-deposit'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', () => openModal('modal-deposit'));
    });

    // Deposit option selection
    document.querySelectorAll('.deposit-option').forEach(opt => {
        opt.addEventListener('click', () => {
            document.querySelectorAll('.deposit-option').forEach(o => o.classList.remove('active'));
            opt.classList.add('active');
        });
    });

    // Confirm deposit
    document.getElementById('btn-confirm-deposit')?.addEventListener('click', async () => {
        const activeOpt = document.querySelector('.deposit-option.active');
        const amount = parseFloat(activeOpt?.dataset.amount || 50);

        // Simulate deposit by adding to account
        if (state.user) {
            await API.createAccount(state.user.ownerId, 0); // ensure exists
            // For demo: we directly create a new account or update balance
            // In production: this would go through Stripe
            const result = await API.createAccount(state.user.ownerId, state.balance + amount);
        }

        closeAllModals();
        await refreshDashboard();
        animateBalanceUpdate();
    });

    // Send job
    document.getElementById('btn-send-job')?.addEventListener('click', async () => {
        await executeHireJob();
    });

    // Enter key to send
    document.getElementById('hire-input')?.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            await executeHireJob();
        }
    });

    // File selection handler
    document.getElementById('hire-file-input')?.addEventListener('change', function (e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function (event) {
            const base64 = event.target.result;
            window._uploadedFile = {
                name: file.name,
                type: file.type,
                size: file.size,
                data: base64
            };

            // Show preview
            const preview = document.getElementById('file-preview');
            const content = document.getElementById('file-preview-content');
            preview.style.display = 'block';

            let previewHtml = '';
            if (file.type.startsWith('image/')) {
                previewHtml = `<img src="${base64}" style="width:40px; height:40px; object-fit:cover; border-radius:6px;">`;
            } else {
                const icon = file.type.includes('pdf') ? '📕' : file.type.includes('word') ? '📘' : '📄';
                previewHtml = `<span style="font-size:24px;">${icon}</span>`;
            }

            content.innerHTML = `
                ${previewHtml}
                <div style="display:flex; flex-direction:column; gap:2px;">
                    <span style="font-size:12px; color:var(--text-primary); font-weight:600; max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${file.name}</span>
                    <span style="font-size:10px; color:var(--text-secondary);">${(file.size / 1024).toFixed(1)} KB</span>
                </div>
            `;
        };
        reader.readAsDataURL(file);
    });
}

function openModal(id) { document.getElementById(id)?.classList.add('active'); }
function closeAllModals() { document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active')); }

// ================================================================
// QUICK ACTIONS
// ================================================================

function initQuickActions() {
    document.querySelectorAll('.quick-action').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            if (action === 'hire') openModal('modal-hire');
            if (action === 'deposit') openModal('modal-deposit');
            if (action === 'publish') navigateTo('agents');
            if (action === 'pipeline') navigateTo('studio');
        });
    });
}

// ================================================================
// HIRE FLOW — Chat-Style with Smart Agent Detection
// ================================================================

let lastJobParams = null;
let jobHistory = JSON.parse(localStorage.getItem('chorus_job_history') || '[]');

function detectBestSkill(userText) {
    const lower = userText.toLowerCase();

    // Weather keywords
    const weatherWords = ['clima', 'weather', 'temperatura', 'pronóstico', 'forecast', 'lluvia', 'rain', 'sol', 'nublado', 'viento', 'wind', 'grados'];
    if (weatherWords.some(w => lower.includes(w)) || lower.startsWith('clima ') || lower.includes('clima en')) {
        return { skill: 'weather', cleaned: lower.replace(/clima (en|de|para)?/i, '').replace(/weather (in|for|at)?/i, '').trim() || userText };
    }

    // Translate keywords
    const translateWords = ['traduc', 'translate', 'traducción', 'translation', 'traducir', 'como se dice'];
    if (translateWords.some(w => lower.includes(w)) || lower.startsWith('translate:') || lower.startsWith('traduce:')) {
        return { skill: 'translate', cleaned: lower.replace(/^(traduc[a-z]*|translate):?\s*/i, '').trim() || userText };
    }

    // Research / Wiki keywords
    const researchWords = ['investiga', 'busca sobre', 'todo sobre', 'qué es', 'quien es', 'quién es', 'historia de', 'wikipedia', 'resumen de', 'research'];
    for (const word of researchWords) {
        if (lower.includes(word)) {
            const regex = new RegExp(word, 'gi');
            return { skill: 'research', cleaned: userText.replace(regex, '').trim() || userText };
        }
    }

    // News keywords
    const newsWords = ['noticia', 'news', 'últimas', 'últimos', 'reciente', 'headline', 'prensa', 'media'];
    if (newsWords.some(w => lower.includes(w)) || lower.startsWith('noticias ') || lower.includes('noticias de')) {
        return { skill: 'news', cleaned: lower.replace(/noticias? (de|sobre|para)?/i, '').replace(/news (about|on|for)?/i, '').trim() || userText };
    }

    // Default: research (Wikipedia)
    return { skill: 'research', cleaned: userText };
}

function getSkillEmoji(skill) {
    const map = { research: '🔍', translate: '🌐', weather: '⛅', news: '📰' };
    return map[skill] || '🤖';
}

function getSkillLabel(skill) {
    const map = { research: 'WikiCloud', translate: 'TranslatorBot', weather: 'WeatherBot', news: 'NewsScanner' };
    return map[skill] || 'Agente';
}

function getAgentWelcome(skill, agentName) {
    const welcomes = {
        research: `¡Hola! 👋 Soy <strong>${agentName || 'WikiCloud'}</strong>, tu agente de investigación.
            <br><br>Escribe cualquier tema y buscaré información detallada en Wikipedia.
            <br><br><strong>Ejemplos:</strong><br>
            🔍 "Bitcoin" — Criptomonedas<br>
            🔍 "Tenerife" — Geografía<br>
            🔍 "Albert Einstein" — Ciencia`,
        translate: `¡Hola! 👋 Soy <strong>${agentName || 'TranslatorBot'}</strong>, tu traductor automático.
            <br><br>Escribe texto en cualquier idioma y lo traduciré automáticamente.
            <br><br><strong>Ejemplos:</strong><br>
            🌐 "Hello world" → Español<br>
            🌐 "Buenos días amigo" → English`,
        weather: `¡Hola! 👋 Soy <strong>${agentName || 'WeatherBot'}</strong>, tu agente del clima.
            <br><br>Escribe el nombre de cualquier ciudad y te daré el clima actual.
            <br><br><strong>Ejemplos:</strong><br>
            ⛅ "Madrid"<br>
            ⛅ "New York"<br>
            ⛅ "Tokio"`,
        news: `¡Hola! 👋 Soy <strong>${agentName || 'NewsScanner'}</strong>, tu buscador de noticias.
            <br><br>Escribe cualquier tema y buscaré las últimas noticias.
            <br><br><strong>Ejemplos:</strong><br>
            📰 "Inteligencia artificial"<br>
            📰 "Fútbol"<br>
            📰 "Economía"`
    };
    return welcomes[skill] || `¡Hola! 👋 Soy <strong>${agentName || 'un agente Chorus'}</strong>. Escribe lo que necesitas y te ayudaré.`;
}

function addChatBubble(type, content) {
    const chatArea = document.getElementById('chat-messages');
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${type}`;
    bubble.innerHTML = `<div class="bubble-content">${content}</div>`;
    bubble.style.animation = 'fadeSlideUp 0.3s ease';
    chatArea.appendChild(bubble);
    chatArea.scrollTop = chatArea.scrollHeight;
    return bubble;
}

function showTypingIndicator() {
    const chatArea = document.getElementById('chat-messages');
    const typing = document.createElement('div');
    typing.className = 'chat-bubble agent';
    typing.id = 'typing-indicator';
    typing.innerHTML = `
        <div class="bubble-content" style="display:flex;gap:4px;padding:8px 12px;">
            <span class="typing-dot" style="animation-delay:0s"></span>
            <span class="typing-dot" style="animation-delay:0.15s"></span>
            <span class="typing-dot" style="animation-delay:0.3s"></span>
        </div>
    `;
    chatArea.appendChild(typing);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

function formatReport(report) {
    if (!report) return '';
    return report
        .replace(/^# (.+)$/gm, '<h3 style="margin:0 0 8px 0;color:#f0f0f5;font-size:15px;">$1</h3>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/^\*(.+)\*$/gm, '<em style="color:#9898aa;">$1</em>')
        .replace(/---/g, '<hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:8px 0;">')
        .replace(/🔗\s*(https?:\/\/\S+)/g, '🔗 <a href="$1" target="_blank" style="color:var(--accent);text-decoration:underline;">Ver artículo completo</a>')
        .replace(/\n/g, '<br>');
}

function addRatingWidget(jobId) {
    const chatArea = document.getElementById('chat-messages');
    const rating = document.createElement('div');
    rating.className = 'chat-bubble agent';
    rating.innerHTML = `
        <div class="bubble-content" style="text-align:center;">
            <div style="font-size:13px;color:var(--text-secondary);margin-bottom:8px;">¿Qué te pareció esta respuesta?</div>
            <div class="star-rating" style="display:flex;gap:4px;justify-content:center;font-size:24px;cursor:pointer;">
                ${[1, 2, 3, 4, 5].map(i => `<span class="star" data-value="${i}" onclick="rateJob('${jobId}', ${i})" 
                    onmouseover="highlightStars(this)" onmouseout="resetStars(this)"
                    style="transition:transform 0.2s;display:inline-block;">☆</span>`).join('')}
            </div>
            <div style="display:flex;gap:8px;justify-content:center;margin-top:10px;">
                <button onclick="retryLastJob()" 
                    style="background:none; border:1px solid var(--accent); color:var(--accent); padding:6px 14px; border-radius:6px; font-size:11px; font-weight:600; cursor:pointer; transition:all 0.2s;">
                    🔄 Reintentar Gratis
                </button>
            </div>
        </div>
    `;
    chatArea.appendChild(rating);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function highlightStars(starEl) {
    const value = parseInt(starEl.dataset.value);
    const stars = starEl.parentElement.querySelectorAll('.star');
    stars.forEach((s, i) => {
        s.textContent = i < value ? '★' : '☆';
        s.style.color = i < value ? '#f59e0b' : '';
        s.style.transform = i < value ? 'scale(1.2)' : 'scale(1)';
    });
}

function resetStars(starEl) {
    const stars = starEl.parentElement.querySelectorAll('.star');
    const rated = starEl.parentElement.dataset.rated;
    if (!rated) {
        stars.forEach(s => {
            s.textContent = '☆';
            s.style.color = '';
            s.style.transform = 'scale(1)';
        });
    }
}

function rateJob(jobId, rating) {
    const allStars = document.querySelectorAll('.star-rating');
    const lastRating = allStars[allStars.length - 1];
    if (lastRating) {
        lastRating.dataset.rated = rating;
        const stars = lastRating.querySelectorAll('.star');
        stars.forEach((s, i) => {
            s.textContent = i < rating ? '★' : '☆';
            s.style.color = i < rating ? '#f59e0b' : '#555';
            s.style.transform = 'scale(1)';
            s.style.cursor = 'default';
            s.onclick = null;
        });
    }

    // Save rating to history
    const job = jobHistory.find(j => j.id === jobId);
    if (job) {
        job.rating = rating;
        localStorage.setItem('chorus_job_history', JSON.stringify(jobHistory));
    }

    const msg = rating >= 4 ? '¡Gracias! 🌟 Me alegra que te haya servido.' :
        rating >= 3 ? 'Gracias por tu feedback. Intentaré mejorar.' :
            '¡Lo siento! Prueba con otro término o usa "🔄 Reintentar Gratis".';

    setTimeout(() => addChatBubble('agent', msg), 500);
}

async function hireFromMarketplace(agentId, skillName, endpoint, ownerId) {
    openModal('modal-hire');

    const agentName = getSkillLabel(skillName);
    const welcomeMsg = getAgentWelcome(skillName, agentName);

    // Reset chat with agent-specific welcome message
    const chatArea = document.getElementById('chat-messages');
    chatArea.innerHTML = `
        <div class="chat-bubble agent">
            <div class="bubble-content">${welcomeMsg}</div>
        </div>
    `;

    // Pre-set skill if coming from marketplace card
    document.getElementById('hire-skill').value = skillName || '';
    document.getElementById('hire-input').value = '';

    // Reset file upload
    const fileInput = document.getElementById('hire-file-input');
    if (fileInput) fileInput.value = '';
    const filePreview = document.getElementById('file-preview');
    if (filePreview) filePreview.style.display = 'none';
    window._uploadedFile = null;

    // Focus input after modal animation
    setTimeout(() => document.getElementById('hire-input').focus(), 400);

    // Update chat header with agent info
    const nameEl = document.getElementById('chat-agent-name');
    const avatarEl = document.getElementById('chat-agent-avatar');
    if (nameEl && skillName) {
        nameEl.textContent = agentName;
        avatarEl.textContent = getSkillEmoji(skillName);
    }

    // Store agent info
    const btn = document.getElementById('btn-send-job');
    btn.dataset.endpoint = endpoint || '';
    btn.dataset.agentOwner = ownerId || '';
    btn.dataset.agentId = agentId || '';
}

async function executeHireJob() {
    const btn = document.getElementById('btn-send-job');
    const userText = document.getElementById('hire-input').value.trim();
    const budget = parseFloat(document.getElementById('hire-budget').value) || 100;

    if (!userText) return;

    // Show user message in chat
    addChatBubble('user', userText);
    document.getElementById('hire-input').value = '';

    // Smart skill detection
    let skill = document.getElementById('hire-skill').value;
    let searchText = userText;

    if (!skill || skill === '') {
        const detected = detectBestSkill(userText);
        skill = detected.skill;
        searchText = detected.cleaned;
    }

    // Update header to show which agent is handling
    const nameEl = document.getElementById('chat-agent-name');
    const avatarEl = document.getElementById('chat-agent-avatar');
    if (nameEl) nameEl.textContent = getSkillLabel(skill);
    if (avatarEl) avatarEl.textContent = getSkillEmoji(skill);

    // Show agent detection message
    addChatBubble('agent', `${getSkillEmoji(skill)} Buscando con <strong>${getSkillLabel(skill)}</strong>...`);

    // Show typing indicator
    showTypingIndicator();
    btn.disabled = true;

    const inputData = { topic: searchText };
    if (window._uploadedFile) {
        inputData.file = window._uploadedFile;
        // Optionally add a mention of the file in the chat
        addChatBubble('user', `📎 Adjunto: ${window._uploadedFile.name}`);
    }

    try {
        // Discover agents with this skill
        const discovered = await API.discover(skill);

        let endpoint, agentOwner;

        if (discovered.agents && discovered.agents.length) {
            const agent = discovered.agents[0];
            endpoint = agent.api_endpoint;
            agentOwner = agent.owner_id;
        } else {
            // Fallback: try direct endpoint
            const fallbackEndpoints = {
                'research': 'https://chorus-ruddy.vercel.app/api/wiki',
                'translate': 'https://chorus-ruddy.vercel.app/api/translate',
                'weather': 'https://chorus-ruddy.vercel.app/api/weather',
                'news': 'https://chorus-ruddy.vercel.app/api/news'
            };
            endpoint = fallbackEndpoints[skill] || fallbackEndpoints['research'];
            agentOwner = '';
        }

        // Save for retry
        lastJobParams = { skill, inputData, endpoint, agentOwner };

        // Send the job
        const result = await API.sendJob(endpoint, skill, inputData, budget);

        removeTypingIndicator();

        // Reset file upload
        window._uploadedFile = null;
        const preview = document.getElementById('file-preview');
        if (preview) preview.style.display = 'none';
        const fileInput = document.getElementById('hire-file-input');
        if (fileInput) fileInput.value = '';

        if (result && result.status === 'SUCCESS') {
            const outputData = result.output_data || {};

            // Process payment
            if (state.user && agentOwner && result.execution_cost > 0) {
                try {
                    await API.transfer(state.user.ownerId, agentOwner, result.execution_cost, result.job_id);
                } catch (e) { /* payment optional */ }
            }

            // Format and display report
            let reportHtml;
            if (outputData.report) {
                reportHtml = formatReport(outputData.report);
                if (outputData.thumbnail) {
                    reportHtml = '<img src="' + outputData.thumbnail + '" style="width:100%;max-width:200px;border-radius:8px;margin-bottom:10px;float:right;margin-left:10px;">' + reportHtml;
                }
            } else if (outputData.error) {
                reportHtml = '⚠️ ' + outputData.error;
            } else {
                reportHtml = '<pre style="font-size:12px;color:#ccc;">' + JSON.stringify(outputData, null, 2) + '</pre>';
            }

            reportHtml += '<div style="margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.06);font-size:11px;color:var(--text-muted);">' +
                '💰 Costo: Ƈ ' + (result.execution_cost || 0).toFixed(0) + ' · ⏱️ ' + (result.execution_time_ms || 0) + 'ms' +
                '</div>';

            addChatBubble('agent', reportHtml);

            // Save to job history
            const jobRecord = {
                id: result.job_id || crypto.randomUUID(),
                skill: skill,
                query: userText,
                agentName: getSkillLabel(skill),
                result: outputData,
                cost: result.execution_cost || 0,
                timestamp: new Date().toISOString(),
                rating: null
            };
            jobHistory.unshift(jobRecord);
            if (jobHistory.length > 50) jobHistory = jobHistory.slice(0, 50);
            localStorage.setItem('chorus_job_history', JSON.stringify(jobHistory));

            // Show rating widget
            addRatingWidget(jobRecord.id);

        } else {
            addChatBubble('agent', '❌ ' + (result && result.error_message ? result.error_message : 'Error al procesar tu solicitud.') +
                '<br><br><button onclick="retryLastJob()" ' +
                'style="background:none; border:1px solid var(--accent); color:var(--accent); padding:6px 14px; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer;">' +
                '🔄 Reintentar</button>');
        }

    } catch (err) {
        removeTypingIndicator();
        addChatBubble('agent', '❌ Error de conexión: ' + err.message);
    }

    btn.disabled = false;
}

async function retryLastJob() {
    if (!lastJobParams) return;

    addChatBubble('user', '🔄 Reintentando...');
    showTypingIndicator();

    const btn = document.getElementById('btn-send-job');
    btn.disabled = true;

    const { skill, inputData, endpoint } = lastJobParams;
    const result = await API.sendJob(endpoint, skill, inputData, 0);

    removeTypingIndicator();

    if (result && result.status === 'SUCCESS') {
        const outputData = result.output_data || {};
        let reportHtml = outputData.report ? formatReport(outputData.report) : JSON.stringify(outputData, null, 2);
        reportHtml += '<div style="margin-top:8px;font-size:11px;color:var(--green);">🆓 Reintento gratuito</div>';
        addChatBubble('agent', reportHtml);
        addRatingWidget(crypto.randomUUID());
    } else {
        addChatBubble('agent', '❌ ' + (result && result.error_message ? result.error_message : 'Reintento fallido'));
    }

    btn.disabled = false;
}

function showHireResult() { /* Legacy - now using chat bubbles */ }

// ================================================================
// UTILS
// ================================================================

function animateBalanceUpdate() {
    const el = document.getElementById('stat-balance');
    if (el) {
        el.style.transition = 'transform 0.3s ease, color 0.3s ease';
        el.style.transform = 'scale(1.1)';
        el.style.color = 'var(--green)';
        setTimeout(() => {
            el.style.transform = 'scale(1)';
            el.style.color = '';
        }, 600);
    }
}

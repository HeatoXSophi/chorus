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
    API.getCurrentUser().then(user => {
        if (user) {
            const name = user.user_metadata.full_name || user.email.split('@')[0];
            loginUserSuccess(user, name);
        }
    });

    // Toggle login/register
    document.getElementById('show-register').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('login-form').classList.remove('active');
        document.getElementById('register-form').classList.add('active');
    });
    document.getElementById('show-login').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('register-form').classList.remove('active');
        document.getElementById('login-form').classList.add('active');
    });

    // Login
    document.getElementById('btn-login').addEventListener('click', async () => {
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value.trim();

        if (!email || !password) { alert('Ingresa email y contraseña'); return; }

        const btn = document.getElementById('btn-login');
        const originalText = btn.innerHTML;
        btn.querySelector('span').textContent = 'Conectando...';
        btn.disabled = true;

        const user = await API.login(email, password);

        if (user._error) {
            alert(`Error: ${user.message}`);
            btn.innerHTML = originalText;
            btn.disabled = false;
        } else {
            const name = user.user_metadata.full_name || email.split('@')[0];
            loginUserSuccess(user, name);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // Register
    document.getElementById('btn-register').addEventListener('click', async () => {
        const name = document.getElementById('reg-name').value.trim() || 'User';
        const email = document.getElementById('reg-email').value.trim();
        const password = document.getElementById('reg-password').value.trim();

        if (!email || !password) { alert('Ingresa todos los campos'); return; }
        if (password.length < 6) { alert('La contraseña debe tener al menos 6 caracteres'); return; }

        const btn = document.getElementById('btn-register');
        const originalText = btn.innerHTML;
        btn.querySelector('span').textContent = 'Creando cuenta...';
        btn.disabled = true;

        const user = await API.register(email, password, name);

        if (user._error) {
            alert(`Error: ${user.message}`);
            btn.innerHTML = originalText;
            btn.disabled = false;
        } else {
            alert('¡Cuenta creada! iniciando sesión...');
            // Auto login logic
            const loggedIn = await API.login(email, password);
            if (!loggedIn._error) {
                loginUserSuccess(loggedIn, name);
            } else {
                // Switch to login
                document.getElementById('register-form').classList.remove('active');
                document.getElementById('login-form').classList.add('active');
            }
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // Logout
    document.getElementById('btn-logout').addEventListener('click', async () => {
        await API.logout();
        state.user = null;
        state.balance = 0;
        state.connected = false;
        document.getElementById('app-screen').classList.remove('active');
        document.getElementById('auth-screen').classList.add('active');
    });
}

async function loginUserSuccess(user, name) {
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
    document.getElementById('user-avatar').textContent = name[0].toUpperCase();
    document.getElementById('user-name-sidebar').textContent = name;

    // Load dashboard
    await refreshDashboard();
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

    // Fetch all data in parallel
    const [balance, economy, skills, health, audit] = await Promise.all([
        API.getBalance(state.user.ownerId),
        API.getEconomy(),
        API.getSkills(),
        API.checkHealth(),
        API.getAudit(state.user.ownerId),
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
}

// ================================================================
// WALLET
// ================================================================

async function refreshWallet() {
    if (!state.user) return;

    const [balance, audit] = await Promise.all([
        API.getBalance(state.user.ownerId),
        API.getAudit(state.user.ownerId),
    ]);

    state.balance = balance;
    document.getElementById('wallet-balance').textContent = `Ƈ ${balance.toFixed(2)}`;
    document.getElementById('wallet-balance-usd').textContent = `≈ $${(balance * 0.10).toFixed(2)} USD`;
    document.getElementById('user-balance-sidebar').textContent = `Ƈ ${balance.toFixed(2)}`;

    const txns = audit?.transactions || [];
    renderWalletTable('wallet-transactions', txns.reverse());
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

    const allAgents = await API.discoverAll();
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
}

// ================================================================
// MARKETPLACE
// ================================================================

let allMarketAgents = [];
let activeSkillFilter = null;

async function refreshMarketplace() {
    const [allAgents, skills] = await Promise.all([
        API.discoverAll(),
        API.getSkills(),
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
    hireSkill.innerHTML = `<option value="">Selecciona una habilidad...</option>` +
        (skills.skills || []).map(s => `<option value="${s}">${s}</option>`).join('');
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
// HIRE FLOW
// ================================================================

async function hireFromMarketplace(agentId, skillName, endpoint, ownerId) {
    openModal('modal-hire');
    const skillSelect = document.getElementById('hire-skill');
    if (skillSelect) skillSelect.value = skillName;
    document.getElementById('hire-input').value = JSON.stringify({ text: "Hello from Chorus Portal!" }, null, 2);

    // Store agent info for the job
    document.getElementById('btn-send-job').dataset.endpoint = endpoint;
    document.getElementById('btn-send-job').dataset.agentOwner = ownerId;
    document.getElementById('btn-send-job').dataset.agentId = agentId;
}

async function executeHireJob() {
    const btn = document.getElementById('btn-send-job');
    const skill = document.getElementById('hire-skill').value;
    const inputRaw = document.getElementById('hire-input').value;
    const budget = parseFloat(document.getElementById('hire-budget').value) || 1.0;

    if (!skill) { alert('Selecciona una habilidad'); return; }

    let inputData;
    try {
        inputData = JSON.parse(inputRaw);
    } catch {
        alert('El JSON de entrada no es válido');
        return;
    }

    btn.querySelector('span').textContent = 'Procesando...';
    btn.disabled = true;

    const resultDiv = document.getElementById('hire-result');
    resultDiv.style.display = 'none';

    // Find an agent for this skill
    const discovered = await API.discover(skill);
    if (!discovered.agents?.length) {
        showHireResult(false, null, 'No se encontró ningún agente con esa habilidad');
        btn.querySelector('span').textContent = 'Enviar Trabajo';
        btn.disabled = false;
        return;
    }

    const agent = discovered.agents[0];
    const endpoint = agent.api_endpoint;
    const agentOwner = agent.owner_id;

    // Send job
    const result = await API.sendJob(endpoint, skill, inputData, budget);

    if (result?.status === 'SUCCESS') {
        // Process payment
        if (state.user && result.execution_cost > 0) {
            await API.transfer(state.user.ownerId, agentOwner, result.execution_cost, result.job_id);
        }
        showHireResult(true, result);
    } else {
        showHireResult(false, result, result?.error_message || 'Trabajo fallido');
    }

    btn.querySelector('span').textContent = 'Enviar Trabajo';
    btn.disabled = false;
}

function showHireResult(success, result, errorMsg = '') {
    const div = document.getElementById('hire-result');
    div.style.display = 'block';

    const statusDiv = document.getElementById('hire-result-status');
    const outputDiv = document.getElementById('hire-result-output');
    const metaDiv = document.getElementById('hire-result-meta');

    if (success) {
        statusDiv.className = 'hire-result-header success';
        statusDiv.textContent = '✅ Trabajo completado exitosamente';
        outputDiv.textContent = JSON.stringify(result.output_data, null, 2);
        metaDiv.innerHTML = `
            <span>Costo: Ƈ ${(result.execution_cost || 0).toFixed(2)}</span>
            <span>Tiempo: ${result.execution_time_ms || 0}ms</span>
            <span>Job: ${(result.job_id || '').slice(0, 12)}...</span>
        `;
    } else {
        statusDiv.className = 'hire-result-header failure';
        statusDiv.textContent = `❌ ${errorMsg}`;
        outputDiv.textContent = result ? JSON.stringify(result, null, 2) : 'Sin respuesta';
        metaDiv.innerHTML = '';
    }
}

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

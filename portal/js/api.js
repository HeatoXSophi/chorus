/**
 * 🎵 Chorus - API Client (Supabase Production Version)
 * Replaces local Python service calls with direct Supabase DB access.
 */

const API = {
    // ── Auth ──────────────────────────────────────────────────

    async login(email, password) {
        const { data, error } = await supabase.auth.signInWithPassword({
            email: email,
            password: password,
        });
        if (error) return { _error: true, message: error.message };
        return data.user;
    },

    async register(email, password, fullName) {
        const { data, error } = await supabase.auth.signUp({
            email: email,
            password: password,
            options: {
                data: {
                    full_name: fullName,
                    avatar_url: `https://ui-avatars.com/api/?name=${fullName}&background=random`
                }
            }
        });
        if (error) return { _error: true, message: error.message };
        return data.user;
    },

    async logout() {
        const { error } = await supabase.auth.signOut();
        return !error;
    },

    async getCurrentUser() {
        const { data: { user } } = await supabase.auth.getUser();
        return user;
    },

    async resendConfirmation(email) {
        const { error } = await supabase.auth.resend({
            type: 'signup',
            email: email,
        });
        if (error) return { success: false, message: error.message };
        return { success: true };
    },

    // ── Health ────────────────────────────────────────────────

    async checkHealth() {
        // Simple ping to DB using a lightweight query
        const { data, error } = await supabase.from('agents').select('count', { count: 'exact', head: true });

        // Also check auth status
        const { data: session } = await supabase.auth.getSession();

        return {
            registryOnline: !error,
            ledgerOnline: !error,
            cloudOnline: true, // Vercel is always up
            agentsOnline: data || 0, // Approximate count
            totalSkills: 0, // Not easily countable without aggregation, skip for now
            isAuthenticated: !!session?.session
        };
    },

    // ── Agents (Registry) ────────────────────────────────────

    async getSkills() {
        const { data, error } = await supabase.from('agents').select('skill');
        if (error) return { skills: [], total_agents: 0 };
        const skills = [...new Set(data.map(a => a.skill))];
        return { skills, total_agents: data.length };
    },

    async discover(skill, minRep = 0) {
        let query = supabase.from('agents').select('*').gte('reputation_score', minRep);
        if (skill) query = query.eq('skill', skill);

        const { data, error } = await query;
        if (error) return { agents: [], total: 0 };

        const mapped = data.map(a => ({
            agent_id: a.id,
            agent_name: a.name,
            owner_id: a.owner_id,
            api_endpoint: a.endpoint,
            reputation_score: a.reputation_score,
            skills: [{ skill_name: a.skill, cost_per_call: a.cost_per_call }]
        }));

        return { agents: mapped, total: mapped.length };
    },

    async discoverAll() {
        return (await this.discover(null)).agents;
    },

    // ── Ledger (Accounts) ────────────────────────────────────

    async createAccount(ownerId, initialBalance = 100) {
        const { data, error } = await supabase.from('ledger_accounts').select('*').eq('owner_id', ownerId).single();
        if (error && error.code === 'PGRST116') return null;
        return data;
    },

    async getBalance(ownerId) {
        const { data, error } = await supabase.from('ledger_accounts').select('balance').eq('owner_id', ownerId).single();
        return data?.balance || 0;
    },

    async getAudit(ownerId = null, limit = 50) {
        let query = supabase.from('transactions').select('*').order('created_at', { ascending: false }).limit(limit);
        const { data, error } = await query;
        if (error) return { transactions: [], total: 0 };

        return {
            transactions: data.map(t => ({
                id: t.id,
                from_owner: t.from_account_id,
                to_owner: t.to_account_id,
                amount: t.amount,
                job_id: t.job_id,
                timestamp: t.created_at
            })),
            total: data.length
        };
    },

    async getEconomy() {
        return { total_accounts: 0, total_volume: 0, total_transactions: 0 };
    },

    async transfer(fromOwner, toOwner, amount, jobId) {
        const { data, error } = await supabase.rpc('transfer_credits', {
            sender_id: fromOwner,
            receiver_id: toOwner,
            amount: amount,
            description: `Payment for job ${jobId}`,
            job_id: jobId
        });
        if (error) {
            console.error("Transfer failed:", error);
            return { success: false, error: error.message };
        }
        return { success: true };
    },

    // ── Jobs (Direct) ────────────────────────────────────────

    async sendJob(agentEndpoint, skillName, inputData, budget) {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;
        try {
            const response = await fetch(`${agentEndpoint}/jobs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    job_id: crypto.randomUUID(),
                    skill_name: skillName,
                    input_data: inputData,
                    budget: budget
                })
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (err) {
            return { status: 'FAILURE', error_message: err.message };
        }
    },

    // ── Studio (Graphs) ──────────────────────────────────────

    studio: {
        async save(name, graphData, id = null) {
            const user = await API.getCurrentUser();
            if (!user) return { error: "Login required" };

            const payload = {
                owner_id: user.id,
                name: name,
                graph_data: graphData,
                updated_at: new Date().toISOString()
            };

            let query;
            if (id) {
                // Update
                query = supabase
                    .from('studio_graphs')
                    .update(payload)
                    .eq('id', id)
                    .select();
            } else {
                // Insert
                query = supabase
                    .from('studio_graphs')
                    .insert(payload)
                    .select();
            }

            const { data, error } = await query;
            if (error) return { error: error.message };
            return { data: data[0] };
        },

        async list() {
            const { data, error } = await supabase
                .from('studio_graphs')
                .select('id, name, updated_at')
                .order('updated_at', { ascending: false });

            if (error) return { error: error.message };
            return { data };
        },

        async load(id) {
            const { data, error } = await supabase
                .from('studio_graphs')
                .select('*')
                .eq('id', id)
                .single();

            if (error) return { error: error.message };
            return { data };
        },

        async delete(id) {
            const { error } = await supabase
                .from('studio_graphs')
                .delete()
                .eq('id', id);

            if (error) return { error: error.message };
            return { success: true };
        }
    }
};

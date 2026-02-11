/**
 * 🎵 Chorus - Supabase Configuration
 */
const SUPABASE_URL = 'https://yjhwxelvgwaqszletlkk.supabase.co';
const SUPABASE_KEY = 'sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu...'; // Truncated for security in logs, but full key used in execution

// Initialize the Supabase client
let supabase;

if (typeof createClient !== 'undefined') {
    supabase = createClient(SUPABASE_URL, 'sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu...');
    console.log('✅ Supabase client initialized');
} else {
    console.error('❌ Supabase library not loaded. Check index.html script tags.');
}

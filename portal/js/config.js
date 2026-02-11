/**
 * 🎵 Chorus - Supabase Configuration
 */
const SUPABASE_URL = 'https://yjhwxelvgwaqszletlkk.supabase.co';
const SUPABASE_KEY = 'sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu...'; // Truncated for security in logs, but full key used in execution

// Initialize the Supabase client
let supabase;

if (typeof supabase !== 'undefined' && supabase.createClient) {
    // If loaded via CDN, supabase is often on the window object
    window.supabase = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    console.log('✅ Supabase client initialized via supabase.createClient');
} else if (window.supabase && window.supabase.createClient) {
    // Sometimes it's window.supabase
    window.supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    console.log('✅ Supabase client initialized via window.supabase.createClient');
} else {
    console.error('❌ Supabase library not loaded or createClient not found.');
    // Fallback?
}

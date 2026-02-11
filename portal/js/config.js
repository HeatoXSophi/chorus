/**
 * 🎵 Chorus - Supabase Configuration
 */
const SUPABASE_URL = 'https://yjhwxelvgwaqszletlkk.supabase.co';
const SUPABASE_KEY = 'sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu'; // Correct key provided by user

// Initialize the Supabase client
// We check for the factory method 'createClient' on the global object
if (window.supabase && window.supabase.createClient) {
    // Overwrite the global 'supabase' object with the initialized Client
    window.supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    console.log('✅ Supabase client initialized.');
} else {
    // Fallback: Check if it's already an initialized client (has .auth)
    if (window.supabase && window.supabase.auth) {
        console.log('ℹ️ Supabase client already initialized.');
    } else {
        console.error('❌ Supabase library not loaded correctly.');
        alert("Error crítico: No se pudo cargar Supabase. Recarga la página.");
    }
}

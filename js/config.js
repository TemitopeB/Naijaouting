/*
 * Supabase connection for the website.
 * Both values are safe to publish: the "anon" key only allows what the access
 * rules in supabase/schema.sql allow. NEVER put the "service_role" key here.
 *
 * Find them in Supabase: Project Settings -> API (or "Connect").
 */
window.NO_CONFIG = {
  supabaseUrl: "",      // e.g. "https://abcdefghijk.supabase.co"
  supabaseAnonKey: ""   // the long "anon" / "publishable" key
};

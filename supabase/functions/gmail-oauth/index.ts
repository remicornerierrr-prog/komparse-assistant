import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CALLBACK = "https://glufyxsdmaccuuqpoxbo.supabase.co/functions/v1/gmail-oauth";
const APP = "https://remicornerierrr-prog.github.io/komparse-assistant/";
const cors = {
  "Access-Control-Allow-Origin": "https://remicornerierrr-prog.github.io",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Vary": "Origin",
};
function back(status: string) {
  const u = new URL(APP); u.searchParams.set("gmail_oauth", status);
  return Response.redirect(u.toString(), 303);
}
function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { ...cors, "Content-Type": "application/json" } });
}
function b64url(bytes: Uint8Array) {
  let s = ""; for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}
async function sha256(value: string) {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("");
}
function keyBytes(raw: string) {
  if (/^[0-9a-fA-F]{64}$/.test(raw)) return new Uint8Array(raw.match(/.{2}/g)!.map(x => parseInt(x, 16)));
  const b = Uint8Array.from(atob(raw), c => c.charCodeAt(0));
  if (b.length !== 32) throw new Error("GMAIL_TOKEN_ENCRYPTION_KEY must encode 32 bytes.");
  return b;
}
async function encrypt(value: string, rawKey: string) {
  const key = await crypto.subtle.importKey("raw", keyBytes(rawKey), { name: "AES-GCM" }, false, ["encrypt"]);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const data = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(value));
  return JSON.stringify({ v: 1, iv: b64url(iv), ciphertext: b64url(new Uint8Array(data)) });
}
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  const url = new URL(req.url);
  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const anon = Deno.env.get("SUPABASE_ANON_KEY");
  const service = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const clientId = Deno.env.get("GOOGLE_OAUTH_CLIENT_ID");
  const clientSecret = Deno.env.get("GOOGLE_OAUTH_CLIENT_SECRET");
  const encryptionKey = Deno.env.get("GMAIL_TOKEN_ENCRYPTION_KEY");
  if (!supabaseUrl || !anon || !service || !clientId || !clientSecret || !encryptionKey) {
    return req.method === "GET" ? back("not_configured") : json({ error: "OAuth server configuration is incomplete." }, 503);
  }
  const admin = createClient(supabaseUrl, service, { auth: { persistSession: false } });
  if (req.method === "GET") {
    const error = url.searchParams.get("error");
    if (error) return back("cancelled");
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    if (!code || !state) return back("invalid_callback");
    const stateHash = await sha256(state);
    const { data: row, error: stateError } = await admin.from("gmail_oauth_states")
      .select("state_hash,user_id,created_at").eq("state_hash", stateHash).maybeSingle();
    if (stateError || !row) return back("invalid_state");
    if (Date.now() - new Date(row.created_at).getTime() > 600000) {
      await admin.from("gmail_oauth_states").delete().eq("state_hash", stateHash);
      return back("expired_state");
    }
    await admin.from("gmail_oauth_states").delete().eq("state_hash", stateHash);
    const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ code, client_id: clientId, client_secret: clientSecret, redirect_uri: CALLBACK, grant_type: "authorization_code" }),
    });
    const tokens = await tokenRes.json();
    if (!tokenRes.ok || !tokens.refresh_token || !tokens.access_token) return back("token_exchange_failed");
    const profileRes = await fetch("https://www.googleapis.com/oauth2/v2/userinfo", { headers: { Authorization: `Bearer ${tokens.access_token}` } });
    const profile = await profileRes.json();
    if (!profileRes.ok || !profile.email) return back("email_lookup_failed");
    let refreshCipher: string, accessCipher: string;
    try {
      refreshCipher = await encrypt(tokens.refresh_token, encryptionKey);
      accessCipher = await encrypt(tokens.access_token, encryptionKey);
    } catch { return back("encryption_failed"); }
    const { error: saveError } = await admin.from("gmail_connections").upsert({
      user_id: row.user_id, gmail_email: profile.email,
      refresh_token_ciphertext: refreshCipher, access_token_ciphertext: accessCipher,
      access_token_expires_at: new Date(Date.now() + Number(tokens.expires_in ?? 3600) * 1000).toISOString(),
      granted_scopes: String(tokens.scope ?? "").split(" ").filter(Boolean),
      connected_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }, { onConflict: "user_id" });
    if (saveError) return back("save_failed");
    return back("connected");
  }
  if (req.method !== "POST") return json({ error: "Method not allowed." }, 405);
  const auth = req.headers.get("Authorization");
  if (!auth?.startsWith("Bearer ")) return json({ error: "Connectez-vous à Komparse d'abord." }, 401);
  const userClient = createClient(supabaseUrl, anon, { global: { headers: { Authorization: auth } }, auth: { persistSession: false } });
  const { data, error } = await userClient.auth.getUser();
  if (error || !data.user) return json({ error: "Session Komparse invalide ou expirée." }, 401);
  const state = b64url(crypto.getRandomValues(new Uint8Array(32)));
  const { error: insertError } = await admin.from("gmail_oauth_states").insert({ state_hash: await sha256(state), user_id: data.user.id });
  if (insertError) return json({ error: "Impossible de démarrer l'autorisation Gmail." }, 500);
  const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authUrl.searchParams.set("client_id", clientId);
  authUrl.searchParams.set("redirect_uri", CALLBACK);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("access_type", "offline");
  authUrl.searchParams.set("prompt", "consent");
  authUrl.searchParams.set("include_granted_scopes", "true");
  authUrl.searchParams.set("scope", "openid email https://www.googleapis.com/auth/gmail.send");
  authUrl.searchParams.set("state", state);
  return json({ authorization_url: authUrl.toString() });
});

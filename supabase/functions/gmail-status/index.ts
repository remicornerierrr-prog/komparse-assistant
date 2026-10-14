import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "https://remicornerierrr-prog.github.io",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Vary": "Origin",
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return json({ error: "Method not allowed." }, 405);

  const auth = req.headers.get("Authorization");
  if (!auth?.startsWith("Bearer ")) return json({ error: "Connectez-vous à Komparse d'abord." }, 401);

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const anon = Deno.env.get("SUPABASE_ANON_KEY");
  const service = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !anon || !service) return json({ error: "Configuration serveur incomplète." }, 503);

  const userClient = createClient(supabaseUrl, anon, {
    global: { headers: { Authorization: auth } },
    auth: { persistSession: false },
  });
  const { data: authData, error: authError } = await userClient.auth.getUser();
  if (authError || !authData.user) return json({ error: "Session Komparse invalide ou expirée." }, 401);

  const admin = createClient(supabaseUrl, service, { auth: { persistSession: false } });
  const { data, error } = await admin.from("gmail_connections")
    .select("gmail_email").eq("user_id", authData.user.id).maybeSingle();

  if (error) {
    console.error("Gmail status lookup failed:", error.message);
    return json({ error: "Impossible de vérifier la connexion Gmail." }, 500);
  }
  return json({ connected: Boolean(data?.gmail_email), email: data?.gmail_email ?? null });
});

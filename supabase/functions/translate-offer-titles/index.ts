import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "https://remicornerierrr-prog.github.io",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
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

  const authorization = req.headers.get("Authorization");
  if (!authorization?.startsWith("Bearer ")) {
    return json({ error: "Connectez-vous à Komparse d'abord." }, 401);
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const googleApiKey = Deno.env.get("GOOGLE_TRANSLATE_API_KEY");
  if (!supabaseUrl || !anonKey || !serviceKey) {
    return json({ error: "Configuration Supabase incomplète." }, 503);
  }
  if (!googleApiKey) {
    return json({ error: "Le service de traduction n'est pas configuré." }, 503);
  }

  try {
    const input = await req.json();
    if (!input || typeof input !== "object") {
      return json({ error: "Requête invalide." }, 400);
    }
    const offerIds: unknown = input.offer_ids;
    const targetLanguage: unknown = input.target_language;
    if (
      !Array.isArray(offerIds) ||
      offerIds.length < 1 ||
      offerIds.length > 50 ||
      !offerIds.every((id) => Number.isSafeInteger(id) && id > 0) ||
      new Set(offerIds).size !== offerIds.length
    ) {
      return json({ error: "Liste d'offres invalide." }, 400);
    }
    if (targetLanguage !== "fr" && targetLanguage !== "en") {
      return json({ error: "Langue cible non prise en charge." }, 400);
    }

    const userClient = createClient(supabaseUrl, anonKey, {
      global: { headers: { Authorization: authorization } },
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data: authData, error: authError } = await userClient.auth.getUser();
    if (authError || !authData.user) {
      return json({ error: "Session Komparse invalide ou expirée." }, 401);
    }

    const admin = createClient(supabaseUrl, serviceKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data: matches, error: matchError } = await admin
      .from("matches")
      .select("offer_id")
      .eq("user_id", authData.user.id)
      .in("offer_id", offerIds);
    if (matchError) {
      console.error("Unable to validate offer access:", matchError.message);
      return json({ error: "Impossible de vérifier l'accès aux offres." }, 500);
    }
    const matchedIds = new Set((matches || []).map((match) => match.offer_id));
    if (offerIds.some((id) => !matchedIds.has(id))) {
      return json({ error: "Une ou plusieurs offres ne sont pas accessibles." }, 403);
    }

    const { data: offers, error: offerError } = await admin
      .from("offers")
      .select("id,title")
      .in("id", offerIds);
    if (offerError) {
      console.error("Unable to load offer titles:", offerError.message);
      return json({ error: "Impossible de charger les titres des offres." }, 500);
    }
    const sourceTitles = offerIds
      .map((id) => offers?.find((offer) => offer.id === id)?.title)
      .filter((title): title is string => typeof title === "string" && Boolean(title.trim()));
    if (sourceTitles.length !== offerIds.length) {
      return json({ error: "Un ou plusieurs titres d'offre sont indisponibles." }, 404);
    }

    const googleResponse = await fetch("https://translation.googleapis.com/language/translate/v2", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": googleApiKey,
      },
      body: JSON.stringify({
        q: sourceTitles,
        source: "de",
        target: targetLanguage,
        format: "text",
      }),
    });
    if (!googleResponse.ok) {
      const providerError = await googleResponse.text();
      console.error("Google Cloud Translation request failed:", providerError);
      return json({ error: "Google Cloud Translation n'a pas pu traduire les titres." }, 502);
    }

    const payload = await googleResponse.json();
    const translatedTitles: unknown = payload?.data?.translations;
    if (
      !Array.isArray(translatedTitles) ||
      translatedTitles.length !== offerIds.length ||
      !translatedTitles.every((item) => typeof item?.translatedText === "string")
    ) {
      console.error("Google Cloud Translation returned an invalid response.");
      return json({ error: "La réponse du service de traduction est invalide." }, 502);
    }

    return json({
      translations: offerIds.map((offerId, index) => ({
        offer_id: offerId,
        title: translatedTitles[index].translatedText,
      })),
    });
  } catch (error) {
    console.error("Offer title translation failed:", error);
    return json({ error: "Impossible de traduire les titres des offres." }, 500);
  }
});

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
  if (!supabaseUrl || !anonKey || !serviceKey) {
    return json({ error: "Configuration Supabase incomplète." }, 503);
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

    const translationRequest = new URLSearchParams();
    for (const title of sourceTitles) {
      translationRequest.append("q", title);
    }
    translationRequest.set("source", "de");
    translationRequest.set("target", targetLanguage);
    translationRequest.set("format", "text");

    let translationResponse: Response;
    try {
      translationResponse = await fetch("https://translate.terraprint.co/translate", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: translationRequest,
        signal: AbortSignal.timeout(15000),
      });
    } catch (error) {
      console.error("LibreTranslate community instance is unavailable:", error);
      return json({ error: "Le service communautaire de traduction est indisponible." }, 502);
    }
    if (!translationResponse.ok) {
      const providerError = await translationResponse.text();
      console.error("LibreTranslate request failed:", providerError);
      return json({ error: "Le service communautaire de traduction n'a pas pu traduire les titres." }, 502);
    }

    const payload = await translationResponse.json();
    const translatedText: unknown = payload?.translatedText;
    const translatedTitles =
      typeof translatedText === "string" && offerIds.length === 1
        ? [translatedText]
        : translatedText;
    if (
      !Array.isArray(translatedTitles) ||
      translatedTitles.length !== offerIds.length ||
      !translatedTitles.every((title) => typeof title === "string" && title.trim())
    ) {
      console.error("LibreTranslate returned an invalid response.");
      return json({ error: "La réponse du service de traduction est invalide." }, 502);
    }

    return json({
      translations: offerIds.map((offerId, index) => ({
        offer_id: offerId,
        title: translatedTitles[index],
      })),
    });
  } catch (error) {
    console.error("Offer title translation failed:", error);
    return json({ error: "Impossible de traduire les titres des offres." }, 500);
  }
});

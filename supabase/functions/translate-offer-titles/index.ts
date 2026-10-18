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

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) &&
    value.every((item): item is string => typeof item === "string" && Boolean(item.trim()));
}

async function translateWithMyMemory(titles: string[], targetLanguage: string) {
  const translations: string[] = [];
  for (let offset = 0; offset < titles.length; offset += 5) {
    const batch = titles.slice(offset, offset + 5);
    const results = await Promise.all(batch.map(async (title) => {
      const url = new URL("https://api.mymemory.translated.net/get");
      url.searchParams.set("q", title);
      url.searchParams.set("langpair", `de|${targetLanguage}`);
      const response = await fetch(url, { signal: AbortSignal.timeout(12000) });
      if (!response.ok) throw new Error(`MyMemory returned HTTP ${response.status}.`);
      const payload = await response.json();
      const translatedTitle: unknown = payload?.responseData?.translatedText;
      if (
        payload?.responseStatus !== 200 ||
        payload?.quotaFinished === true ||
        typeof translatedTitle !== "string" ||
        !translatedTitle.trim()
      ) {
        throw new Error("MyMemory returned no translation.");
      }
      return translatedTitle;
    }));
    translations.push(...results);
  }
  return translations;
}

async function translateWithLibreTranslate(titles: string[], targetLanguage: string) {
  const response = await fetch("https://translate.terraprint.co/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      q: titles,
      source: "de",
      target: targetLanguage,
      format: "text",
    }),
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    throw new Error(`LibreTranslate returned HTTP ${response.status}.`);
  }
  const payload = await response.json();
  const translatedText: unknown = payload?.translatedText;
  const translations =
    typeof translatedText === "string" && titles.length === 1
      ? [translatedText]
      : translatedText;
  if (!isStringArray(translations) || translations.length !== titles.length) {
    throw new Error("LibreTranslate returned an invalid response.");
  }
  return translations;
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

    const sourceTitleByOfferId = new Map<string, string>(
      offerIds.map((offerId, index): [string, string] => [String(offerId), sourceTitles[index]])
    );
    const { data: cachedRows, error: cacheReadError } = await admin
      .from("offer_title_translations")
      .select("offer_id,source_title,translated_title")
      .in("offer_id", offerIds.map(String))
      .eq("target_language", targetLanguage);
    if (cacheReadError) {
      console.error("Unable to read shared offer title translations:", cacheReadError.message);
      return json({ error: "Impossible de charger le cache des traductions." }, 500);
    }

    const translatedByOfferId = new Map<string, string>();
    for (const row of cachedRows || []) {
      if (
        row.source_title === sourceTitleByOfferId.get(row.offer_id) &&
        typeof row.translated_title === "string" &&
        row.translated_title.trim()
      ) {
        translatedByOfferId.set(row.offer_id, row.translated_title);
      }
    }

    const missingIndices = offerIds
      .map((_, index) => index)
      .filter((index) => !translatedByOfferId.has(String(offerIds[index])));
    let cachePersisted = true;
    if (missingIndices.length) {
      const missingTitles = missingIndices.map((index) => sourceTitles[index]);
      let translatedMissingTitles: string[];
      try {
        translatedMissingTitles = await translateWithMyMemory(missingTitles, targetLanguage);
      } catch (error) {
        console.warn("MyMemory translation failed; trying LibreTranslate:", error);
        try {
          translatedMissingTitles = await translateWithLibreTranslate(missingTitles, targetLanguage);
        } catch (fallbackError) {
          console.error("Both translation providers failed:", fallbackError);
          return json({ error: "Les services de traduction sont indisponibles." }, 502);
        }
      }

      const cacheRows = missingIndices.map((index, translatedIndex) => {
        const offerId = String(offerIds[index]);
        const translatedTitle = translatedMissingTitles[translatedIndex];
        translatedByOfferId.set(offerId, translatedTitle);
        return {
          offer_id: offerId,
          target_language: targetLanguage,
          source_title: sourceTitles[index],
          translated_title: translatedTitle,
          updated_at: new Date().toISOString(),
        };
      });
      const { error: cacheWriteError } = await admin
        .from("offer_title_translations")
        .upsert(cacheRows, { onConflict: "offer_id,target_language" });
      if (cacheWriteError) {
        cachePersisted = false;
        console.error("Unable to persist shared offer title translations:", cacheWriteError.message);
      }
    }

    return json({
      translations: offerIds.map((offerId, index) => ({
        offer_id: offerId,
        title: translatedByOfferId.get(String(offerId)) || sourceTitles[index],
      })),
      cache_persisted: cachePersisted,
    });
  } catch (error) {
    console.error("Offer title translation failed:", error);
    return json({ error: "Impossible de traduire les titres des offres." }, 500);
  }
});

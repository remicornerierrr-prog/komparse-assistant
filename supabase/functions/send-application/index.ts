import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": Deno.env.get("APP_ORIGIN") ?? "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function requiredEnv(name: string): string {
  const value = Deno.env.get(name);
  if (!value) throw new Error(`Missing server configuration: ${name}`);
  return value;
}

function base64(bytes: Uint8Array): string {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  try {
    const authorization = req.headers.get("Authorization");
    if (!authorization?.startsWith("Bearer ")) return json({ error: "Authentication required" }, 401);

    const supabaseUrl = requiredEnv("SUPABASE_URL");
    const anonKey = requiredEnv("SUPABASE_ANON_KEY");
    const resendKey = requiredEnv("RESEND_API_KEY");
    const fromEmail = requiredEnv("RESEND_FROM_EMAIL");

    const supabase = createClient(supabaseUrl, anonKey, {
      global: { headers: { Authorization: authorization } },
      auth: { persistSession: false, autoRefreshToken: false },
    });

    const { data: userData, error: userError } = await supabase.auth.getUser();
    if (userError || !userData.user) return json({ error: "Invalid session" }, 401);
    const userId = userData.user.id;

    const body = await req.json();
    const offerId = Number(body.offer_id);
    if (!Number.isSafeInteger(offerId) || offerId <= 0) return json({ error: "Invalid offer_id" }, 400);
    if (body.confirm !== true) return json({ error: "Explicit confirmation required" }, 400);

    const { data: match, error: matchError } = await supabase
      .from("matches").select("id").eq("user_id", userId).eq("offer_id", offerId).maybeSingle();
    if (matchError) throw matchError;
    if (!match) return json({ error: "Offer not matched to this user" }, 403);

    const { data: offer, error: offerError } = await supabase
      .from("offers")
      .select("id,title,email,subject_keyword,shoot_date,shoot_date_text,source_url,detail_text,raw_text,application_method,application_url")
      .eq("id", offerId).maybeSingle();
    if (offerError) throw offerError;
    if (!offer) return json({ error: "Offer not found" }, 404);
    if (!offer.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(offer.email)) {
      return json({ error: "This offer has no valid application email address" }, 422);
    }

    const { data: profile, error: profileError } = await supabase
      .from("profiles").select("first_name,last_name,email,phone,birth_date,city,height_cm,shoe_size,clothing_size")
      .eq("id", userId).maybeSingle();
    if (profileError) throw profileError;
    if (!profile) return json({ error: "Complete your profile before applying" }, 422);

    const { data: photos, error: photosError } = await supabase
      .from("profile_photos").select("photo_type,storage_path").eq("user_id", userId);
    if (photosError) throw photosError;
    if (!photos?.length) return json({ error: "Upload profile photos before applying" }, 422);

    const photoNames: Record<string, string> = {
      portrait: "portrait", left: "blick-links", right: "blick-rechts", full_body: "ganzkoerper",
    };
    const attachments: Array<{ filename: string; content: string }> = [];
    let totalBytes = 0;
    for (const photo of photos) {
      const { data: blob, error: downloadError } = await supabase.storage
        .from("profile-photos").download(photo.storage_path);
      if (downloadError || !blob) throw new Error("Unable to retrieve one of your profile photos");
      totalBytes += blob.size;
      if (blob.size > 5 * 1024 * 1024 || totalBytes > 15 * 1024 * 1024) {
        return json({ error: "Photo attachments exceed the allowed email size" }, 413);
      }
      const bytes = new Uint8Array(await blob.arrayBuffer());
      const ext = blob.type === "image/png" ? "png" : blob.type === "image/webp" ? "webp" : "jpg";
      attachments.push({
        filename: `${photoNames[photo.photo_type] ?? "profilfoto"}.${ext}`,
        content: base64(bytes),
      });
    }

    const fullName = [profile.first_name, profile.last_name].filter(Boolean).join(" ");
    const shootDate = offer.shoot_date_text || offer.shoot_date || "";
    const subject = offer.subject_keyword?.trim() || (shootDate ? `Bewerbung Komparse ${shootDate}` : "Bewerbung Komparse");
    const text = [
      "Hallo,", "",
      `ich möchte mich gerne für den Einsatz als Komparse${shootDate ? ` am ${shootDate}` : ""} bewerben.`, "",
      "Nachfolgend finden Sie meine Angaben:", "",
      `Vollständiger Name: ${fullName}`,
      `Wohnort: ${profile.city || ""}`,
      `Telefon: ${profile.phone || ""}`,
      `Geburtsdatum: ${profile.birth_date || ""}`,
      `Kleidergröße: ${profile.clothing_size || ""}`,
      `Größe: ${profile.height_cm ?? ""} cm`,
      `Schuhgröße: ${profile.shoe_size || ""}`, "",
      "Vielen Dank.", "", "Mit freundlichen Grüßen,", fullName,
    ].join("\n");

    const resendResponse = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${resendKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ from: fromEmail, to: [offer.email], subject, text, attachments }),
    });
    const resendResult = await resendResponse.json().catch(() => ({}));
    if (!resendResponse.ok) {
      console.error("Resend rejected application", resendResponse.status, resendResult);
      return json({ error: "Email provider rejected the application. No success was recorded." }, 502);
    }

    return json({ success: true, email_id: resendResult.id, recipient: offer.email, subject });
  } catch (error) {
    console.error("send-application error", error);
    return json({ error: "Unable to send application. Please try again later." }, 500);
  }
});

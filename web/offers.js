/* Mes offres et détail — aucune donnée Komparse n'est injectée via innerHTML. */
(function () {
  const SUPABASE_URL = "https://glufyxsdmaccuuqpoxbo.supabase.co";
  const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_RdYDH-Ez9SGoLxMaKceXsQ_KQPQmwBu";
  const client = window.supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
  const root = document.getElementById("offers-root");
  if (!root) return;

  function node(tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined && text !== null) el.textContent = String(text);
    if (className) el.className = className;
    return el;
  }
  function field(parent, label, value) {
    const p = node("p");
    const strong = node("strong", label + ": ");
    p.append(strong, document.createTextNode(value || "Non précisé"));
    parent.append(p);
  }
  function safeSourceLink(url) {
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== "https:" || parsed.hostname !== "komparse.de") return null;
      return parsed.href;
    } catch (_) { return null; }
  }
  function offerTitle(offer) { return offer.title || "Offre Komparse"; }

  async function init() {
    const { data: userResult, error: authError } = await client.auth.getUser();
    if (authError || !userResult.user) {
      root.append(node("p", "Connectez-vous pour consulter vos offres."));
      return;
    }
    const user = userResult.user;
    const offerId = new URLSearchParams(location.search).get("id");
    if (offerId) return showDetail(user.id, offerId);
    return showList(user.id);
  }

  async function showList(userId) {
    root.append(node("h2", "Mes offres"));
    const { data: matches, error } = await client.from("matches")
      .select("id,offer_id,created_at,offers(id,title,location_text,shoot_date,shoot_date_text,age_description,source_url)")
      .eq("user_id", userId).order("created_at", { ascending: false });
    if (error) {
      root.append(node("p", "Impossible de charger vos offres. Réessayez plus tard."));
      console.error("Erreur Mes offres", error);
      return;
    }
    if (!matches || matches.length === 0) {
      root.append(node("p", "Aucune offre ne correspond encore à votre profil."));
      return;
    }
    for (const match of matches) {
      const offer = match.offers;
      if (!offer) continue;
      const card = node("article", undefined, "offer-card");
      card.append(node("h3", offerTitle(offer)));
      field(card, "Lieu", offer.location_text);
      field(card, "Tournage", offer.shoot_date_text || offer.shoot_date);
      field(card, "Âge", offer.age_description || formatAge(offer));
      const link = node("a", "Voir le détail");
      link.href = "./offers.html?id=" + encodeURIComponent(String(offer.id));
      card.append(link);
      root.append(card);
    }
  }

  function formatAge(offer) {
    if (offer.age_min != null && offer.age_max != null) return offer.age_min + "–" + offer.age_max + " ans";
    if (offer.age_min != null) return offer.age_min + " ans minimum";
    if (offer.age_max != null) return offer.age_max + " ans maximum";
    return "Non précisé";
  }

  async function showDetail(userId, offerId) {
    const numericId = Number(offerId);
    if (!Number.isSafeInteger(numericId) || numericId <= 0) {
      root.append(node("p", "Identifiant d'offre invalide."));
      return;
    }
    const { data: match, error: matchError } = await client.from("matches")
      .select("id").eq("user_id", userId).eq("offer_id", numericId).maybeSingle();
    if (matchError || !match) {
      root.append(node("p", "Cette offre n'est pas disponible dans vos correspondances."));
      return;
    }
    const { data: offer, error } = await client.from("offers")
      .select("id,title,location_text,shoot_date,shoot_date_text,age_min,age_max,age_description,detail_text,raw_text,source_url,email,subject_keyword,application_method,application_url")
      .eq("id", numericId).maybeSingle();
    if (error || !offer) {
      root.append(node("p", "Impossible de charger le détail de cette offre."));
      return;
    }
    root.append(node("a", "← Retour à Mes offres", "back-link"));
    root.append(node("h2", offerTitle(offer)));
    field(root, "Lieu", offer.location_text);
    field(root, "Date de tournage", offer.shoot_date_text || offer.shoot_date);
    field(root, "Âge demandé", offer.age_description || formatAge(offer));
    const description = offer.detail_text || offer.raw_text || "Aucune description disponible.";
    const desc = node("section", undefined, "description");
    desc.append(node("h3", "Description"), node("p", description));
    root.append(desc);
    const source = safeSourceLink(offer.source_url);
    if (source) {
      const a = node("a", "Voir l'annonce originale sur Komparse");
      a.href = source;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      root.append(a);
    }
    const apply = node("button", "Préparer et envoyer ma candidature");
    apply.type = "button";
    apply.addEventListener("click", () => showApplicationConfirmation(offer, apply));
    root.append(apply);
    root.append(node("p", "Votre email sera envoyé uniquement après confirmation. Vérifiez les photos de votre profil avant l'envoi."));
  }

  async function showApplicationConfirmation(offer, button) {
    if (!offer.email) {
      alert("Cette annonce ne contient pas d'adresse email de candidature. Consultez l'annonce originale.");
      return;
    }
    const confirmPanel = node("section", undefined, "confirm-panel");
    confirmPanel.append(node("h3", "Confirmer l'envoi"));
    field(confirmPanel, "Destinataire", offer.email);
    field(confirmPanel, "Objet", offer.subject_keyword || ("Bewerbung Komparse " + (offer.shoot_date_text || offer.shoot_date || "")));
    confirmPanel.append(node("p", "Les photos enregistrées dans votre profil seront jointes à l'email."));
    const consentLabel = node("label");
    const consent = document.createElement("input");
    consent.type = "checkbox";
    consentLabel.append(consent, document.createTextNode(" Je confirme l'envoi de cette candidature et le partage de mes données et photos avec le destinataire."));
    confirmPanel.append(consentLabel);
    const send = node("button", "Confirmer et envoyer");
    send.type = "button";
    send.disabled = true;
    consent.addEventListener("change", () => { send.disabled = !consent.checked; });
    send.addEventListener("click", async () => {
      if (!consent.checked) return;
      send.disabled = true;
      send.textContent = "Envoi en cours…";
      const { data: sessionData } = await client.auth.getSession();
      const token = sessionData.session && sessionData.session.access_token;
      if (!token) {
        send.textContent = "Session expirée — reconnectez-vous";
        return;
      }
      try {
        const response = await fetch(SUPABASE_URL + "/functions/v1/send-application", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token, "apikey": SUPABASE_PUBLISHABLE_KEY },
          body: JSON.stringify({ offer_id: offer.id, confirm: true })
        });
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.error || "Échec de l'envoi");
        send.textContent = "Email envoyé";
        confirmPanel.append(node("p", "Candidature envoyée à " + result.recipient + "."));
      } catch (error) {
        send.disabled = false;
        send.textContent = "Réessayer l'envoi";
        confirmPanel.append(node("p", error.message || "L'envoi a échoué. Aucun succès n'a été confirmé."));
      }
    });
    const cancel = node("button", "Annuler");
    cancel.type = "button";
    cancel.addEventListener("click", () => confirmPanel.remove());
    confirmPanel.append(send, cancel);
    button.after(confirmPanel);
    button.disabled = true;
  }

  init().catch(error => {
    console.error(error);
    root.append(node("p", "Une erreur inattendue est survenue."));
  });
})();

/* Mes offres et détail — aucune donnée Komparse n'est injectée via innerHTML. */
(function () {
  const SUPABASE_URL = "https://glufyxsdmaccuuqpoxbo.supabase.co";
  const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_RdYDH-Ez9SGoLxMaKceXsQ_KQPQmwBu";
  const client = window.supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
  const root = document.getElementById("offers-root");
  if (!root) return;
  const titleTranslations = new Map();
  let visibleTitles = [];
  let titleRenderVersion = 0;

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
  function currentLanguage() {
    try {
      const saved = localStorage.getItem("komparse-language");
      return saved === "de" || saved === "en" ? saved : "fr";
    } catch (error) {
      console.error("Impossible de lire la langue de l’interface.", error);
      return document.documentElement.lang === "de" || document.documentElement.lang === "en"
        ? document.documentElement.lang
        : "fr";
    }
  }

  function translationUnavailableText(language) {
    if (language === "de") return "";
    if (language === "en") return "Translation unavailable; showing the original title.";
    return "Traduction indisponible ; le titre original est affiché.";
  }

  function setOfferTitle(element, offer, translation, language, unavailable = false) {
    const original = offerTitle(offer);
    element.replaceChildren(node("span", translation || original, "offer-title-primary"));
    if (language === "de") return;

    if (translation && translation !== original) {
      element.append(node("small", original, "offer-title-original"));
    } else if (unavailable) {
      element.append(node("small", translationUnavailableText(language), "offer-title-translation-status"));
    }
  }

  async function updateOfferTitles() {
    const language = currentLanguage();
    const renderVersion = ++titleRenderVersion;

    for (const entry of visibleTitles) {
      const cached = titleTranslations.get(`${language}:${entry.offer.id}`);
      setOfferTitle(entry.element, entry.offer, cached, language);
    }
    if (language === "de") return;

    const missing = visibleTitles.filter(
      ({ offer }) => !titleTranslations.has(`${language}:${offer.id}`)
    );
    if (!missing.length) return;

    try {
      for (let offset = 0; offset < missing.length; offset += 50) {
        const batch = missing.slice(offset, offset + 50);
        const { data, error } = await client.functions.invoke("translate-offer-titles", {
          body: {
            offer_ids: batch.map(({ offer }) => offer.id),
            target_language: language,
          },
        });
        if (error) throw error;
        if (!data || !Array.isArray(data.translations)) {
          throw new Error("La réponse de traduction des titres est invalide.");
        }
        for (const result of data.translations) {
          if (
            Number.isSafeInteger(result.offer_id) &&
            typeof result.title === "string" &&
            result.title.trim()
          ) {
            titleTranslations.set(`${language}:${result.offer_id}`, result.title);
          }
        }
      }
    } catch (error) {
      console.error("Impossible de traduire les titres des offres.", error);
      if (renderVersion !== titleRenderVersion) return;
      for (const entry of visibleTitles) {
        if (currentLanguage() !== language) return;
        const cached = titleTranslations.get(`${language}:${entry.offer.id}`);
        setOfferTitle(entry.element, entry.offer, cached, language, !cached);
      }
      return;
    }

    if (renderVersion !== titleRenderVersion || currentLanguage() !== language) return;
    for (const entry of visibleTitles) {
      setOfferTitle(
        entry.element,
        entry.offer,
        titleTranslations.get(`${language}:${entry.offer.id}`),
        language,
        true
      );
    }
  }

  document.addEventListener("komparse:languagechange", () => {
    updateOfferTitles();
  });

  async function init() {
    const kicker = node("p", "À L’AFFICHE POUR VOUS", "offers-kicker");
    kicker.setAttribute("data-i18n", "À L’AFFICHE POUR VOUS");
    root.append(kicker);

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
      .select("id,offer_id,created_at,offers(id,title,location_text,shoot_date,shoot_date_text,age_min,age_max,age_description,source_url)")
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
      const title = node("h3");
      setOfferTitle(title, offer, null, currentLanguage());
      card.append(title);
      visibleTitles.push({ offer, element: title });
      field(card, "Lieu", offer.location_text);
      field(card, "Tournage", offer.shoot_date_text || offer.shoot_date);
      field(card, "Âge", offer.age_description || formatAge(offer));
      const link = node("a", "Voir le détail");
      link.href = "./offers.html?id=" + encodeURIComponent(String(offer.id));
      card.append(link);
      root.append(card);
    }
    await updateOfferTitles();
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
    const backLink = node("a", "← Retour à Mes offres", "back-link");
    backLink.href = "./offers.html";
    root.append(backLink);
    const title = node("h2");
    setOfferTitle(title, offer, null, currentLanguage());
    root.append(title);
    visibleTitles = [{ offer, element: title }];
    await updateOfferTitles();
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
    confirmPanel.append(node("h3", "Préparer votre candidature"));
    confirmPanel.append(node("p", "Chargement du brouillon et des photos…"));
    button.after(confirmPanel);
    button.disabled = true;

    const { data: sessionData } = await client.auth.getSession();
    const token = sessionData.session && sessionData.session.access_token;
    if (!token) {
      confirmPanel.replaceChildren(node("p", "Session expirée — reconnectez-vous."));
      button.disabled = false;
      return;
    }
    try {
      const response = await fetch(SUPABASE_URL + "/functions/v1/gmail-send-application", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token, "apikey": SUPABASE_PUBLISHABLE_KEY },
        body: JSON.stringify({ action: "preview", offer_id: offer.id })
      });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || "Impossible de préparer la candidature.");

      confirmPanel.replaceChildren(node("h3", "Relire votre candidature"));
      field(confirmPanel, "Votre adresse Gmail", result.sender);
      field(confirmPanel, "Destinataire", result.recipient);

      const subjectLabel = node("label", "Objet de l'email");
      const subjectInput = document.createElement("input");
      subjectInput.type = "text";
      subjectInput.maxLength = 250;
      subjectInput.value = result.subject || "";
      subjectInput.style.display = "block";
      subjectInput.style.width = "100%";
      subjectInput.style.boxSizing = "border-box";
      subjectInput.style.margin = "6px 0 12px";
      subjectLabel.append(subjectInput);
      confirmPanel.append(subjectLabel);

      const bodyLabel = node("label", "Message (modifiable)");
      const bodyInput = document.createElement("textarea");
      bodyInput.rows = 12;
      bodyInput.maxLength = 12000;
      bodyInput.value = result.body || "";
      bodyInput.style.display = "block";
      bodyInput.style.width = "100%";
      bodyInput.style.boxSizing = "border-box";
      bodyInput.style.margin = "6px 0 12px";
      bodyLabel.append(bodyInput);
      confirmPanel.append(bodyLabel);

      const photosText = result.photos && result.photos.length
        ? "Photos jointes : " + result.photos.join(", ")
        : "Aucune photo détectée.";
      confirmPanel.append(node("p", photosText));

      if (Array.isArray(result.photo_previews) && result.photo_previews.length) {
        const photoGallery = node("div", undefined, "application-photo-previews");
        photoGallery.style.display = "flex";
        photoGallery.style.flexWrap = "wrap";
        photoGallery.style.gap = "12px";
        photoGallery.style.margin = "12px 0";
        for (const photo of result.photo_previews) {
          if (!photo || typeof photo.url !== "string") continue;
          let photoUrl;
          try {
            photoUrl = new URL(photo.url);
            if (photoUrl.protocol !== "https:" || photoUrl.hostname !== "glufyxsdmaccuuqpoxbo.supabase.co") continue;
          } catch (_) { continue; }
          const figure = node("figure", undefined, "application-photo-preview");
          figure.style.margin = "0";
          const img = document.createElement("img");
          img.src = photoUrl.href;
          img.alt = "Aperçu de la photo " + String(photo.name || "de profil");
          img.loading = "lazy";
          img.style.width = "120px";
          img.style.height = "150px";
          img.style.objectFit = "contain";
          img.style.borderRadius = "6px";
          img.addEventListener("error", () => {
            figure.replaceChildren(node("p", "Aperçu indisponible : " + String(photo.name || "photo")));
          }, { once: true });
          figure.append(img, node("figcaption", String(photo.name || "Photo de profil")));
          photoGallery.append(figure);
        }
        if (photoGallery.childElementCount) confirmPanel.append(photoGallery);
      }

      confirmPanel.append(node("p", "Vérifiez le destinataire, l'objet, le message et les photos avant l'envoi."));

      const consentLabel = node("label");
      const consent = document.createElement("input");
      consent.type = "checkbox";
      consentLabel.append(consent, document.createTextNode(" Je confirme l'envoi de cette candidature et le partage de mes données et photos avec ce destinataire."));
      confirmPanel.append(consentLabel);

      const send = node("button", "Envoyer depuis mon Gmail");
      send.type = "button";
      send.disabled = true;
      consent.addEventListener("change", () => { send.disabled = !consent.checked; });
      send.addEventListener("click", async () => {
        if (!consent.checked) return;
        send.disabled = true;
        send.textContent = "Envoi en cours…";
        try {
          const sendResponse = await fetch(SUPABASE_URL + "/functions/v1/gmail-send-application", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token, "apikey": SUPABASE_PUBLISHABLE_KEY },
            body: JSON.stringify({ action: "send", offer_id: offer.id, confirm: true, subject: subjectInput.value, body: bodyInput.value })
          });
          const sent = await sendResponse.json();
          if (!sendResponse.ok || !sent.success) throw new Error(sent.error || "Échec de l'envoi.");
          confirmPanel.replaceChildren(
            node("h3", "🙌 Candidature envoyée !"),
            node("p", "Candidature envoyée depuis " + sent.sender + " à " + sent.recipient + ".", "success-message")
          );
        } catch (error) {
          send.disabled = false;
          send.textContent = "Réessayer l'envoi";
          confirmPanel.append(node("p", error.message || "L'envoi a échoué. Aucun succès n'a été confirmé."));
        }
      });
      const cancel = node("button", "Annuler");
      cancel.type = "button";
      cancel.addEventListener("click", () => { confirmPanel.remove(); button.disabled = false; });
      confirmPanel.append(send, cancel);
    } catch (error) {
      confirmPanel.replaceChildren(node("p", error.message || "Impossible de préparer la candidature."));
      const close = node("button", "Fermer");
      close.type = "button";
      close.addEventListener("click", () => { confirmPanel.remove(); button.disabled = false; });
      confirmPanel.append(close);
    }
  }

  init().catch(error => {
    console.error(error);
    root.append(node("p", "Une erreur inattendue est survenue."));
  });
})();

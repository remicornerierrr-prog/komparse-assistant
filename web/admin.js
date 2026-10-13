// ============================================================
// KOMPARSE ASSISTANT — DASHBOARD ADMIN
// ============================================================

// Utiliser uniquement la clé publique/publishable.
// Ne jamais mettre SUPABASE_SECRET_KEY ici.

const SUPABASE_URL = "https://glufyxsdmaccuuqpoxbo.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_RdYDH-Ez9SGoLxMaKceXsQ_KQPQmwBu";

const supabaseClient = window.supabase.createClient(
    SUPABASE_URL,
    SUPABASE_ANON_KEY
);

// ============================================================
// ÉLÉMENTS HTML
// ============================================================

const adminApp = document.getElementById("admin-app");
const adminError = document.getElementById("admin-error");
const adminUserEmail = document.getElementById("admin-user-email");
const offersCount = document.getElementById("offers-count");
const matchesCount = document.getElementById("matches-count");
const notificationsCount = document.getElementById("notifications-count");
const reviewCount = document.getElementById("review-count");
const reviewOffersBody = document.getElementById("review-offers-body");
const offersBody = document.getElementById("offers-body");
const qualificationModal = document.getElementById("qualification-modal");
const qualificationForm = document.getElementById("qualification-form");
const qualificationOfferId = document.getElementById("qualification-offer-id");
const qualificationSource = document.getElementById("qualification-source");
const qualificationValidation = document.getElementById("qualification-validation");
const offersById = new Map();
let editingOfferId = null;

// ============================================================
// AFFICHER UNE ERREUR
// ============================================================

function showError(message) {
    adminError.textContent = message;
    adminError.classList.remove("admin-hidden");
}

// ============================================================
// ÉCHAPPER LE HTML
// ============================================================

function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

// ============================================================
// LIEN VERS L'ANNONCE ORIGINALE KOMPARSE
// ============================================================

function renderOfferReference(offer) {
    const reference = escapeHtml(offer.komparse_id || offer.id || "—");
    const rawUrl = String(offer.source_url || "").trim();

    if (!rawUrl) {
        return reference;
    }

    try {
        const url = new URL(rawUrl);
        // Les liens sources attendus sont les pages publiques de Komparse.
        if (url.protocol !== "https:" || url.hostname.toLowerCase() !== "komparse.de") {
            return reference;
        }

        return `<a href="${escapeHtml(url.href)}" target="_blank" rel="noopener noreferrer" title="Ouvrir l’annonce originale Komparse">${reference} ↗</a>`;
    } catch {
        return reference;
    }
}

// ============================================================
// FORMATER UNE DATE
// ============================================================

function formatDate(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return escapeHtml(value);
    }

    // Komparse affiche l'heure locale allemande dans ses annonces.
    // La valeur importée est stockée avec un suffixe UTC, mais son heure
    // représente déjà l'heure locale source : ne pas appliquer le fuseau
    // horaire du navigateur une seconde fois.
    return date.toLocaleString("fr-FR", {
        dateStyle: "short",
        timeStyle: "short",
        timeZone: "UTC"
    });
}

// ============================================================
// FORMATER LE SEXE
// ============================================================

function formatGender(offer) {
    const genders = [];

    if (offer.gender_male) {
        genders.push("H");
    }

    if (offer.gender_female) {
        genders.push("F");
    }

    if (genders.length === 0) {
        return "Non précisé";
    }

    return genders.join(" / ");
}

// ============================================================
// DÉTECTER UNE DESCRIPTION EXPLICITE D'ÂGES VARIÉS
// ============================================================

function hasExplicitAgeDescription(offer) {
    const text = [
        offer.title || "",
        offer.detail_text || "",
        offer.raw_text || "",
        offer.age_description || ""
    ]
        .join(" ")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase();

    const patterns = [
        /\bgemischtes\s+alter\b/,
        /\bgemischte[nr]?\s+altersgruppen\b/,
        /\baltersgemischt\b/,
        /\bverschiedene\s+altersgruppen\b/,
        /\balle\s+altersgruppen\b/,
        /\bmenschen\s+jeden\s+alters\b/,
        /\bjeden\s+alters\b/,
        /\baltersgruppen\s+gemischt\b/
    ];

    return patterns.some(pattern => pattern.test(text)) ||
        Boolean(String(offer.age_description || "").trim());
}

// ============================================================
// FORMATER L'ÂGE
// ============================================================

function formatAge(offer) {
    const min = offer.age_min;
    const max = offer.age_max;

    if (min == null && max == null) {
        const hasVariedAge = hasExplicitAgeDescription({
            ...offer,
            age_description: ""
        });
        if (hasVariedAge) {
            return "Âges variés";
        }
        if (offer.age_description) {
            return String(offer.age_description);
        }
        return "Non précisé";
    }

    if (min != null && max != null) {
        if (Number(min) === Number(max)) {
            return String(min);
        }

        return `${min}–${max}`;
    }

    if (min != null) {
        return `${min}+`;
    }

    return `jusqu'à ${max}`;
}

// ============================================================
// AFFICHER DATE/PÉRIODE ET DURÉE
// ============================================================

function formatShooting(offer) {
    const mainValue = offer.shoot_date || offer.shoot_date_text || "À préciser";
    const duration = offer.shoot_duration_text || "";

    return `
        <span>${escapeHtml(mainValue)}</span>
        ${duration ? `<br><small class="schedule-note">${escapeHtml(duration)}</small>` : ""}
    `;
}

// ============================================================
// DÉTERMINER LE STATUT DU PARSER
// ============================================================

function getParserStatus(offer) {
    // Les offres hors bassin doivent rester visibles dans la liste générale,
    // sans polluer la file de revue manuelle.
    if (offer.location_status === "outside" && offer.admin_review_required !== true) {
        return "Hors zone V1";
    }

    const missing = [];

    if (!offer.location_text) {
        missing.push("localisation");
    } else if (offer.location_status === "manual_review") {
        missing.push("localisation à confirmer");
    }

    const hasExactDate = Boolean(offer.shoot_date);
    const hasDateText = Boolean(offer.shoot_date_text);

    if (!hasExactDate && !hasDateText) {
        missing.push("date");
    } else if (!hasExactDate && hasDateText && offer.parser_needs_review) {
        missing.push("date exacte à confirmer");
    }

    // Une annonce qui demande explicitement des âges variés ne doit pas
    // être faussement signalée comme dépourvue d'âge.
    if (
        offer.age_min == null &&
        offer.age_max == null &&
        !hasExplicitAgeDescription(offer)
    ) {
        missing.push("âge");
    }

    if (!offer.gender_male && !offer.gender_female) {
        missing.push("sexe");
    }

    if (missing.length > 0) {
        return "À vérifier : " + [...new Set(missing)].join(", ");
    }

    if (offer.parser_needs_review) {
        const labels = {
            localisation_ambigue: "localisation à confirmer",
            date_exacte_absente: "date exacte à confirmer",
            sexe_annonce_non_precise: "sexe à vérifier",
            age_non_numerique: "âge à préciser"
        };
        const reason = String(offer.parser_review_reason || "")
            .split(",")
            .map(value => value.trim())
            .filter(Boolean)
            .map(value => labels[value] || value);
        return reason.length
            ? `À vérifier : ${[...new Set(reason)].join(", ")}`
            : "À vérifier";
    }

    return "OK";
}

// ============================================================
// CHARGER LES COMPTEURS
// ============================================================

async function loadCounters() {
    const offersResult = await supabaseClient
        .from("offers")
        .select("id", {
            count: "exact",
            head: true
        });

    if (offersResult.error) {
        throw offersResult.error;
    }

    const matchesResult = await supabaseClient
        .from("matches")
        .select("id", {
            count: "exact",
            head: true
        });

    if (matchesResult.error) {
        throw matchesResult.error;
    }

    const notificationsResult = await supabaseClient
        .from("matches")
        .select("id", {
            count: "exact",
            head: true
        })
        .not("notified_at", "is", null);

    if (notificationsResult.error) {
        throw notificationsResult.error;
    }

    offersCount.textContent = offersResult.count ?? 0;
    matchesCount.textContent = matchesResult.count ?? 0;
    notificationsCount.textContent = notificationsResult.count ?? 0;
}

// ============================================================
// CHARGER LES OFFRES
// ============================================================

async function loadOffers() {
    const result = await supabaseClient
        .from("offers")
        .select([
            "id",
            "komparse_id",
            "source_url",
            "title",
            "raw_text",
            "detail_text",
            "location_text",
            "location_status",
            "shoot_date",
            "shoot_date_text",
            "shoot_duration_text",
            "age_min",
            "age_max",
            "age_description",
            "gender_male",
            "gender_female",
            "published_at",
            "parser_needs_review",
            "parser_review_reason",
            "admin_review_required",
            "application_method",
            "application_url"
        ].join(","))
        .order("published_at", {
            ascending: false,
            nullsFirst: false
        })
        .limit(50);

    if (result.error) {
        throw result.error;
    }

    const offers = result.data || [];
    for (const offer of offers) {
        offersById.set(Number(offer.id), offer);
    }

    if (offers.length === 0) {
        offersBody.innerHTML = `
            <tr>
                <td colspan="8">Aucune annonce importée.</td>
            </tr>
        `;
    } else {
        offersBody.innerHTML = offers.map(offer => {
            const parserStatus = getParserStatus(offer);

            const adminStatus = offer.admin_review_required
                ? "À vérifier"
                : "—";

            return `
                <tr>
                    <td>${renderOfferReference(offer)}</td>

                    <td>${formatDate(offer.published_at)}</td>

                    <td>
                        ${escapeHtml(offer.location_text) || "—"}
                    </td>

                    <td>${formatShooting(offer)}</td>

                    <td>${escapeHtml(formatAge(offer))}</td>

                    <td>${escapeHtml(formatGender(offer))}</td>

                    <td class="${parserStatus !== "OK" && parserStatus !== "Hors zone V1" ? "review" : ""}">
                        ${escapeHtml(parserStatus)}
                    </td>

                    <td class="${offer.admin_review_required ? "review" : ""}">
                        ${escapeHtml(adminStatus)}
                        <br>
                        <button class="admin-button" data-offer-id="${offer.id}" data-action="edit">Qualifier</button>
                    </td>
                </tr>
            `;
        }).join("");
    }

    // Charger la file de revue indépendamment des 50 annonces récentes.
    // La file est paginée pour qu'un ancien élément à vérifier ne soit pas
    // invisible simplement parce qu'il est plus ancien que les dernières offres.
    const reviewOffers = await loadAllReviewOffers();
    for (const offer of reviewOffers) {
        offersById.set(Number(offer.id), offer);
    }
    if (reviewCount) {
        reviewCount.textContent = String(reviewOffers.length);
    }

    if (reviewOffers.length === 0) {
        reviewOffersBody.innerHTML = `
            <tr>
                <td colspan="8">Aucune annonce actuellement à vérifier.</td>
            </tr>
        `;
        return;
    }

    reviewOffersBody.innerHTML = reviewOffers.map(offer => {
        const parserStatus = getParserStatus(offer);
        const isAdminReview = offer.admin_review_required === true;

        return `
            <tr>
                <td>${renderOfferReference(offer)}</td>
                <td>${formatDate(offer.published_at)}</td>
                <td>${escapeHtml(offer.location_text) || "—"}</td>
                <td>${formatShooting(offer)}</td>
                <td>${escapeHtml(formatAge(offer))}</td>
                <td>${escapeHtml(formatGender(offer))}</td>
                <td class="review">${escapeHtml(parserStatus)}</td>
                <td>
                    <button
                        class="admin-button"
                        data-offer-id="${offer.id}"
                        data-action="edit"
                    >Qualifier</button>
                    ${
                        isAdminReview
                            ? `
                                <button
                                    class="admin-button"
                                    data-offer-id="${offer.id}"
                                    data-action="unreview"
                                >
                                    Retirer le signalement admin
                                </button>
                              `
                            : `
                                <button
                                    class="admin-button"
                                    data-offer-id="${offer.id}"
                                    data-action="review"
                                >
                                    Signaler pour vérification admin
                                </button>
                              `
                    }
                </td>
            </tr>
        `;
    }).join("");
}

const OFFER_REVIEW_COLUMNS = [
    "id",
    "komparse_id",
    "source_url",
    "title",
    "raw_text",
    "detail_text",
    "location_text",
    "location_status",
    "shoot_date",
    "shoot_date_text",
    "shoot_duration_text",
    "age_min",
    "age_max",
    "age_description",
    "gender_male",
    "gender_female",
    "published_at",
    "parser_needs_review",
    "parser_review_reason",
    "admin_review_required",
    "application_method",
    "application_url"
].join(",");

function shouldShowInReview(offer) {
    // Explicitly out-of-scope offers are not parser review items unless an
    // administrator manually flagged them.
    if (offer.location_status === "outside" && offer.admin_review_required !== true) {
        return false;
    }

    if (
        offer.location_status === "manual_review" ||
        offer.parser_needs_review === true ||
        offer.admin_review_required === true
    ) {
        return true;
    }

    // A documented period or scheduling condition is valid source information.
    // Keep it out of the queue once an administrator has explicitly reviewed it.
    const hasSchedule = Boolean(offer.shoot_date || offer.shoot_date_text);
    const hasAge = offer.age_min != null ||
        offer.age_max != null ||
        Boolean(String(offer.age_description || "").trim());
    const hasGender = offer.gender_male === true || offer.gender_female === true;
    return !offer.location_text || !hasSchedule || !hasAge || !hasGender;
}

async function loadAllReviewOffers() {
    const pageSize = 500;
    const uniqueOffers = new Map();

    for (let offset = 0; ; offset += pageSize) {
        const result = await supabaseClient
            .from("offers")
            .select(OFFER_REVIEW_COLUMNS)
            .or("parser_needs_review.eq.true,admin_review_required.eq.true,location_status.eq.manual_review,shoot_date.is.null,shoot_date_text.is.null,location_text.is.null,gender_male.eq.false,gender_female.eq.false,age_min.is.null,age_max.is.null")
            .order("id", { ascending: true })
            .range(offset, offset + pageSize - 1);

        if (result.error) {
            throw result.error;
        }

        const page = result.data || [];
        for (const offer of page) {
            if (shouldShowInReview(offer)) {
                uniqueOffers.set(offer.id, offer);
            }
        }

        if (page.length < pageSize) {
            break;
        }
    }

    return [...uniqueOffers.values()].sort((a, b) => {
        const aDate = a.published_at ? Date.parse(a.published_at) : 0;
        const bDate = b.published_at ? Date.parse(b.published_at) : 0;
        return bDate - aDate;
    });
}

// ============================================================
// MODIFIER LE STATUT DE VÉRIFICATION
// ============================================================

async function setReviewStatus(offerId, required) {
    const result = await supabaseClient
        .from("offers")
        .update({
            admin_review_required: required
        })
        .eq("id", offerId);

    if (result.error) {
        throw result.error;
    }
}

// ============================================================
// QUALIFICATION MANUELLE DES ANNONCES
// ============================================================

function setEditorMessage(message) {
    qualificationValidation.textContent = message || "";
    qualificationValidation.hidden = !message;
}

function openQualificationEditor(offerId) {
    const offer = offersById.get(Number(offerId));
    if (!offer) {
        showError("Annonce introuvable dans les données chargées. Actualisez le tableau.");
        return;
    }

    editingOfferId = Number(offerId);
    qualificationForm.reset();
    setEditorMessage("");
    qualificationOfferId.textContent = `Annonce Komparse ${offer.komparse_id || offer.id}`;

    const fields = qualificationForm.elements;
    fields.namedItem("title").value = offer.title || "";
    fields.namedItem("location_text").value = offer.location_text || "";
    fields.namedItem("location_status").value = offer.location_status || "manual_review";
    fields.namedItem("shoot_date").value = offer.shoot_date || "";
    fields.namedItem("shoot_date_text").value = offer.shoot_date_text || "";
    fields.namedItem("shoot_duration_text").value = offer.shoot_duration_text || "";
    fields.namedItem("age_min").value = offer.age_min ?? "";
    fields.namedItem("age_max").value = offer.age_max ?? "";
    fields.namedItem("age_description").value = offer.age_description || "";
    fields.namedItem("gender").value =
        offer.gender_male && offer.gender_female ? "mixed" :
        offer.gender_male ? "male" :
        offer.gender_female ? "female" : "unknown";
    fields.namedItem("application_method").value = offer.application_method || "";
    fields.namedItem("application_url").value = offer.application_url || "";
    fields.namedItem("parser_review_reason").value = offer.parser_review_reason || "";
    fields.namedItem("mark_reviewed").checked = false;

    // Prefer the detail page text, then the captured listing text. Keep it
    // text-only so source content cannot inject HTML into the admin page.
    qualificationSource.textContent = offer.detail_text || offer.raw_text || "Aucun texte source enregistré.";
    qualificationModal.hidden = false;
    fields.namedItem("location_text").focus();
}

function closeQualificationEditor() {
    qualificationModal.hidden = true;
    editingOfferId = null;
    setEditorMessage("");
}

function validateQualification(data, markReviewed) {
    if (data.age_min !== null && data.age_min < 0) return "L’âge minimum ne peut pas être négatif.";
    if (data.age_max !== null && data.age_max < 0) return "L’âge maximum ne peut pas être négatif.";
    if (data.age_min !== null && data.age_max !== null && data.age_min > data.age_max) {
        return "L’âge minimum ne peut pas dépasser l’âge maximum.";
    }
    if (data.shoot_date && data.shoot_date_text) {
        // Exact date and source wording may coexist; this is intentional.
    }
    if (data.application_url && !/^https?:\/\//i.test(data.application_url)) {
        return "L’URL de candidature doit commencer par http:// ou https://.";
    }
    if (markReviewed) {
        if (!data.location_text.trim()) return "Impossible de valider : la localisation manque.";
        if (data.location_status === "manual_review") return "Confirmez la localisation ou laissez l’annonce en revue.";
        if (!data.shoot_date && !data.shoot_date_text.trim()) return "Impossible de valider : indiquez une date, une période ou la modalité de tournage.";
        if (data.age_min === null && data.age_max === null && !data.age_description.trim()) return "Impossible de valider : indiquez une tranche d’âge ou une description non numérique.";
        if (!data.gender_male && !data.gender_female) return "Impossible de valider : confirmez le sexe recherché.";
        if (data.location_status === "outside") {
            // Out-of-scope offers can be marked reviewed without being matched.
        }
    }
    return "";
}

qualificationForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!editingOfferId) return;

    const fields = qualificationForm.elements;
    const ageMinValue = fields.namedItem("age_min").value.trim();
    const ageMaxValue = fields.namedItem("age_max").value.trim();
    const gender = fields.namedItem("gender").value;
    const markReviewed = fields.namedItem("mark_reviewed").checked;
    const data = {
        title: fields.namedItem("title").value.trim() || null,
        location_text: fields.namedItem("location_text").value.trim() || null,
        location_status: fields.namedItem("location_status").value,
        shoot_date: fields.namedItem("shoot_date").value || null,
        shoot_date_text: fields.namedItem("shoot_date_text").value.trim() || null,
        shoot_duration_text: fields.namedItem("shoot_duration_text").value.trim() || null,
        age_min: ageMinValue === "" ? null : Number(ageMinValue),
        age_max: ageMaxValue === "" ? null : Number(ageMaxValue),
        age_description: fields.namedItem("age_description").value.trim() || null,
        gender_male: gender === "male" || gender === "mixed",
        gender_female: gender === "female" || gender === "mixed",
        application_method: fields.namedItem("application_method").value || null,
        application_url: fields.namedItem("application_url").value.trim() || null,
        parser_review_reason: fields.namedItem("parser_review_reason").value.trim() || null
    };

    const validationMessage = validateQualification(data, markReviewed);
    if (validationMessage) {
        setEditorMessage(validationMessage);
        return;
    }

    if (markReviewed) {
        data.parser_needs_review = false;
        data.admin_review_required = false;
        data.parser_review_reason = null;
    } else {
        // Saving without explicit confirmation keeps the offer in the review queue.
        data.parser_needs_review = true;
        data.admin_review_required = true;
    }

    const submitButton = qualificationForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = "Enregistrement…";

    try {
        const result = await supabaseClient
            .from("offers")
            .update(data)
            .eq("id", editingOfferId)
            .select(OFFER_REVIEW_COLUMNS)
            .single();

        if (result.error) throw result.error;

        offersById.set(Number(result.data.id), result.data);
        closeQualificationEditor();
        await loadCounters();
        await loadOffers();
    } catch (error) {
        console.error("Erreur lors de la qualification de l’annonce :", error);
        setEditorMessage("Enregistrement impossible : " + (error.message || "erreur inconnue"));
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Enregistrer la qualification";
    }
});

qualificationModal.addEventListener("click", event => {
    if (event.target === qualificationModal) closeQualificationEditor();
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !qualificationModal.hidden) {
        closeQualificationEditor();
    }
});

// ============================================================
// GESTION DES BOUTONS
// ============================================================

document.addEventListener("click", async event => {
    const button = event.target.closest("[data-action]");

    if (!button) {
        return;
    }

    const offerId = Number(button.dataset.offerId);
    const action = button.dataset.action;

    if (action === "edit") {
        if (offerId) openQualificationEditor(offerId);
        return;
    }

    if (action === "close-editor") {
        closeQualificationEditor();
        return;
    }

    if (!offerId) {
        return;
    }

    button.disabled = true;

    try {
        await setReviewStatus(
            offerId,
            action === "review"
        );

        await loadOffers();
    } catch (error) {
        console.error(error);

        showError(
            "Impossible de modifier le statut de l'annonce."
        );

        button.disabled = false;
    }
});

// ============================================================
// CHARGER LE DASHBOARD
// ============================================================

async function loadAdminDashboard(session) {
    adminUserEmail.textContent =
        session.user.email || "Administrateur";

    const adminResult = await supabaseClient.rpc("is_admin");

    if (adminResult.error) {
        throw adminResult.error;
    }

    if (adminResult.data !== true) {
        showError(
            "Accès refusé : ce compte n'est pas administrateur."
        );

        return;
    }

    adminApp.classList.remove("admin-hidden");

    await loadCounters();
    await loadOffers();
}

// ============================================================
// DÉCONNEXION DEPUIS L'ADMINISTRATION
// ============================================================

const adminLogoutButton = document.getElementById("admin-logout");

if (adminLogoutButton) {
    adminLogoutButton.addEventListener("click", async () => {
        adminLogoutButton.disabled = true;

        const { error } = await supabaseClient.auth.signOut();

        if (error) {
            showError("La déconnexion a échoué. Réessayez.");
            adminLogoutButton.disabled = false;
            return;
        }

        redirectToLogin();
    });
}

// ============================================================
// INITIALISATION
// ============================================================

async function initializeAdmin() {
    try {
        const sessionResult =
            await supabaseClient.auth.getSession();

        if (sessionResult.error) {
            throw sessionResult.error;
        }

        let session = sessionResult.data.session;

        // Attendre brièvement le rétablissement de session
        // après une connexion ou un changement de page.
        if (!session) {
            await new Promise(resolve => setTimeout(resolve, 800));

            const retryResult =
                await supabaseClient.auth.getSession();

            if (retryResult.error) {
                throw retryResult.error;
            }

            session = retryResult.data.session;
        }

        if (!session) {
            adminUserEmail.textContent = "Non connecté";

            showError(
                "Vous devez être connecté pour accéder au tableau de bord administrateur."
            );

            return;
        }

        await loadAdminDashboard(session);
    } catch (error) {
        console.error("Erreur dashboard admin :", error);

        showError(
            "Erreur lors du chargement du tableau de bord : " +
            (error.message || "erreur inconnue")
        );
    }
}

initializeAdmin();
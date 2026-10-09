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
const reviewOffersBody = document.getElementById("review-offers-body");
const offersBody = document.getElementById("offers-body");

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

    return date.toLocaleString("fr-FR", {
        dateStyle: "short",
        timeStyle: "short"
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
    const missing = [];

    if (!offer.location_text) {
        missing.push("localisation");
    } else if (offer.location_status === "manual_review") {
        missing.push("localisation à confirmer");
    }

    const hasExactDate = Boolean(offer.shoot_date);
    const hasDateText = Boolean(offer.shoot_date_text);

    if (!hasExactDate) {
        missing.push(hasDateText ? "date exacte à confirmer" : "date");
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
            "admin_review_required"
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
                    <td>${escapeHtml(offer.komparse_id)}</td>

                    <td>${formatDate(offer.published_at)}</td>

                    <td>
                        ${escapeHtml(offer.location_text) || "—"}
                    </td>

                    <td>${formatShooting(offer)}</td>

                    <td>${escapeHtml(formatAge(offer))}</td>

                    <td>${escapeHtml(formatGender(offer))}</td>

                    <td class="${parserStatus !== "OK" ? "review" : ""}">
                        ${escapeHtml(parserStatus)}
                    </td>

                    <td class="${offer.admin_review_required ? "review" : ""}">
                        ${escapeHtml(adminStatus)}
                    </td>
                </tr>
            `;
        }).join("");
    }

    const reviewOffers = offers.filter(offer =>
        offer.parser_needs_review === true ||
        offer.admin_review_required === true ||
        getParserStatus(offer) !== "OK"
    );

    if (reviewOffers.length === 0) {
        reviewOffersBody.innerHTML = `
            <tr>
                <td colspan="8">Aucune annonce à vérifier.</td>
            </tr>
        `;

        return;
    }

    reviewOffersBody.innerHTML = reviewOffers.map(offer => {
        const parserStatus = getParserStatus(offer);
        const isAdminReview = offer.admin_review_required === true;

        return `
            <tr>
                <td>${escapeHtml(offer.komparse_id)}</td>

                <td>${formatDate(offer.published_at)}</td>

                <td>
                    ${escapeHtml(offer.location_text) || "—"}
                </td>

                <td>${formatShooting(offer)}</td>

                <td>${escapeHtml(formatAge(offer))}</td>

                <td>${escapeHtml(formatGender(offer))}</td>

                <td class="review">
                    ${escapeHtml(parserStatus)}
                </td>

                <td>
                    ${
                        isAdminReview
                            ? `
                                <button
                                    class="admin-button"
                                    data-offer-id="${offer.id}"
                                    data-action="unreview"
                                >
                                    ✓ Vérifié
                                </button>
                              `
                            : `
                                <button
                                    class="admin-button"
                                    data-offer-id="${offer.id}"
                                    data-action="review"
                                >
                                    Marquer à vérifier
                                </button>
                              `
                    }
                </td>
            </tr>
        `;
    }).join("");
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
// GESTION DES BOUTONS
// ============================================================

document.addEventListener("click", async event => {
    const button = event.target.closest("[data-action]");

    if (!button) {
        return;
    }

    const offerId = Number(button.dataset.offerId);
    const action = button.dataset.action;

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
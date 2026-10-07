// ============================================================
// KOMPARSE ASSISTANT — DASHBOARD ADMIN
// ============================================================

// IMPORTANT : utiliser uniquement la clé publique/publishable.
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

const adminUserEmail =
    document.getElementById("admin-user-email");

const offersCount =
    document.getElementById("offers-count");

const matchesCount =
    document.getElementById("matches-count");

const notificationsCount =
    document.getElementById("notifications-count");

const reviewOffersBody =
    document.getElementById("review-offers-body");

const offersBody =
    document.getElementById("offers-body");


// ============================================================
// AFFICHER UNE ERREUR
// ============================================================

function showError(message) {

    adminError.textContent = message;

    adminError.classList.remove(
        "admin-hidden"
    );
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

    return date.toLocaleString(
        "fr-FR",
        {
            dateStyle: "short",
            timeStyle: "short"
        }
    );
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
// FORMATER L'ÂGE
// ============================================================

function formatAge(offer) {

    const min = offer.age_min;

    const max = offer.age_max;

    if (min === null && max === null) {
        return "Non précisé";
    }

    if (
        min !== null &&
        min !== undefined &&
        max !== null &&
        max !== undefined
    ) {
        if (Number(min) === Number(max)) {
            return String(min);
        }

        return `${min}–${max}`;
    }

    if (min !== null && min !== undefined) {
        return `${min}+`;
    }

    return `jusqu'à ${max}`;
}


// ============================================================
// DÉTERMINER LE STATUT DU PARSER
// ============================================================

function getParserStatus(offer) {

    if (offer.parser_needs_review) {
        return "À vérifier";
    }

    const missing = [];

    if (!offer.location_text) {
        missing.push("localisation");
    }

    if (
        offer.shoot_date === null ||
        offer.shoot_date === undefined ||
        offer.shoot_date === ""
    ) {
        missing.push("date");
    }

    if (
        offer.age_min === null ||
        offer.age_max === null
    ) {
        missing.push("âge");
    }

    if (
        !offer.gender_male &&
        !offer.gender_female
    ) {
        missing.push("sexe");
    }

    if (missing.length > 0) {
        return "À vérifier : " + missing.join(", ");
    }

    return "OK";
}


// ============================================================
// ÉCHARGER LES COMPTEURS
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
        .not(
            "notified_at",
            "is",
            null
        );

    if (notificationsResult.error) {
        throw notificationsResult.error;
    }


    offersCount.textContent =
        offersResult.count ?? 0;

    matchesCount.textContent =
        matchesResult.count ?? 0;

    notificationsCount.textContent =
        notificationsResult.count ?? 0;
}


// ============================================================
// CHARGER LES OFFRES
// ============================================================

async function loadOffers() {

    const result = await supabaseClient
        .from("offers")
        .select(
            [
                "id",
                "komparse_id",
                "title",
                "location_text",
                "shoot_date",
                "age_min",
                "age_max",
                "gender_male",
                "gender_female",
                "published_at",
                "parser_needs_review",
                "admin_review_required"
            ].join(",")
        )
        .order(
            "published_at",
            {
                ascending: false,
                nullsFirst: false
            }
        )
        .limit(50);

    if (result.error) {
        throw result.error;
    }

    const offers = result.data || [];


    // --------------------------------------------------------
    // Tableau des dernières offres
    // --------------------------------------------------------

    if (offers.length === 0) {

        offersBody.innerHTML = `
            <tr>
                <td colspan="8">
                    Aucune annonce importée.
                </td>
            </tr>
        `;

    } else {

        offersBody.innerHTML = offers
            .map(offer => {

                const parserStatus =
                    getParserStatus(offer);

                const adminStatus =
                    offer.admin_review_required
                        ? "À vérifier"
                        : "—";

                return `
                    <tr>

                        <td>
                            ${escapeHtml(
                                offer.komparse_id
                            )}
                        </td>

                        <td>
                            ${formatDate(
                                offer.published_at
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                offer.location_text
                            ) || "—"}
                        </td>

                        <td>
                            ${
                                offer.shoot_date
                                    ? escapeHtml(
                                        offer.shoot_date
                                    )
                                    : "—"
                            }
                        </td>

                        <td>
                            ${escapeHtml(
                                formatAge(offer)
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                formatGender(offer)
                            )}
                        </td>

                        <td class="${
                            parserStatus !== "OK"
                                ? "review"
                                : ""
                        }">
                            ${escapeHtml(
                                parserStatus
                            )}
                        </td>

                        <td class="${
                            offer.admin_review_required
                                ? "review"
                                : ""
                        }">
                            ${escapeHtml(
                                adminStatus
                            )}
                        </td>

                    </tr>
                `;
            })
            .join("");
    }


    // --------------------------------------------------------
    // Tableau des offres à vérifier
    // --------------------------------------------------------

    const reviewOffers = offers.filter(
        offer =>
            offer.parser_needs_review === true
            ||
            offer.admin_review_required === true
            ||
            getParserStatus(offer) !== "OK"
    );


    if (reviewOffers.length === 0) {

        reviewOffersBody.innerHTML = `
            <tr>
                <td colspan="8">
                    Aucune annonce à vérifier.
                </td>
            </tr>
        `;

        return;
    }


    reviewOffersBody.innerHTML = reviewOffers
        .map(offer => {

            const parserStatus =
                getParserStatus(offer);

            const isAdminReview =
                offer.admin_review_required === true;

            return `
                <tr>

                    <td>
                        ${escapeHtml(
                            offer.komparse_id
                        )}
                    </td>

                    <td>
                        ${formatDate(
                            offer.published_at
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            offer.location_text
                        ) || "—"}
                    </td>

                    <td>
                        ${
                            offer.shoot_date
                                ? escapeHtml(
                                    offer.shoot_date
                                )
                                : "—"
                        }
                    </td>

                    <td>
                        ${escapeHtml(
                            formatAge(offer)
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            formatGender(offer)
                        )}
                    </td>

                    <td class="review">
                        ${escapeHtml(
                            parserStatus
                        )}
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
        })
        .join("");
}


// ============================================================
// MARQUER UNE OFFRE À VÉRIFIER
// ============================================================

async function setReviewStatus(
    offerId,
    required
) {

    const result = await supabaseClient
        .from("offers")
        .update({
            admin_review_required: required
        })
        .eq(
            "id",
            offerId
        );

    if (result.error) {
        throw result.error;
    }
}


// ============================================================
// GESTION DES BOUTONS
// ============================================================

document.addEventListener(
    "click",
    async event => {

        const button =
            event.target.closest(
                "[data-action]"
            );

        if (!button) {
            return;
        }

        const offerId =
            Number(
                button.dataset.offerId
            );

        const action =
            button.dataset.action;

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
                "Impossible de modifier le statut "
                + "de l'annonce."
            );

            button.disabled = false;
        }
    }
);


// ============================================================
// INITIALISATION
// ============================================================

async function initializeAdmin() {

    try {

        // ----------------------------------------------------
        // Vérifier la session
        // ----------------------------------------------------

        const sessionResult =
            await supabaseClient.auth.getSession();

        if (sessionResult.error) {
            throw sessionResult.error;
        }

        const session =
            sessionResult.data.session;

        if (!session) {

            window.location.href =
                "./index.html";

            return;
        }


        adminUserEmail.textContent =
            session.user.email ||
            "Administrateur";


        // ----------------------------------------------------
        // Vérifier le rôle admin
        // ----------------------------------------------------

        const adminResult =
            await supabaseClient.rpc(
                "is_admin"
            );

        if (adminResult.error) {
            throw adminResult.error;
        }

        if (adminResult.data !== true) {

            showError(
                "Accès refusé : ce compte "
                + "n'est pas administrateur."
            );

            return;
        }


        // ----------------------------------------------------
        // Afficher le dashboard
        // ----------------------------------------------------

        adminApp.classList.remove(
            "admin-hidden"
        );


        await loadCounters();

        await loadOffers();


    } catch (error) {

        console.error(
            "Erreur dashboard admin :",
            error
        );

        showError(
            "Erreur lors du chargement du "
            + "tableau de bord : "
            + (
                error.message ||
                "erreur inconnue"
            )
        );
    }
}


initializeAdmin();
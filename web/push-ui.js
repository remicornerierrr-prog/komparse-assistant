// ============================================================
// SERVICE WORKER
// ============================================================

async function getPushRegistration() {

    if (
        !("serviceWorker" in navigator)
    ) {

        throw new Error(
            "Les Service Workers ne sont pas pris en charge."
        );

    }


    const registration =
        await navigator
            .serviceWorker
            .ready;


    return registration;

}


// ============================================================
// IDENTITÉ DU NAVIGATEUR / APPAREIL
// ============================================================

let pushDeviceIdFallback = null;

function getPushDeviceId() {
    const storageKey = "komparse-push-device-id";

    try {
        let deviceId = localStorage.getItem(storageKey);

        if (!deviceId) {
            deviceId = (typeof crypto !== "undefined" && crypto.randomUUID)
                ? crypto.randomUUID()
                : `device-${Date.now()}-${Math.random().toString(36).slice(2)}`;
            localStorage.setItem(storageKey, deviceId);
        }

        return deviceId;
    } catch (error) {
        // Fallback exceptionnel si le stockage local est bloqué.
        // Un identifiant temporaire différent par contexte empêche deux
        // navigateurs de s'écraser mutuellement ; l'endpoint servira à
        // retrouver la ligne lors d'une prochaine synchronisation.
        if (!pushDeviceIdFallback) {
            pushDeviceIdFallback =
                `device-temp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        }
        return pushDeviceIdFallback;
    }
}

function getPushDeviceLabel() {
    const ua = navigator.userAgent || "";
    let browser = "Navigateur";
    let platform = "Appareil";

    if (/Edg\//i.test(ua)) browser = "Microsoft Edge";
    else if (/Firefox\//i.test(ua)) browser = "Firefox";
    else if (/OPR\//i.test(ua)) browser = "Opera";
    else if (/Chrome\//i.test(ua) && !/Edg\//i.test(ua)) browser = "Chrome";
    else if (/Safari\//i.test(ua) && !/Chrome\//i.test(ua)) browser = "Safari";

    if (/Windows/i.test(ua)) platform = "Windows";
    else if (/Android/i.test(ua)) platform = "Android";
    else if (/(iPhone|iPad|iPod)/i.test(ua)) platform = "iOS";
    else if (/Macintosh|Mac OS X/i.test(ua)) platform = "macOS";
    else if (/Linux/i.test(ua)) platform = "Linux";

    return `${browser} · ${platform}`;
}

async function loadUserPushSubscriptions(userId) {
    const result = await supabaseClient
        .from("push_subscriptions")
        .select("id,device_id,device_label,endpoint,subscription_json,last_seen_at")
        .eq("user_id", userId)
        .order("last_seen_at", { ascending: false });

    if (result.error) {
        throw new Error(
            "Impossible de vérifier les navigateurs enregistrés : " +
            result.error.message
        );
    }

    return result.data || [];
}

// ============================================================
// ÉTAT DES NOTIFICATIONS
// ============================================================

async function updatePushUI() {
    if (!enablePushButton) return;

    if (!isPushSupported()) {
        enablePushButton.disabled = true;
        enablePushButton.textContent = "Notifications non disponibles";
        showPushStatus(
            "Les notifications push ne sont pas prises en charge par ce navigateur.",
            "error"
        );
        return;
    }

    const permission = getNotificationPermission();

    if (permission === "denied") {
        enablePushButton.disabled = false;
        enablePushButton.textContent = "Notifications bloquées ici";
        showPushStatus(
            "Les notifications sont bloquées dans ce navigateur. Les autres navigateurs déjà associés à votre compte ne sont pas désactivés.",
            "error"
        );
        return;
    }

    try {
        const user = await getCurrentUser();
        const registration = await getPushRegistration();
        const browserSubscription = await getExistingPushSubscription(registration);

        if (!user) {
            enablePushButton.disabled = false;
            enablePushButton.textContent = browserSubscription
                ? "Connectez-vous pour synchroniser les notifications"
                : "🔔 Activer les notifications";
            showPushStatus(
                browserSubscription
                    ? "Un abonnement existe dans ce navigateur. Connectez-vous pour l'associer à votre compte."
                    : "Connectez-vous pour activer les notifications sur ce navigateur.",
                "info"
            );
            return;
        }

        let savedRows = await loadUserPushSubscriptions(user.id);

        if (browserSubscription) {
            const deviceId = getPushDeviceId();
            const currentEndpoint = browserSubscription.endpoint;
            const currentRow = savedRows.find(row =>
                row.device_id === deviceId ||
                row.endpoint === currentEndpoint ||
                row.subscription_json?.endpoint === currentEndpoint
            );

            // Synchroniser ce navigateur sans supprimer ceux déjà associés
            // au même compte sur d'autres navigateurs ou appareils.
            if (
                !currentRow ||
                currentRow.endpoint !== currentEndpoint ||
                currentRow.device_id !== deviceId
            ) {
                await savePushSubscription(browserSubscription);
                savedRows = await loadUserPushSubscriptions(user.id);
            }

            const count = savedRows.length;
            enablePushButton.disabled = false;
            enablePushButton.textContent = "✓ Notifications activées ici";
            showPushStatus(
                `Notifications actives sur ce navigateur. ${count} navigateur(s)/appareil(s) enregistré(s) pour votre compte. Activez-les une fois sur chaque navigateur souhaité.`,
                "success"
            );
            return;
        }

        enablePushButton.disabled = false;
        enablePushButton.textContent = "🔔 Activer sur ce navigateur";

        if (savedRows.length > 0) {
            showPushStatus(
                `Aucun abonnement actif dans ce navigateur. Votre compte possède déjà ${savedRows.length} navigateur(s)/appareil(s) enregistré(s). Cliquez pour ajouter celui-ci sans désactiver les autres.`,
                "info"
            );
        } else {
            showPushStatus(
                "Les notifications ne sont pas encore activées dans ce navigateur.",
                "info"
            );
        }
    } catch (error) {
        console.error("Erreur vérification/synchronisation abonnement push :", error);
        enablePushButton.disabled = false;
        enablePushButton.textContent = "Réparer les notifications ici";
        showPushStatus(
            "L'abonnement de ce navigateur n'a pas pu être vérifié. Cliquez pour le réparer. " +
            (error.message || "Erreur inconnue."),
            "error"
        );
    }
}

// ============================================================
// ENREGISTRER / METTRE À JOUR UN SEUL NAVIGATEUR
// ============================================================

async function savePushSubscription(subscription) {
    const user = await getCurrentUser();

    if (!user) {
        throw new Error("Vous devez être connecté.");
    }

    if (!subscription || !subscription.endpoint) {
        throw new Error("L'abonnement push ne contient pas d'endpoint valide.");
    }

    const deviceId = getPushDeviceId();
    const now = new Date().toISOString();

    const payload = {
        user_id: user.id,
        device_id: deviceId,
        device_label: getPushDeviceLabel(),
        user_agent: navigator.userAgent || null,
        endpoint: subscription.endpoint,
        subscription_json: subscription,
        last_seen_at: now
    };

    // Priorité à l'identifiant stable de ce profil navigateur.
    let lookup = await supabaseClient
        .from("push_subscriptions")
        .select("id")
        .eq("user_id", user.id)
        .eq("device_id", deviceId)
        .limit(1);

    if (lookup.error) {
        throw new Error("Impossible de rechercher cet appareil : " + lookup.error.message);
    }

    let existingRow = (lookup.data || [])[0] || null;

    // Migration transparente des anciennes lignes, qui n'avaient
    // pas encore device_id : on tente de retrouver le même endpoint.
    if (!existingRow) {
        lookup = await supabaseClient
            .from("push_subscriptions")
            .select("id")
            .eq("user_id", user.id)
            .eq("endpoint", subscription.endpoint)
            .limit(1);

        if (lookup.error) {
            throw new Error("Impossible de rechercher l'ancien abonnement : " + lookup.error.message);
        }

        existingRow = (lookup.data || [])[0] || null;
    }

    let result;

    if (existingRow) {
        result = await supabaseClient
            .from("push_subscriptions")
            .update(payload)
            .eq("id", existingRow.id)
            .eq("user_id", user.id);
    } else {
        result = await supabaseClient
            .from("push_subscriptions")
            .insert(payload);
    }

    if (result.error) {
        console.error("Erreur enregistrement abonnement push :", result.error);
        throw new Error(
            "Impossible d'enregistrer cet appareil pour les notifications : " +
            result.error.message
        );
    }
}

// ============================================================
// ACTIVER LES NOTIFICATIONS DANS CE NAVIGATEUR
// ============================================================

if (enablePushButton) {
    enablePushButton.addEventListener("click", async function () {
        enablePushButton.disabled = true;
        showPushStatus("Activation des notifications dans ce navigateur...", "info");

        try {
            const user = await getCurrentUser();
            if (!user) {
                throw new Error("Vous devez être connecté pour activer les notifications.");
            }

            const registration = await getPushRegistration();
            const subscription = await subscribeToPush(registration);

            if (!subscription) {
                throw new Error("Aucun abonnement push n'a été créé.");
            }

            await savePushSubscription(subscription);
            const rows = await loadUserPushSubscriptions(user.id);

            enablePushButton.textContent = "✓ Notifications activées ici";
            showPushStatus(
                `Notifications activées sur ce navigateur. ${rows.length} navigateur(s)/appareil(s) enregistré(s) pour votre compte. Les autres restent actifs.`,
                "success"
            );

            console.log("Abonnement push de ce navigateur enregistré.");
        } catch (error) {
            console.error("Erreur activation push :", error);
            showPushStatus(
                error.message || "Impossible d'activer les notifications.",
                "error"
            );
        } finally {
            enablePushButton.disabled = false;
        }
    });
}



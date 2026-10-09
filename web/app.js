// ============================================================
// CONNEXION SUPABASE
// ============================================================

const SUPABASE_URL =
    "https://glufyxsdmaccuuqpoxbo.supabase.co";


const SUPABASE_PUBLISHABLE_KEY =
    "sb_publishable_RdYDH-Ez9SGoLxMaKceXsQ_KQPQmwBu";


const supabaseClient =
    window.supabase.createClient(
        SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY
    );


console.log(
    "Connexion Supabase initialisée."
);


// ============================================================
// ÉLÉMENTS HTML
// ============================================================

const authSection =
    document.getElementById(
        "auth-section"
    );


const profileSection =
    document.getElementById(
        "profile-section"
    );


const emailInput =
    document.getElementById(
        "email"
    );


const passwordInput =
    document.getElementById(
        "password"
    );


const signupButton =
    document.getElementById(
        "signup-button"
    );


const loginButton =
    document.getElementById(
        "login-button"
    );


const forgotPasswordButton =
    document.getElementById(
        "forgot-password-button"
    );


const passwordResetSection =
    document.getElementById(
        "password-reset-section"
    );


const newPasswordInput =
    document.getElementById(
        "new-password"
    );


const confirmNewPasswordInput =
    document.getElementById(
        "confirm-new-password"
    );


const resetPasswordButton =
    document.getElementById(
        "reset-password-button"
    );


// Le paramètre est ajouté à l'URL de retour par le lien de récupération.
let passwordRecoveryMode =
    new URLSearchParams(window.location.search).get("mode") === "recovery";


const logoutButton =
    document.getElementById(
        "logout-button"
    );


const adminButton =
    document.getElementById(
        "admin-button"
    );


const profileEmailInput =
    document.getElementById(
        "profile-email"
    );


const messageElement =
    document.getElementById(
        "message"
    );


const profileSaveMessageElement =
    document.getElementById(
        "profile-save-message"
    );


const saveProfileButton =
    document.getElementById(
        "save-profile-button"
    );


const birthDateInput =
    document.getElementById(
        "birth-date"
    );


const calculatedAgeElement =
    document.getElementById(
        "calculated-age"
    );


const enablePushButton =
    document.getElementById(
        "enable-push-button"
    );


const pushStatusElement =
    document.getElementById(
        "push-status"
    );


// ============================================================
// CONSTANTES PHOTOS
// ============================================================

const PHOTO_BUCKET =
    "profile-photos";


const MAX_PHOTO_SIZE =
    5 * 1024 * 1024;


const ALLOWED_PHOTO_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp"
];


const PHOTO_CONFIG = {

    portrait: {
        inputId: "photo-portrait",
        previewId: "photo-preview-portrait",
        statusId: "photo-status-portrait"
    },

    left: {
        inputId: "photo-left",
        previewId: "photo-preview-left",
        statusId: "photo-status-left"
    },

    right: {
        inputId: "photo-right",
        previewId: "photo-preview-right",
        statusId: "photo-status-right"
    },

    full_body: {
        inputId: "photo-full-body",
        previewId: "photo-preview-full_body",
        statusId: "photo-status-full_body"
    }

};


// ============================================================
// MESSAGE GÉNÉRAL
// ============================================================

function showMessage(message) {

    if (!messageElement) {
        return;
    }


    messageElement.textContent =
        message;


    messageElement.style.display =
        "block";
}


function clearMessage() {

    if (!messageElement) {
        return;
    }


    messageElement.textContent =
        "";


    messageElement.style.display =
        "none";
}


// ============================================================
// RÉINITIALISATION DU MOT DE PASSE
// ============================================================

function showPasswordResetForm() {
    passwordRecoveryMode = true;

    authSection.classList.add("hidden");
    profileSection.classList.add("hidden");

    if (passwordResetSection) {
        passwordResetSection.classList.remove("hidden");
    }
}


function hidePasswordResetForm() {
    if (passwordResetSection) {
        passwordResetSection.classList.add("hidden");
    }
}


// ============================================================
// MESSAGE PROFIL
// ============================================================

function showProfileSaveMessage(message) {

    if (!profileSaveMessageElement) {
        return;
    }


    profileSaveMessageElement.textContent =
        message;


    profileSaveMessageElement.style.display =
        "block";
}


function clearProfileSaveMessage() {

    if (!profileSaveMessageElement) {
        return;
    }


    profileSaveMessageElement.textContent =
        "";


    profileSaveMessageElement.style.display =
        "none";
}


// ============================================================
// STATUT PUSH
// ============================================================

function showPushStatus(
    message,
    type = "info"
) {

    if (!pushStatusElement) {
        return;
    }


    pushStatusElement.textContent =
        message;


    pushStatusElement.className =
        "";


    pushStatusElement.id =
        "push-status";


    pushStatusElement.classList.add(
        type
    );
}


function clearPushStatus() {

    if (!pushStatusElement) {
        return;
    }


    pushStatusElement.textContent =
        "";


    pushStatusElement.className =
        "info";


    pushStatusElement.id =
        "push-status";
}


// ============================================================
// UTILISATEUR NON CONNECTÉ
// ============================================================

function showLoggedOut() {

    hidePasswordResetForm();

    authSection.classList.remove(
        "hidden"
    );


    profileSection.classList.add(
        "hidden"
    );


    clearProfileSaveMessage();


    clearPushStatus();


    if (enablePushButton) {

        enablePushButton.disabled =
            false;

        enablePushButton.textContent =
            "🔔 Activer les notifications";

    }


    if (adminButton) {

        adminButton.style.display =
            "none";

    }


    clearAllPhotoUI();
}


// ============================================================
// UTILISATEUR CONNECTÉ
// ============================================================

function showLoggedIn(user) {

    if (passwordRecoveryMode) {
        showPasswordResetForm();
        return;
    }

    hidePasswordResetForm();

    authSection.classList.add(
        "hidden"
    );


    profileSection.classList.remove(
        "hidden"
    );


    if (
        user &&
        user.email
    ) {

        profileEmailInput.value =
            user.email;

    }

}


// ============================================================
// ADMINISTRATION
// ============================================================

async function updateAdminUI() {

    if (!adminButton) {
        return;
    }


    // Par défaut, le bouton reste caché.
    // Il n'apparaît que si Supabase confirme
    // que l'utilisateur est administrateur.

    adminButton.style.display =
        "none";


    try {

        const {
            data,
            error
        } =
            await supabaseClient
                .rpc(
                    "is_admin"
                );


        if (error) {

            console.error(
                "Erreur vérification admin :",
                error
            );


            return;
        }


        if (data === true) {

            adminButton.style.display =
                "block";

        }

    }


    catch (error) {

        console.error(
            "Erreur inattendue vérification admin :",
            error
        );

    }

}


// ============================================================
// BOUTON ADMIN
// ============================================================

if (adminButton) {

    adminButton.addEventListener(
        "click",
        function () {

            window.location.href =
                "./admin.html";

        }
    );

}


// ============================================================
// CALCUL DE L'ÂGE
// ============================================================

function calculateAge(
    birthDate
) {

    if (!birthDate) {
        return null;
    }


    const birth =
        new Date(
            birthDate +
            "T00:00:00"
        );


    if (
        Number.isNaN(
            birth.getTime()
        )
    ) {

        return null;
    }


    const today =
        new Date();


    let age =
        today.getFullYear() -
        birth.getFullYear();


    const monthDifference =
        today.getMonth() -
        birth.getMonth();


    if (
        monthDifference < 0 ||
        (
            monthDifference === 0 &&
            today.getDate() <
            birth.getDate()
        )
    ) {

        age--;

    }


    return age;
}


function updateDisplayedAge() {

    const age =
        calculateAge(
            birthDateInput.value
        );


    if (age === null) {

        calculatedAgeElement.textContent =
            "-";


        return;
    }


    calculatedAgeElement.textContent =
        age + " ans";
}


birthDateInput.addEventListener(
    "change",
    updateDisplayedAge
);


// ============================================================
// VALIDATION PHOTO
// ============================================================

function validatePhotoFile(file) {

    if (!file) {

        return {
            valid: true
        };

    }


    if (
        !ALLOWED_PHOTO_TYPES.includes(
            file.type
        )
    ) {

        return {

            valid: false,

            message:
                "Format non accepté. Utilisez uniquement JPG, PNG ou WebP."

        };

    }


    if (
        file.size > MAX_PHOTO_SIZE
    ) {

        return {

            valid: false,

            message:
                "Photo trop volumineuse. La taille maximale est de 5 Mo."

        };

    }


    return {
        valid: true
    };

}


// ============================================================
// EXTENSION
// ============================================================

function getFileExtension(
    mimeType
) {

    switch (mimeType) {

        case "image/jpeg":
            return "jpg";

        case "image/png":
            return "png";

        case "image/webp":
            return "webp";

        default:
            return "bin";

    }

}


// ============================================================
// UTILISATEUR CONNECTÉ
// ============================================================

async function getCurrentUser() {

    const {
        data,
        error
    } =
        await supabaseClient.auth.getUser();


    if (error) {

        console.error(
            "Erreur récupération utilisateur :",
            error
        );


        return null;
    }


    return data.user;
}


// ============================================================
// ÉLÉMENTS PHOTO
// ============================================================

function getPhotoElements(
    photoType
) {

    const config =
        PHOTO_CONFIG[photoType];


    if (!config) {
        return null;
    }


    return {

        input:
            document.getElementById(
                config.inputId
            ),

        preview:
            document.getElementById(
                config.previewId
            ),

        status:
            document.getElementById(
                config.statusId
            ),

        replaceButton:
            document.querySelector(
                `.replace-photo-button[data-photo-type="${photoType}"]`
            )

    };

}


// ============================================================
// STATUT PHOTO
// ============================================================

function setPhotoStatus(
    photoType,
    message,
    type = ""
) {

    const elements =
        getPhotoElements(
            photoType
        );


    if (!elements) {
        return;
    }


    elements.status.textContent =
        message;


    elements.status.className =
        "photo-status";


    if (type) {

        elements.status.classList.add(
            type
        );

    }

}


// ============================================================
// NETTOYAGE PHOTO
// ============================================================

function clearPhotoUI(
    photoType
) {

    const elements =
        getPhotoElements(
            photoType
        );


    if (!elements) {
        return;
    }


    elements.preview.src =
        "";


    elements.preview.classList.add(
        "hidden"
    );


    elements.replaceButton.classList.add(
        "hidden"
    );


    elements.status.textContent =
        "";


    elements.status.className =
        "photo-status";


    elements.input.value =
        "";

}


function clearAllPhotoUI() {

    Object.keys(
        PHOTO_CONFIG
    ).forEach(
        function (photoType) {

            clearPhotoUI(
                photoType
            );

        }
    );

}


// ============================================================
// MINIATURE PHOTO VIA URL SIGNÉE
// ============================================================

async function displayPhoto(
    photoType,
    storagePath
) {

    const elements =
        getPhotoElements(
            photoType
        );


    if (!elements) {
        return;
    }


    if (!storagePath) {

        clearPhotoUI(
            photoType
        );


        return;
    }


    const {
        data,
        error
    } =
        await supabaseClient
            .storage
            .from(
                PHOTO_BUCKET
            )
            .createSignedUrl(
                storagePath,
                60 * 60
            );


    if (error) {

        console.error(
            "Erreur URL signée :",
            error
        );


        setPhotoStatus(
            photoType,
            "Photo enregistrée, mais impossible de charger l'aperçu.",
            "error"
        );


        return;
    }


    elements.preview.src =
        data.signedUrl;


    elements.preview.classList.remove(
        "hidden"
    );


    elements.replaceButton.classList.remove(
        "hidden"
    );


    setPhotoStatus(
        photoType,
        "✓ Photo enregistrée",
        "success"
    );

}


// ============================================================
// CHARGER PHOTOS
// ============================================================

async function loadProfilePhotos() {

    const user =
        await getCurrentUser();


    if (!user) {
        return;
    }


    clearAllPhotoUI();


    const {
        data,
        error
    } =
        await supabaseClient
            .from(
                "profile_photos"
            )
            .select(
                "id,user_id,photo_type,storage_path,created_at"
            )
            .eq(
                "user_id",
                user.id
            );


    if (error) {

        console.error(
            "Erreur chargement photos :",
            error
        );


        return;
    }


    for (
        const photo of data || []
    ) {

        if (
            !PHOTO_CONFIG[
                photo.photo_type
            ]
        ) {

            continue;
        }


        await displayPhoto(
            photo.photo_type,
            photo.storage_path
        );

    }

}


// ============================================================
// UPLOAD PHOTO
// ============================================================

async function uploadProfilePhoto(
    photoType,
    file
) {

    const elements =
        getPhotoElements(
            photoType
        );


    if (!elements) {
        return;
    }


    const validation =
        validatePhotoFile(
            file
        );


    if (
        !validation.valid
    ) {

        elements.input.value =
            "";


        setPhotoStatus(
            photoType,
            validation.message,
            "error"
        );


        return;
    }


    const user =
        await getCurrentUser();


    if (!user) {

        setPhotoStatus(
            photoType,
            "Vous devez être connecté.",
            "error"
        );


        return;
    }


    elements.input.disabled =
        true;


    elements.replaceButton.disabled =
        true;


    setPhotoStatus(
        photoType,
        "Upload de la photo..."
    );


    try {

        const {
            data: oldPhoto,
            error: oldPhotoError
        } =
            await supabaseClient
                .from(
                    "profile_photos"
                )
                .select(
                    "id,storage_path"
                )
                .eq(
                    "user_id",
                    user.id
                )
                .eq(
                    "photo_type",
                    photoType
                )
                .maybeSingle();


        if (oldPhotoError) {

            console.error(
                "Erreur recherche ancienne photo :",
                oldPhotoError
            );


            setPhotoStatus(
                photoType,
                "Impossible de préparer le remplacement.",
                "error"
            );


            return;
        }


        const extension =
            getFileExtension(
                file.type
            );


        const timestamp =
            Date.now();


        const storagePath =
            `${user.id}/${photoType}-${timestamp}.${extension}`;


        const {
            error: uploadError
        } =
            await supabaseClient
                .storage
                .from(
                    PHOTO_BUCKET
                )
                .upload(
                    storagePath,
                    file,
                    {
                        contentType:
                            file.type,

                        upsert:
                            false
                    }
                );


        if (uploadError) {

            console.error(
                "Erreur upload photo :",
                uploadError
            );


            setPhotoStatus(
                photoType,
                "Erreur lors de l'envoi de la photo : " +
                uploadError.message,
                "error"
            );


            return;
        }


        const {
            error: databaseError
        } =
            await supabaseClient
                .from(
                    "profile_photos"
                )
                .upsert(
                    {
                        user_id:
                            user.id,

                        photo_type:
                            photoType,

                        storage_path:
                            storagePath
                    },
                    {
                        onConflict:
                            "user_id,photo_type"
                    }
                );


        if (databaseError) {

            console.error(
                "Erreur base de données photo :",
                databaseError
            );


            await supabaseClient
                .storage
                .from(
                    PHOTO_BUCKET
                )
                .remove([
                    storagePath
                ]);


            setPhotoStatus(
                photoType,
                "La photo n'a pas pu être enregistrée.",
                "error"
            );


            return;
        }


        if (
            oldPhoto &&
            oldPhoto.storage_path &&
            oldPhoto.storage_path !== storagePath
        ) {

            const {
                error: deleteError
            } =
                await supabaseClient
                    .storage
                    .from(
                        PHOTO_BUCKET
                    )
                    .remove([
                        oldPhoto.storage_path
                    ]);


            if (deleteError) {

                console.warn(
                    "Ancienne photo non supprimée :",
                    deleteError
                );

            }

        }


        await displayPhoto(
            photoType,
            storagePath
        );


        elements.input.value =
            "";

    }


    catch (error) {

        console.error(
            "Erreur inattendue upload photo :",
            error
        );


        setPhotoStatus(
            photoType,
            "Une erreur inattendue s'est produite.",
            "error"
        );

    }


    finally {

        elements.input.disabled =
            false;


        elements.replaceButton.disabled =
            false;
    }

}


// ============================================================
// LISTENERS PHOTOS
// ============================================================

Object.keys(
    PHOTO_CONFIG
).forEach(
    function (photoType) {

        const elements =
            getPhotoElements(
                photoType
            );


        if (!elements) {
            return;
        }


        elements.input.addEventListener(
            "change",
            async function () {

                const file =
                    elements.input.files &&
                    elements.input.files.length > 0
                        ? elements.input.files[0]
                        : null;


                if (!file) {
                    return;
                }


                await uploadProfilePhoto(
                    photoType,
                    file
                );

            }
        );


        elements.replaceButton.addEventListener(
            "click",
            function () {

                elements.input.click();

            }
        );

    }
);


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


// ============================================================
// INSCRIPTION
// ============================================================

// ============================================================

signupButton.addEventListener(
    "click",
    async function () {

        const email =
            emailInput.value.trim();


        const password =
            passwordInput.value;


        if (
            !email ||
            !password
        ) {

            showMessage(
                "Veuillez saisir votre email et votre mot de passe."
            );


            return;
        }


        if (
            password.length < 6
        ) {

            showMessage(
                "Le mot de passe doit contenir au moins 6 caractères."
            );


            return;
        }

        // Confirmation supplémentaire pour éviter une inscription
        // accidentelle, notamment sur écran mobile.
        const confirmSignup = window.confirm(
            "Vous allez lancer une nouvelle inscription.\n\n" +
            "Si vous avez déjà un compte, cliquez sur Annuler puis sur « Se connecter ».\n\n" +
            "Voulez-vous continuer ?"
        );

        if (!confirmSignup) {
            return;
        }


        signupButton.disabled =
            true;


        loginButton.disabled =
            true;


        showMessage(
            "Création du compte..."
        );


        try {

            const {
                data,
                error
            } =
                await supabaseClient
                    .auth
                    .signUp({

                        email:
                            email,

                        password:
                            password

                    });


            if (error) {

                console.error(
                    "Erreur inscription :",
                    error
                );

                const signupErrorCode = String(
                    error.code || ""
                ).toLowerCase();

                const signupErrorMessage = String(
                    error.message || ""
                ).toLowerCase();

                const duplicateOrObfuscatedSignup =
                    [
                        "user_already_exists",
                        "user_already_registered",
                        "email_exists",
                        "user_exists"
                    ].includes(signupErrorCode) ||
                    signupErrorMessage.includes("user already registered") ||
                    signupErrorMessage.includes("user already exists") ||
                    signupErrorMessage.includes("email address already exists");

                if (duplicateOrObfuscatedSignup) {
                    // Ne pas révéler publiquement si une adresse est enregistrée.
                    showMessage(
                        "Impossible de finaliser cette demande d'inscription. " +
                        "Si vous avez déjà un compte, utilisez « Se connecter » " +
                        "avec votre mot de passe habituel. Sinon, vérifiez les " +
                        "informations saisies et réessayez."
                    );
                } else {
                    showMessage(
                        "Erreur lors de la création du compte : " +
                        error.message
                    );
                }

                return;
            }


            if (!data.session) {

                // Avec la confirmation d'e-mail activée, Supabase peut renvoyer
                // une réponse obfusquée lorsqu'une adresse existe déjà.
                // L'absence de session ne prouve donc pas qu'un compte vient
                // d'être créé : ne jamais afficher un faux succès.
                showMessage(
                    "Nous ne pouvons pas confirmer qu'un nouveau compte a été créé, " +
                    "et vous n'êtes pas connecté. Si vous avez déjà un compte, " +
                    "cliquez sur « Se connecter » avec votre mot de passe habituel. " +
                    "S'il s'agit de votre première inscription, vérifiez votre boîte " +
                    "e-mail pour un éventuel lien de confirmation."
                );


                return;
            }


            showLoggedIn(
                data.user
            );


            await loadProfile();


            await loadProfilePhotos();


            await updatePushUI();


            await updateAdminUI();


            showMessage(
                "Compte créé avec succès."
            );

        }


        catch (error) {

            console.error(
                "Erreur inattendue :",
                error
            );


            showMessage(
                "Une erreur inattendue s'est produite."
            );

        }


        finally {

            signupButton.disabled =
                false;


            loginButton.disabled =
                false;

        }

    }
);


// ============================================================
// MOT DE PASSE OUBLIÉ
// ============================================================

if (forgotPasswordButton) {
    forgotPasswordButton.addEventListener("click", async function () {
        const email = emailInput.value.trim();

        if (!email) {
            showMessage("Saisissez d'abord l'adresse e-mail associée à votre compte.");
            emailInput.focus();
            return;
        }

        if (!emailInput.checkValidity()) {
            showMessage("Veuillez saisir une adresse e-mail valide.");
            emailInput.focus();
            return;
        }

        forgotPasswordButton.disabled = true;
        showMessage("Envoi de la demande de récupération...");

        try {
            const redirectTo =
                `${window.location.origin}${window.location.pathname}?mode=recovery`;

            const { error } = await supabaseClient.auth.resetPasswordForEmail(
                email,
                { redirectTo }
            );

            if (error) {
                console.error("Erreur récupération du mot de passe :", error);
                showMessage(
                    "Impossible d'envoyer la demande pour le moment. " +
                    "Vérifiez l'adresse et réessayez plus tard."
                );
                return;
            }

            // Message volontairement générique pour ne pas révéler
            // si cette adresse correspond à un compte enregistré.
            showMessage(
                "Si un compte utilise cette adresse, un lien de récupération " +
                "vient d'être envoyé. Vérifiez votre boîte de réception et vos indésirables."
            );
        } catch (error) {
            console.error("Erreur inattendue lors de la récupération :", error);
            showMessage(
                "Impossible d'envoyer la demande pour le moment. Réessayez plus tard."
            );
        } finally {
            forgotPasswordButton.disabled = false;
        }
    });
}


// ============================================================
// ENREGISTRER LE NOUVEAU MOT DE PASSE
// ============================================================

if (resetPasswordButton) {
    resetPasswordButton.addEventListener("click", async function () {
        const newPassword = newPasswordInput.value;
        const confirmPassword = confirmNewPasswordInput.value;

        if (!newPassword || !confirmPassword) {
            showMessage("Saisissez puis confirmez votre nouveau mot de passe.");
            return;
        }

        if (newPassword.length < 6) {
            showMessage("Le mot de passe doit contenir au moins 6 caractères.");
            return;
        }

        if (newPassword !== confirmPassword) {
            showMessage("Les deux mots de passe ne correspondent pas.");
            confirmNewPasswordInput.focus();
            return;
        }

        resetPasswordButton.disabled = true;
        showMessage("Mise à jour du mot de passe...");

        try {
            const { data, error } = await supabaseClient.auth.updateUser({
                password: newPassword
            });

            if (error) {
                console.error("Erreur mise à jour du mot de passe :", error);
                showMessage(
                    "Le lien de récupération a peut-être expiré. " +
                    "Demandez un nouveau lien et réessayez."
                );
                return;
            }

            passwordRecoveryMode = false;
            hidePasswordResetForm();

            // Retire les paramètres de retour de l'URL après utilisation.
            window.history.replaceState(
                {},
                document.title,
                window.location.pathname
            );

            newPasswordInput.value = "";
            confirmNewPasswordInput.value = "";

            showLoggedIn(data.user);
            await loadProfile();
            await loadProfilePhotos();
            await updatePushUI();
            await updateAdminUI();

            showMessage("Votre mot de passe a été mis à jour. Vous êtes connecté(e).");
        } catch (error) {
            console.error("Erreur inattendue lors du changement de mot de passe :", error);
            showMessage("Une erreur inattendue s'est produite. Réessayez.");
        } finally {
            resetPasswordButton.disabled = false;
        }
    });
}


// ============================================================
// CONNEXION
// ============================================================

loginButton.addEventListener(
    "click",
    async function () {

        const email =
            emailInput.value.trim();


        const password =
            passwordInput.value;


        if (
            !email ||
            !password
        ) {

            showMessage(
                "Veuillez saisir votre email et votre mot de passe."
            );


            return;
        }


        signupButton.disabled =
            true;


        loginButton.disabled =
            true;


        showMessage(
            "Connexion..."
        );


        try {

            const {
                data,
                error
            } =
                await supabaseClient
                    .auth
                    .signInWithPassword({

                        email:
                            email,

                        password:
                            password

                    });


            if (error) {

                console.error(
                    "Erreur connexion :",
                    error
                );


                showMessage(
                    "Erreur de connexion : " +
                    error.message
                );


                return;
            }


            showLoggedIn(
                data.user
            );


            await loadProfile();


            await loadProfilePhotos();


            await updatePushUI();


            await updateAdminUI();

        }


        catch (error) {

            console.error(
                "Erreur inattendue :",
                error
            );


            showMessage(
                "Une erreur inattendue s'est produite."
            );

        }


        finally {

            signupButton.disabled =
                false;


            loginButton.disabled =
                false;

        }

    }
);


// ============================================================
// CHARGER PROFIL
// ============================================================

async function loadProfile() {

    const {
        data: userData,
        error: userError
    } =
        await supabaseClient
            .auth
            .getUser();


    if (userError) {

        console.error(
            "Erreur récupération utilisateur :",
            userError
        );


        return;
    }


    const user =
        userData.user;


    if (!user) {
        return;
    }


    profileEmailInput.value =
        user.email || "";


    const {
        data,
        error
    } =
        await supabaseClient
            .from(
                "profiles"
            )
            .select("*")
            .eq(
                "id",
                user.id
            )
            .maybeSingle();


    if (error) {

        console.error(
            "Erreur chargement profil :",
            error
        );


        showMessage(
            "Impossible de charger votre profil : " +
            error.message
        );


        return;
    }


    if (!data) {

        updateDisplayedAge();

        return;
    }


    document.getElementById(
        "first-name"
    ).value =
        data.first_name || "";


    document.getElementById(
        "last-name"
    ).value =
        data.last_name || "";


    document.getElementById(
        "phone"
    ).value =
        data.phone || "";


    document.getElementById(
        "birth-date"
    ).value =
        data.birth_date || "";


    document.getElementById(
        "gender"
    ).value =
        data.gender || "";


    document.getElementById(
        "address"
    ).value =
        data.address || "";


    document.getElementById(
        "city"
    ).value =
        data.city || "";


    document.getElementById(
        "height"
    ).value =
        data.height_cm || "";


    document.getElementById(
        "shoe-size"
    ).value =
        data.shoe_size || "";


    document.getElementById(
        "clothing-size"
    ).value =
        data.clothing_size || "";


    document.getElementById(
        "profession"
    ).value =
        data.profession || "";


    updateDisplayedAge();


    console.log(
        "Profil chargé."
    );

}


// ============================================================
// ENREGISTRER PROFIL
// ============================================================

saveProfileButton.addEventListener(
    "click",
    async function () {

        saveProfileButton.disabled =
            true;


        clearProfileSaveMessage();


        showMessage(
            "Enregistrement du profil..."
        );


        try {

            const user =
                await getCurrentUser();


            if (!user) {

                showMessage(
                    "Vous devez être connecté pour enregistrer votre profil."
                );


                showProfileSaveMessage(
                    "Vous devez être connecté."
                );


                return;
            }


            const firstName =
                document
                    .getElementById(
                        "first-name"
                    )
                    .value
                    .trim();


            const lastName =
                document
                    .getElementById(
                        "last-name"
                    )
                    .value
                    .trim();


            const phone =
                document
                    .getElementById(
                        "phone"
                    )
                    .value
                    .trim();


            const birthDate =
                document
                    .getElementById(
                        "birth-date"
                    )
                    .value;


            const gender =
                document
                    .getElementById(
                        "gender"
                    )
                    .value;


            const address =
                document
                    .getElementById(
                        "address"
                    )
                    .value
                    .trim();


            const city =
                document
                    .getElementById(
                        "city"
                    )
                    .value
                    .trim();


            const height =
                document
                    .getElementById(
                        "height"
                    )
                    .value;


            const shoeSize =
                document
                    .getElementById(
                        "shoe-size"
                    )
                    .value
                    .trim();


            const clothingSize =
                document
                    .getElementById(
                        "clothing-size"
                    )
                    .value
                    .trim();


            const profession =
                document
                    .getElementById(
                        "profession"
                    )
                    .value
                    .trim();


            if (!firstName) {

                showMessage(
                    "Veuillez renseigner votre prénom."
                );


                showProfileSaveMessage(
                    "Veuillez renseigner votre prénom."
                );


                return;
            }


            if (!lastName) {

                showMessage(
                    "Veuillez renseigner votre nom."
                );


                showProfileSaveMessage(
                    "Veuillez renseigner votre nom."
                );


                return;
            }


            if (!birthDate) {

                showMessage(
                    "Veuillez renseigner votre date de naissance."
                );


                showProfileSaveMessage(
                    "Veuillez renseigner votre date de naissance."
                );


                return;
            }


            if (!gender) {

                showMessage(
                    "Veuillez sélectionner votre sexe."
                );


                showProfileSaveMessage(
                    "Veuillez sélectionner votre sexe."
                );


                return;
            }


            if (!city) {

                showMessage(
                    "Veuillez renseigner votre ville."
                );


                showProfileSaveMessage(
                    "Veuillez renseigner votre ville."
                );


                return;
            }


            updateDisplayedAge();


            const profileData = {

                id:
                    user.id,

                first_name:
                    firstName,

                last_name:
                    lastName,

                email:
                    user.email,

                phone:
                    phone || null,

                birth_date:
                    birthDate,

                gender:
                    gender,

                address:
                    address || null,

                city:
                    city,

                height_cm:
                    height
                        ? parseInt(
                            height,
                            10
                        )
                        : null,

                shoe_size:
                    shoeSize || null,

                clothing_size:
                    clothingSize || null,

                profession:
                    profession || null,

                updated_at:
                    new Date().toISOString()

            };


            const {
                error
            } =
                await supabaseClient
                    .from(
                        "profiles"
                    )
                    .upsert(
                        profileData,
                        {
                            onConflict:
                                "id"
                        }
                    );


            if (error) {

                console.error(
                    "Erreur enregistrement profil :",
                    error
                );


                showMessage(
                    "Erreur lors de l'enregistrement : " +
                    error.message
                );


                showProfileSaveMessage(
                    "Erreur lors de l'enregistrement : " +
                    error.message
                );


                return;
            }


            const successMessage =
                "✓ Votre profil a été enregistré avec succès.";


            showMessage(
                successMessage
            );


            showProfileSaveMessage(
                successMessage
            );

        }


        catch (error) {

            console.error(
                "Erreur inattendue :",
                error
            );


            const errorMessage =
                "Une erreur inattendue s'est produite.";


            showMessage(
                errorMessage
            );


            showProfileSaveMessage(
                errorMessage
            );

        }


        finally {

            saveProfileButton.disabled =
                false;

        }

    }
);


// ============================================================
// DÉCONNEXION
// ============================================================

logoutButton.addEventListener(
    "click",
    async function () {

        logoutButton.disabled =
            true;


        try {

            const {
                error
            } =
                await supabaseClient
                    .auth
                    .signOut();


            if (error) {

                console.error(
                    "Erreur déconnexion :",
                    error
                );


                showMessage(
                    "Erreur lors de la déconnexion : " +
                    error.message
                );


                return;
            }


            showLoggedOut();


            emailInput.value =
                "";


            passwordInput.value =
                "";

        }


        catch (error) {

            console.error(
                "Erreur inattendue :",
                error
            );


            showMessage(
                "Une erreur inattendue s'est produite."
            );

        }


        finally {

            logoutButton.disabled =
                false;

        }

    }
);


// ============================================================
// SESSION AU CHARGEMENT
// ============================================================

async function checkCurrentSession() {

    try {

        const {
            data,
            error
        } =
            await supabaseClient
                .auth
                .getSession();


        if (error) {

            console.error(
                "Erreur récupération session :",
                error
            );


            showLoggedOut();


            return;
        }


        if (passwordRecoveryMode) {

            showPasswordResetForm();
            showMessage(
                "Choisissez un nouveau mot de passe, puis confirmez-le."
            );
            return;

        }


        if (data.session) {

            showLoggedIn(
                data.session.user
            );


            await loadProfile();


            await loadProfilePhotos();


            await updatePushUI();


            await updateAdminUI();

        }
        else {

            showLoggedOut();

        }

    }


    catch (error) {

        console.error(
            "Erreur inattendue :",
            error
        );


        showLoggedOut();

    }

}


// ============================================================
// CHANGEMENTS AUTH
// ============================================================

supabaseClient.auth.onAuthStateChange(
    async function (
        event,
        session
    ) {

        console.log(
            "Auth event :",
            event
        );


        if (event === "PASSWORD_RECOVERY") {
            passwordRecoveryMode = true;
            showPasswordResetForm();
            showMessage(
                "Lien de récupération validé. Choisissez votre nouveau mot de passe."
            );
            return;
        }


        if (passwordRecoveryMode) {
            showPasswordResetForm();
            return;
        }


        if (session) {

            showLoggedIn(
                session.user
            );


            await loadProfile();


            await loadProfilePhotos();


            await updatePushUI();


            await updateAdminUI();

        }
        else if (
            event === "SIGNED_OUT"
        ) {

            showLoggedOut();

        }

    }
);


// ============================================================
// DÉMARRAGE
// ============================================================

checkCurrentSession();
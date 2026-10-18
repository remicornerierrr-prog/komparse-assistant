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

// Après connexion, n'autoriser qu'une destination interne connue.
// Cela évite les redirections ouvertes vers des sites externes.
function redirectToRequestedRoute() {
    const requestedRoute = new URLSearchParams(window.location.search).get("next");

    if (requestedRoute !== "admin.html") {
        return false;
    }

    const destination = new URL("./admin.html", window.location.href);
    if (destination.origin !== window.location.origin) {
        return false;
    }

    window.location.replace(destination.toString());
    return true;
}


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

const candidateSidebar = document.querySelector(".candidate-sidebar");

function setCandidateNavigationVisible(visible) {
    if (!candidateSidebar) return;
    candidateSidebar.style.display = visible
        ? (window.matchMedia("(max-width: 1049px)").matches ? "grid" : "block")
        : "none";
    candidateSidebar.setAttribute("aria-hidden", visible ? "false" : "true");
}

const candidateDashboardPanels = Array.from(
    document.querySelectorAll("[data-dashboard-panel]")
);
const candidateDashboardLinks = Array.from(
    document.querySelectorAll("[data-dashboard-view]")
);

function setCandidateDashboardView(view) {
    const selectedLinks = candidateDashboardLinks.filter(
        (link) => link.dataset.dashboardView === view
    );

    if (!selectedLinks.length) return;

    for (const panel of candidateDashboardPanels) {
        panel.hidden = panel.dataset.dashboardPanel !== view;
    }

    for (const link of candidateDashboardLinks) {
        const selected = link.dataset.dashboardView === view;
        link.classList.toggle("active", selected && link.closest(".candidate-sidebar"));
        if (link.closest(".candidate-sidebar")) {
            if (selected) {
                link.setAttribute("aria-current", "page");
            } else {
                link.removeAttribute("aria-current");
            }
        }
    }
}

document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-dashboard-view]");
    if (!link || profileSection.classList.contains("hidden")) return;

    event.preventDefault();
    setCandidateDashboardView(link.dataset.dashboardView);

    if (link.hash) {
        window.history.replaceState(null, "", link.hash);
    }
});

setCandidateDashboardView("profile");


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


// Le lien doit contenir un code/token de callback Supabase pour
// autoriser la réinitialisation. Le simple paramètre ?mode=recovery
// ne prouve pas que le lien est valide.
const authQueryParams = new URLSearchParams(window.location.search);
const authHashText = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
const authHashParams = new URLSearchParams(authHashText);

const recoveryModeRequested =
    authQueryParams.get("mode") === "recovery";

const recoveryCallbackHasCredentials =
    authQueryParams.has("code") ||
    authHashParams.has("access_token") ||
    authHashParams.get("type") === "recovery";

const recoveryCallbackHasError =
    authQueryParams.has("error") ||
    authQueryParams.has("error_code") ||
    authHashParams.has("error") ||
    authHashParams.has("error_code");

let passwordRecoveryMode = false;
let recoverySessionReady = false;


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

function showMessage(message, type = "") {
    if (!messageElement) {
        return;
    }

    messageElement.textContent = message;
    messageElement.style.display = "block";
    messageElement.classList.remove(
        "message-error",
        "message-info",
        "message-success"
    );

    if (type === "error" || type === "info" || type === "success") {
        messageElement.classList.add(`message-${type}`);
    }

    messageElement.setAttribute(
        "role",
        type === "error" ? "alert" : "status"
    );
}

function clearMessage() {
    if (!messageElement) {
        return;
    }

    messageElement.textContent = "";
    messageElement.style.display = "none";
    messageElement.classList.remove(
        "message-error",
        "message-info",
        "message-success"
    );
    messageElement.setAttribute("role", "status");
}

function cleanAuthCallbackUrl() {
    window.history.replaceState(
        {},
        document.title,
        window.location.pathname
    );
}

function showInvalidRecoveryLink(message = "Le lien de récupération est invalide ou a expiré. Demandez un nouveau lien puis ouvrez le dernier e-mail reçu.") {
    recoverySessionReady = false;
    passwordRecoveryMode = false;
    hidePasswordResetForm();
    cleanAuthCallbackUrl();
    showLoggedOut();
    showMessage(message, "error");
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

    setCandidateNavigationVisible(false);


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

    setCandidateDashboardView("profile");
    setCandidateNavigationVisible(true);


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


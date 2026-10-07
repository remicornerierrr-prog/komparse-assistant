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
// ÉTAT DES NOTIFICATIONS
// ============================================================

async function updatePushUI() {

    if (!enablePushButton) {
        return;
    }


    if (
        !isPushSupported()
    ) {

        enablePushButton.disabled =
            true;


        enablePushButton.textContent =
            "Notifications non disponibles";


        showPushStatus(
            "Les notifications push ne sont pas prises en charge par ce navigateur.",
            "error"
        );


        return;
    }


    const permission =
        getNotificationPermission();


    if (
        permission === "denied"
    ) {

        enablePushButton.textContent =
            "Notifications bloquées";


        showPushStatus(
            "Les notifications sont bloquées dans les paramètres du navigateur.",
            "error"
        );


        return;
    }


    try {

        const registration =
            await getPushRegistration();


        const subscription =
            await getExistingPushSubscription(
                registration
            );


        if (
            subscription
        ) {

            enablePushButton.textContent =
                "✓ Notifications activées";


            showPushStatus(
                "Votre navigateur est déjà abonné aux notifications push.",
                "success"
            );


            return;
        }


    }


    catch (error) {

        console.error(
            "Erreur vérification abonnement push :",
            error
        );

    }


    enablePushButton.textContent =
        "🔔 Activer les notifications";


    showPushStatus(
        "Les notifications ne sont pas encore activées.",
        "info"
    );

}


// ============================================================
// ENREGISTRER L'ABONNEMENT DANS SUPABASE
// ============================================================

async function savePushSubscription(
    subscription
) {

    const user =
        await getCurrentUser();


    if (!user) {

        throw new Error(
            "Vous devez être connecté."
        );

    }


    // --------------------------------------------------------
    // V1 :
    // un abonnement actif par utilisateur.
    //
    // On supprime d'abord l'ancien abonnement éventuel.
    // --------------------------------------------------------

    const {
        error: deleteError
    } =
        await supabaseClient
            .from(
                "push_subscriptions"
            )
            .delete()
            .eq(
                "user_id",
                user.id
            );


    if (deleteError) {

        console.error(
            "Erreur suppression ancien abonnement :",
            deleteError
        );


        throw new Error(
            "Impossible de mettre à jour votre abonnement push."
        );

    }


    // --------------------------------------------------------
    // Insérer le nouvel abonnement
    // --------------------------------------------------------

    const {
        error: insertError
    } =
        await supabaseClient
            .from(
                "push_subscriptions"
            )
            .insert(
                {
                    user_id:
                        user.id,

                    subscription_json:
                        subscription
                }
            );


    if (insertError) {

        console.error(
            "Erreur enregistrement abonnement push :",
            insertError
        );


        throw new Error(
            "Impossible d'enregistrer votre abonnement push : " +
            insertError.message
        );

    }

}


// ============================================================
// ACTIVER LES NOTIFICATIONS
// ============================================================

enablePushButton.addEventListener(
    "click",
    async function () {

        enablePushButton.disabled =
            true;


        showPushStatus(
            "Activation des notifications...",
            "info"
        );


        try {

            const user =
                await getCurrentUser();


            if (!user) {

                throw new Error(
                    "Vous devez être connecté pour activer les notifications."
                );

            }


            const registration =
                await getPushRegistration();


            const subscription =
                await subscribeToPush(
                    registration
                );


            if (
                !subscription
            ) {

                throw new Error(
                    "Aucun abonnement push n'a été créé."
                );

            }


            await savePushSubscription(
                subscription
            );


            enablePushButton.textContent =
                "✓ Notifications activées";


            showPushStatus(
                "✓ Notifications activées avec succès.",
                "success"
            );


            console.log(
                "Abonnement Push enregistré :",
                subscription
            );

        }


        catch (error) {

            console.error(
                "Erreur activation push :",
                error
            );


            enablePushButton.disabled =
                false;


            showPushStatus(
                error.message ||
                "Impossible d'activer les notifications.",
                "error"
            );

        }

    }
);


// ============================================================
// INSCRIPTION
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


                showMessage(
                    "Erreur lors de la création du compte : " +
                    error.message
                );


                return;
            }


            if (!data.session) {

                showMessage(
                    "Compte créé avec succès. " +
                    "Vérifiez votre boîte email et cliquez sur le lien de confirmation."
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
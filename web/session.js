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
        let { data, error } = await supabaseClient.auth.getSession();

        if (error) {
            console.error("Erreur récupération session :", error);
            if (recoveryModeRequested) {
                showInvalidRecoveryLink(
                    "Impossible de valider le lien de récupération. Demandez un nouveau lien puis réessayez."
                );
            } else {
                showLoggedOut();
            }
            return;
        }

        if (recoveryModeRequested) {
            if (recoveryCallbackHasError) {
                showInvalidRecoveryLink();
                return;
            }

            if (!recoveryCallbackHasCredentials) {
                showInvalidRecoveryLink(
                    "Aucun jeton de récupération n'a été trouvé. Demandez un nouveau lien depuis « Mot de passe oublié ? » puis ouvrez le dernier e-mail reçu."
                );
                return;
            }

            // L'échange du code PKCE peut finir juste après le chargement.
            if (!data.session) {
                await new Promise(resolve => setTimeout(resolve, 500));
                const retry = await supabaseClient.auth.getSession();
                if (!retry.error) {
                    data = retry.data;
                }
            }

            if (data.session) {
                recoverySessionReady = true;
                passwordRecoveryMode = true;
                showPasswordResetForm();
                showMessage(
                    "Lien de récupération validé. Choisissez votre nouveau mot de passe.",
                    "success"
                );
            } else {
                showInvalidRecoveryLink();
            }

            return;
        }

        if (data.session) {
            showLoggedIn(data.session.user);
            await loadProfile();
            await loadProfilePhotos();
            await updatePushUI();
            await updateAdminUI();
        } else {
            showLoggedOut();
        }
    } catch (error) {
        console.error("Erreur inattendue :", error);
        if (recoveryModeRequested) {
            showInvalidRecoveryLink(
                "Impossible de valider le lien de récupération. Demandez un nouveau lien puis réessayez."
            );
        } else {
            showLoggedOut();
        }
    }
}

// ============================================================
// CHANGEMENTS AUTH
// ============================================================

supabaseClient.auth.onAuthStateChange(
    async function (event, session) {
        console.log("Auth event :", event);

        if (event === "PASSWORD_RECOVERY") {
            if (!session) {
                showInvalidRecoveryLink();
                return;
            }

            recoverySessionReady = true;
            passwordRecoveryMode = true;
            showPasswordResetForm();
            showMessage(
                "Lien de récupération validé. Choisissez votre nouveau mot de passe.",
                "success"
            );
            return;
        }

        // Pour le flux PKCE, l'échange peut être signalé comme INITIAL_SESSION
        // ou SIGNED_IN. On n'accepte cette session que si le navigateur vient
        // réellement du callback de récupération (code/token présent à l'arrivée).
        if (
            recoveryModeRequested &&
            recoveryCallbackHasCredentials &&
            session
        ) {
            recoverySessionReady = true;
            passwordRecoveryMode = true;
            showPasswordResetForm();
            return;
        }

        if (passwordRecoveryMode) {
            if (recoverySessionReady) {
                showPasswordResetForm();
            }
            return;
        }

        if (session) {
            showLoggedIn(session.user);
            await loadProfile();
            await loadProfilePhotos();
            await updatePushUI();
            await updateAdminUI();
        } else if (event === "SIGNED_OUT") {
            showLoggedOut();
        }
    }
);

// ============================================================
// DÉMARRAGE
// ============================================================

checkCurrentSession();
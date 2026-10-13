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
            showMessage("Saisissez puis confirmez votre nouveau mot de passe.", "error");
            return;
        }

        if (newPassword.length < 6) {
            showMessage("Le mot de passe doit contenir au moins 6 caractères.", "error");
            newPasswordInput.focus();
            return;
        }

        if (newPassword !== confirmPassword) {
            showMessage("Les deux mots de passe ne correspondent pas.", "error");
            confirmNewPasswordInput.focus();
            return;
        }

        resetPasswordButton.disabled = true;
        showMessage("Vérification du lien et mise à jour du mot de passe...", "info");

        try {
            // updateUser() exige une session authentifiée créée par le
            // lien de récupération. Ne pas présenter le formulaire comme
            // valide uniquement parce que l'URL contient mode=recovery.
            const { data: sessionData, error: sessionError } =
                await supabaseClient.auth.getSession();

            if (sessionError) {
                console.error("Erreur de session de récupération :", sessionError);
                showMessage(
                    "Impossible de vérifier la session de récupération. Demandez un nouveau lien et réessayez.",
                    "error"
                );
                return;
            }

            if (!recoverySessionReady || !sessionData.session) {
                showInvalidRecoveryLink();
                return;
            }

            const { data, error } = await supabaseClient.auth.updateUser({
                password: newPassword
            });

            if (error) {
                console.error("Erreur mise à jour du mot de passe :", error);
                const errorText = `${error.code || ""} ${error.message || ""}`.toLowerCase();

                if (
                    errorText.includes("session missing") ||
                    errorText.includes("invalid token") ||
                    errorText.includes("expired") ||
                    errorText.includes("otp_expired") ||
                    errorText.includes("refresh token") ||
                    error.status === 401
                ) {
                    showInvalidRecoveryLink();
                } else if (
                    errorText.includes("different from the old password") ||
                    errorText.includes("should be different")
                ) {
                    showMessage(
                        "Choisissez un mot de passe différent de votre ancien mot de passe.",
                        "error"
                    );
                } else if (
                    errorText.includes("weak password") ||
                    errorText.includes("password should") ||
                    errorText.includes("password must") ||
                    errorText.includes("minimum password")
                ) {
                    showMessage(
                        "Ce mot de passe ne respecte pas les exigences de sécurité. Choisissez-en un autre, plus robuste.",
                        "error"
                    );
                } else {
                    // Afficher une erreur informative au lieu de supposer
                    // que tous les échecs signifient que le lien a expiré.
                    showMessage(
                        `Impossible de mettre à jour le mot de passe : ${error.message || "erreur inconnue"}`,
                        "error"
                    );
                }
                return;
            }

            passwordRecoveryMode = false;
            recoverySessionReady = false;
            hidePasswordResetForm();
            cleanAuthCallbackUrl();

            newPasswordInput.value = "";
            confirmNewPasswordInput.value = "";

            showLoggedIn(data.user);
            await loadProfile();
            await loadProfilePhotos();
            await updatePushUI();
            await updateAdminUI();

            showMessage("Votre mot de passe a été mis à jour. Vous êtes connecté(e).", "success");
        } catch (error) {
            console.error("Erreur inattendue lors du changement de mot de passe :", error);
            showMessage(
                "Une erreur inattendue s'est produite pendant la mise à jour. Réessayez.",
                "error"
            );
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



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

    document.getElementById("notify-national").checked =
        data.notify_national !== false;

    document.getElementById("notify-regional").checked =
        data.notify_regional !== false;

    document.getElementById("notify-region").value =
        data.notify_region || "";


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

            const notifyNational =
                document.getElementById("notify-national").checked;

            const notifyRegional =
                document.getElementById("notify-regional").checked;

            const notifyRegion =
                document.getElementById("notify-region").value;

            if (!notifyNational && !notifyRegional && !notifyRegion) {
                showMessage(
                    "Veuillez choisir au moins un type d'annonce : nationale et/ou régionale."
                );
                showProfileSaveMessage(
                    "Veuillez choisir au moins un type d'annonce."
                );
                return;
            }


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

                notify_national:
                    notifyNational,

                notify_regional:
                    notifyRegional,

                notify_region:
                    notifyRegion || null,

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



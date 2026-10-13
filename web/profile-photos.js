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



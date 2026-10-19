// ============================================================
// VALIDATION PHOTO
// ============================================================

const uploadedPhotoTypes = new Set();


function renderProfilePhotoInputs() {
    const container = document.getElementById("profile-photo-list");

    if (!container) {
        return;
    }

    for (const [photoType, config] of Object.entries(PHOTO_CONFIG)) {
        const card = document.createElement("div");
        card.className = "photo-upload";
        card.dataset.photoType = photoType;

        const title = document.createElement("label");
        title.htmlFor = config.inputId;
        title.textContent = config.label;
        card.append(title);

        const previewContainer = document.createElement("div");
        previewContainer.className = "photo-preview-container";
        const preview = document.createElement("img");
        preview.id = config.previewId;
        preview.className = `photo-preview ${config.previewClass || ""} hidden`.trim();
        preview.alt = `Aperçu : ${config.label.toLowerCase()}`;
        previewContainer.append(preview);
        card.append(previewContainer);

        const fileControl = document.createElement("div");
        fileControl.className = "photo-file-control";
        const input = document.createElement("input");
        input.type = "file";
        input.id = config.inputId;
        input.className = "photo-file-input";
        input.accept = ALLOWED_PHOTO_TYPES.join(",");
        fileControl.append(input);

        const chooseButton = document.createElement("label");
        chooseButton.className = "photo-file-button";
        chooseButton.htmlFor = config.inputId;
        chooseButton.textContent = "Choisir un fichier";
        fileControl.append(chooseButton);

        const fileName = document.createElement("span");
        fileName.className = "photo-file-name";
        fileName.dataset.i18n = "Aucun fichier choisi";
        fileName.setAttribute("aria-live", "polite");
        fileName.textContent = "Aucun fichier choisi";
        fileControl.append(fileName);
        card.append(fileControl);

        const replaceButton = document.createElement("button");
        replaceButton.type = "button";
        replaceButton.className = "replace-photo-button hidden";
        replaceButton.dataset.photoType = photoType;
        replaceButton.textContent = "Remplacer";
        card.append(replaceButton);

        const status = document.createElement("div");
        status.id = config.statusId;
        status.className = "photo-status";
        status.setAttribute("role", "status");
        status.setAttribute("aria-live", "polite");
        card.append(status);

        container.append(card);
    }
}


function updateProfilePhotoCount() {
    const count = document.getElementById("profile-photo-count");

    if (count) {
        count.textContent = `${uploadedPhotoTypes.size} photo${uploadedPhotoTypes.size === 1 ? "" : "s"} sur 10`;
    }
}


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


    return {
        valid: true
    };

}


async function compressPhotoFile(file) {
    const objectUrl = URL.createObjectURL(file);

    try {
        const image = new Image();
        image.src = objectUrl;
        await image.decode();

        const maxDimension = 1600;
        const scale = Math.min(
            1,
            maxDimension / Math.max(image.naturalWidth, image.naturalHeight)
        );
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(image.naturalWidth * scale);
        canvas.height = Math.round(image.naturalHeight * scale);

        const context = canvas.getContext("2d");

        if (!context) {
            throw new Error("Impossible de préparer le canevas de compression.");
        }

        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);

        const compressedBlob = await new Promise((resolve, reject) => {
            canvas.toBlob(
                (blob) => {
                    if (!blob) {
                        reject(new Error("La compression de la photo a échoué."));
                        return;
                    }

                    resolve(blob);
                },
                "image/jpeg",
                0.82
            );
        });

        return compressedBlob;
    } finally {
        URL.revokeObjectURL(objectUrl);
    }
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

        fileName:
            document.querySelector(
                `.photo-upload[data-photo-type="${photoType}"] .photo-file-name`
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

function setPhotoFileName(elements, fileName = "") {
    if (fileName) {
        elements.fileName.removeAttribute("data-i18n");
        elements.fileName.textContent = fileName;
        return;
    }

    elements.fileName.setAttribute("data-i18n", "Aucun fichier choisi");
    elements.fileName.textContent = "Aucun fichier choisi";
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


    const uploadErrorPrefix =
        "Erreur lors de l'envoi de la photo : ";

    if (message.startsWith(uploadErrorPrefix)) {
        const prefix = document.createElement("span");
        prefix.dataset.i18n = "Erreur lors de l'envoi de la photo :";
        prefix.textContent = "Erreur lors de l'envoi de la photo :";
        elements.status.replaceChildren(
            prefix,
            document.createTextNode(` ${message.slice(uploadErrorPrefix.length)}`)
        );
    } else {
        elements.status.textContent = message;
    }


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

    setPhotoFileName(elements);

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
    uploadedPhotoTypes.clear();
    updateProfilePhotoCount();


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

        uploadedPhotoTypes.add(photo.photo_type);


        await displayPhoto(
            photo.photo_type,
            photo.storage_path
        );

    }

    updateProfilePhotoCount();

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

        setPhotoFileName(elements);


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
        "Optimisation de la photo..."
    );


    try {

        const compressedFile =
            await compressPhotoFile(file);

        if (compressedFile.size > MAX_PHOTO_SIZE) {
            setPhotoStatus(
                photoType,
                "La photo optimisée dépasse la taille maximale de 5 Mo.",
                "error"
            );

            return;
        }


        setPhotoStatus(
            photoType,
            "Upload de la photo..."
        );


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
                compressedFile.type
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
                    compressedFile,
                    {
                        contentType:
                            compressedFile.type,

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

        uploadedPhotoTypes.add(photoType);
        updateProfilePhotoCount();


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

        setPhotoFileName(elements);

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

renderProfilePhotoInputs();


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

                setPhotoFileName(elements, file ? file.name : "");

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

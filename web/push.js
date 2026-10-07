// ============================================================
// PUSH NOTIFICATIONS — KOMPARSE ASSISTANT
// ============================================================


// ============================================================
// CLÉ PUBLIQUE VAPID
// ============================================================
//
// Mets ici TA clé publique VAPID.
//
// IMPORTANT :
// - publicKey = OUI
// - privateKey = JAMAIS dans ce fichier
// ============================================================

const VAPID_PUBLIC_KEY =
    "BArHhOeRfSB5GkUZr68n-oMVbjCSdadzZ4pMYJDIw5NLxwDhn7JcE6b6WGHi3ni21schDCnLaDxE4-nl80pE2o0";


// ============================================================
// CONVERSION BASE64URL → UINT8ARRAY
// ============================================================

function urlBase64ToUint8Array(
    base64String
) {

    const padding =
        "=".repeat(
            (
                4 -
                (
                    base64String.length % 4
                )
            ) % 4
        );


    const base64 =
        (
            base64String +
            padding
        )
        .replace(
            /-/g,
            "+"
        )
        .replace(
            /_/g,
            "/"
        );


    const rawData =
        window.atob(
            base64
        );


    return Uint8Array.from(
        [...rawData].map(
            function (char) {

                return char.charCodeAt(0);

            }
        )
    );
}


// ============================================================
// VÉRIFIER SI LE PUSH EST SUPPORTÉ
// ============================================================

function isPushSupported() {

    return (
        "serviceWorker" in navigator &&
        "PushManager" in window &&
        "Notification" in window
    );

}


// ============================================================
// OBTENIR LA PERMISSION DE NOTIFICATION
// ============================================================

function getNotificationPermission() {

    if (
        !("Notification" in window)
    ) {

        return "unsupported";

    }


    return Notification.permission;

}


// ============================================================
// S'ABONNER AUX NOTIFICATIONS
// ============================================================

async function subscribeToPush(
    registration
) {

    if (
        !isPushSupported()
    ) {

        throw new Error(
            "Les notifications push ne sont pas prises en charge par ce navigateur."
        );

    }


    // --------------------------------------------------------
    // Vérification clé VAPID
    // --------------------------------------------------------

    if (
        !VAPID_PUBLIC_KEY ||
        VAPID_PUBLIC_KEY ===
        "COLLE_ICI_TA_CLE_PUBLIQUE_VAPID"
    ) {

        throw new Error(
            "La clé publique VAPID n'a pas encore été configurée dans push.js."
        );

    }


    // --------------------------------------------------------
    // Demande de permission
    // --------------------------------------------------------
    //
    // Cette fonction est appelée uniquement après clic
    // de l'utilisateur sur le bouton.
    // --------------------------------------------------------

    const permission =
        await Notification.requestPermission();


    if (
        permission !== "granted"
    ) {

        if (
            permission === "denied"
        ) {

            throw new Error(
                "Permission de notification refusée dans le navigateur."
            );

        }


        throw new Error(
            "La permission de notification n'a pas été accordée."
        );

    }


    // --------------------------------------------------------
    // Chercher un abonnement existant
    // --------------------------------------------------------

    let subscription =
        await registration
            .pushManager
            .getSubscription();


    // --------------------------------------------------------
    // Créer l'abonnement
    // --------------------------------------------------------

    if (!subscription) {

        subscription =
            await registration
                .pushManager
                .subscribe({

                    userVisibleOnly:
                        true,

                    applicationServerKey:
                        urlBase64ToUint8Array(
                            VAPID_PUBLIC_KEY
                        )

                });

    }


    // --------------------------------------------------------
    // Retourner le JSON
    // --------------------------------------------------------

    return subscription.toJSON();

}


// ============================================================
// RÉCUPÉRER L'ABONNEMENT EXISTANT
// ============================================================

async function getExistingPushSubscription(
    registration
) {

    if (
        !registration ||
        !registration.pushManager
    ) {

        return null;

    }


    const subscription =
        await registration
            .pushManager
            .getSubscription();


    if (!subscription) {

        return null;

    }


    return subscription.toJSON();

}
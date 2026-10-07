// ============================================================
// SERVICE WORKER — KOMPARSE ASSISTANT
// ============================================================


// ============================================================
// RÉCEPTION D'UNE NOTIFICATION PUSH
// ============================================================

self.addEventListener(
    "push",
    function (event) {

        let data = {};


        try {

            data =
                event.data
                    ? event.data.json()
                    : {};

        }

        catch (error) {

            console.error(
                "Impossible de lire le payload push :",
                error
            );

        }


        const title =
            data.title ||
            "Nouvelle offre Komparse";


        const body =
            data.body ||
            "Une offre correspondant à votre profil vient d'être publiée.";


        const url =
            data.url ||
            "/";


        event.waitUntil(

            self.registration.showNotification(
                title,
                {

                    body:
                        body,

                    icon:
                        "/icon-192.png",

                    badge:
                        "/icon-192.png",

                    data: {
                        url:
                            url
                    }

                }
            )

        );

    }
);


// ============================================================
// CLIC SUR UNE NOTIFICATION
// ============================================================

self.addEventListener(
    "notificationclick",
    function (event) {

        event.notification.close();


        const target =
            event.notification &&
            event.notification.data &&
            event.notification.data.url
                ? event.notification.data.url
                : "/";


        event.waitUntil(

            clients.matchAll({
                type:
                    "window",
                includeUncontrolled:
                    true
            })

            .then(
                function (clientList) {

                    // ------------------------------------------------
                    // Si l'application est déjà ouverte,
                    // on réutilise sa fenêtre.
                    // ------------------------------------------------

                    for (
                        const client of clientList
                    ) {

                        if (
                            "focus" in client
                        ) {

                            client.navigate(
                                target
                            );

                            return client.focus();
                        }
                    }


                    // ------------------------------------------------
                    // Sinon on ouvre une nouvelle fenêtre.
                    // ------------------------------------------------

                    if (
                        clients.openWindow
                    ) {

                        return clients.openWindow(
                            target
                        );
                    }


                    return undefined;

                }
            )

        );

    }
);


// ============================================================
// INSTALLATION
// ============================================================

self.addEventListener(
    "install",
    function () {

        console.log(
            "Komparse Assistant Service Worker installé."
        );


        self.skipWaiting();

    }
);


// ============================================================
// ACTIVATION
// ============================================================

self.addEventListener(
    "activate",
    function (event) {

        console.log(
            "Komparse Assistant Service Worker activé."
        );


        event.waitUntil(
            self.clients.claim()
        );

    }
);
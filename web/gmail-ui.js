// Gmail OAuth UI. OAuth tokens remain server-side.
(function () {
  const button = document.getElementById("gmail-connect-button");
  const status = document.getElementById("gmail-connection-status");
  if (!button || !status) return;

  const messages = {
    connected: "Gmail a été connecté. L'envoi des candidatures reste à finaliser et tester.",
    cancelled: "Connexion Gmail annulée.",
    not_configured: "La configuration serveur Gmail est incomplète. Vérifiez les secrets Supabase.",
    invalid_callback: "Le retour de Google est incomplet. Réessayez.",
    invalid_state: "La vérification de sécurité a échoué ou a expiré. Relancez la connexion.",
    expired_state: "La demande de connexion a expiré. Réessayez.",
    token_exchange_failed: "Google n'a pas pu finaliser l'autorisation. Vérifiez le client OAuth et l'URI de redirection.",
    email_lookup_failed: "Impossible de récupérer l'adresse Gmail autorisée.",
    encryption_failed: "Le chiffrement des jetons a échoué. Vérifiez le secret de chiffrement Supabase.",
    save_failed: "Gmail a été autorisé mais la connexion n'a pas pu être enregistrée.",
    connection_failed: "Une erreur est survenue pendant la connexion Gmail."
  };

  const params = new URLSearchParams(window.location.search);
  const outcome = params.get("gmail_oauth");
  if (outcome) {
    status.textContent = messages[outcome] || "Résultat de la connexion Gmail : " + outcome;
    status.className = outcome === "connected" ? "success" : "error";
    params.delete("gmail_oauth");
    const query = params.toString();
    window.history.replaceState({}, document.title, window.location.pathname + (query ? "?" + query : "") + window.location.hash);
  }

  button.addEventListener("click", async function () {
    button.disabled = true;
    button.textContent = "Ouverture de Google…";
    status.textContent = "Vérification de votre session Komparse…";
    status.className = "info";
    try {
      const { data, error } = await supabaseClient.auth.getSession();
      if (error || !data.session) throw new Error("Connectez-vous d'abord à votre compte Komparse.");
      const response = await fetch("https://glufyxsdmaccuuqpoxbo.supabase.co/functions/v1/gmail-oauth", {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + data.session.access_token,
          "apikey": SUPABASE_PUBLISHABLE_KEY,
          "Content-Type": "application/json"
        },
        body: "{}"
      });
      const result = await response.json();
      if (!response.ok || !result.authorization_url) throw new Error(result.error || "Impossible de démarrer la connexion Gmail.");
      const destination = new URL(result.authorization_url);
      if (destination.protocol !== "https:" || destination.hostname !== "accounts.google.com") throw new Error("Adresse d'autorisation Google inattendue.");
      window.location.assign(destination.toString());
    } catch (error) {
      status.textContent = error.message || "La connexion Gmail n'a pas pu démarrer.";
      status.className = "error";
      button.disabled = false;
      button.textContent = "Réessayer de connecter Gmail";
    }
  });
})();
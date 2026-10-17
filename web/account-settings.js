(function () {
  "use strict";

  const button = document.getElementById("settings-change-password");
  const password = document.getElementById("settings-new-password");
  const confirmation = document.getElementById("settings-confirm-password");
  const status = document.getElementById("settings-password-status");

  if (!button || !password || !confirmation || !status) return;

  function show(message, kind) {
    status.textContent = message;
    status.dataset.state = kind || "info";
    status.style.color = kind === "error" ? "#ffb4b4" : kind === "success" ? "#9de4b8" : "";
  }

  button.addEventListener("click", async function () {
    const nextPassword = password.value;
    const confirmPassword = confirmation.value;

    if (nextPassword.length < 10) {
      show("Le mot de passe doit contenir au moins 10 caractères.", "error");
      password.focus();
      return;
    }

    if (nextPassword !== confirmPassword) {
      show("Les deux mots de passe ne correspondent pas.", "error");
      confirmation.focus();
      return;
    }

    if (typeof supabaseClient === "undefined" || !supabaseClient.auth) {
      show("Le service de compte n’est pas disponible. Rechargez la page.", "error");
      return;
    }

    button.disabled = true;
    show("Mise à jour du mot de passe…", "info");

    try {
      const sessionResult = await supabaseClient.auth.getSession();
      if (sessionResult.error) throw sessionResult.error;
      if (!sessionResult.data.session) {
        throw new Error("Vous devez être connecté pour modifier votre mot de passe.");
      }

      const result = await supabaseClient.auth.updateUser({ password: nextPassword });
      if (result.error) throw result.error;

      password.value = "";
      confirmation.value = "";
      show("Mot de passe mis à jour.", "success");
    } catch (error) {
      show(error && error.message ? error.message : "Impossible de modifier le mot de passe. Réessayez.", "error");
    } finally {
      button.disabled = false;
    }
  });
})();

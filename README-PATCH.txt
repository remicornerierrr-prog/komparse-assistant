Komparse Assistant — correctif récupération du mot de passe

Remplacer dans le projet :
- web/app.js
- web/index.html

Cause traitée : le précédent code affichait le formulaire dès que l'URL contenait ?mode=recovery, même si Supabase n'avait pas établi de session de récupération. Il transformait aussi toutes les erreurs de updateUser en message « lien expiré », ce qui masquait leur vraie cause, et affichait ces messages en vert.

Le nouveau code :
- exige le callback/token de récupération et une session Supabase avant d'autoriser la mise à jour ;
- attend brièvement l'échange PKCE s'il n'est pas encore terminé ;
- distingue les liens invalides/expirés des mots de passe refusés et des autres erreurs ;
- affiche les erreurs en rouge, les informations en bleu et les réussites en vert.

IMPORTANT POUR LE TEST :
1. Installer le patch, puis commit/push sur main.
2. Attendre le déploiement GitHub Pages.
3. Demander un NOUVEAU lien « Mot de passe oublié ? » et ouvrir le dernier e-mail dans le même navigateur où la demande a été faite. En flux PKCE, ouvrir le lien dans un autre navigateur/appareil peut ne pas avoir le vérificateur de session nécessaire.
4. Si l'erreur persiste, la console du navigateur affichera désormais la véritable erreur Supabase au lieu d'affirmer systématiquement que le lien a expiré.

Vérification :
node --check web\app.js

Commit / push :
git add web/app.js web/index.html
git commit -m "Fix password recovery session and error handling"
git push origin main

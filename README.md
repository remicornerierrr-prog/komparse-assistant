# Komparse Assistant

Prototype d'un assistant destiné aux figurants en Allemagne.

## Objectif du MVP V1

Surveiller automatiquement les nouvelles annonces publiées sur Komparse.de, les analyser et identifier celles qui correspondent au profil d'un figurant. Les offres compatibles sont enregistrées dans Supabase et peuvent déclencher une notification Web Push.

## Zone géographique V1

- Köln
- Großraum Köln
- Großraum Bonn
- Großraum Düsseldorf
- Großraum Köln/Bonn/Düsseldorf
- Nordrhein-Westfalen (NRW)
- Annonces nationales en Allemagne : Bundesweit, Deutschlandweit, Ganz Deutschland, Deutschland, Germany

Les localisations qui ne correspondent pas clairement à ces règles restent en revue manuelle ou hors périmètre. Les rayons explicites jusqu'à 100 km peuvent être acceptés lorsqu'ils partent d'une ville prise en charge. Les rayons supérieurs à 100 km restent en revue manuelle.

## Critères de matching

- Localisation
- Âge
- Sexe

Une annonce sans date exacte peut tout de même être considérée si les critères de matching sont utilisables ; la période et les modalités de tournage sont conservées séparément et aucune date n'est inventée.

## Pipeline automatisé

Komparse.de → scraping → parsing et contrôles de qualité → mise à jour Supabase → matching avec les profils → enregistrement des matches → notifications Web Push.

Le workflow GitHub Actions `Komparse scraper` est planifié toutes les 15 minutes et peut aussi être lancé manuellement. Le workflow `Deploy site to GitHub Pages` publie le contenu du dossier `web/` à chaque push sur `main`.

Lorsqu'un profil est créé, les annonces qui le matchent et dont la date de publication se situe dans les sept jours précédant la création du profil sont ajoutées à Mes offres au prochain passage du scraper. Ces matches de bienvenue ne déclenchent pas de notification push rétroactive.

Lorsqu'un profil est modifié, le scraper recalcule les correspondances des annonces publiées au cours des sept derniers jours selon les critères actualisés. Les annonces qui ne correspondent plus sont masquées, sauf si une candidature leur a déjà été envoyée. Les matches recalculés ne génèrent pas de notification push rétroactive.

## Traduction des titres d'offres

Les titres restent en allemand lorsque l'interface est en allemand. En français ou en anglais, la fonction Supabase `translate-offer-titles` traduit les titres affichés et conserve le titre allemand original en dessous. La fonction vérifie que chaque offre appartient aux correspondances de l'utilisateur connecté, utilise MyMemory comme service gratuit principal et tente l'instance communautaire LibreTranslate en secours. Les résultats sont mémorisés dans Supabase par offre et par langue, afin que les utilisateurs partagent le même cache et qu'une traduction déjà enregistrée ne consomme pas à nouveau le quota externe.

Pour activer cette fonctionnalité, déployer la fonction depuis un environnement connecté au projet :

```powershell
supabase functions deploy translate-offer-titles
```

Ces services externes reçoivent les titres allemands envoyés pour traduction et peuvent appliquer des limites de disponibilité ou de quota. Si les deux services échouent, les offres restent accessibles et le titre original est affiché avec un message signalant que la traduction est indisponible.

## Notifications push

- Les abonnements Web Push sont enregistrés par utilisateur et par appareil.
- Les notifications sont envoyées via Web Push/VAPID depuis le workflow du scraper.
- Les tentatives et résultats de livraison sont suivis par appareil afin de retenter les échecs sans renvoyer inutilement les notifications déjà délivrées.
- Une réponse positive de la passerelle signifie qu'elle a accepté la notification, pas nécessairement que le système d'exploitation l'a affichée à l'écran.
- Les secrets `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` et `VAPID_SUBJECT` doivent être configurés dans les secrets GitHub Actions.

## Photos de profil

Jusqu'à 10 photos peuvent être stockées dans le profil. Elles sont redimensionnées à 1 600 pixels maximum sur leur plus grand côté, puis converties en JPEG dans le navigateur avant l'envoi. Seule la version optimisée est stockée dans le bucket privé Supabase, avec une limite de 5 Mo par photo. Les fichiers d'origine ne sont pas envoyés à un service externe.

Lors de la préparation d'une candidature Gmail, l'adresse du destinataire peut être modifiée et validée avant l'envoi. Chaque photo du profil peut aussi être cochée/décochée et son nom de pièce jointe modifié. Seules les photos cochées sont jointes, dans la limite totale de 15 Mo.

Pour déployer la limite de 10 photos et la prise en charge des pièces jointes personnalisées, appliquer la migration Supabase puis déployer la fonction :

```powershell
supabase db push
supabase functions deploy gmail-send-application
```

## Règles de qualité du parsing

- Le titre de page « Aktuelle Gesuche » est retiré avant l'analyse de la localisation.
- Les localisations sont normalisées par `scraper/location_rules.py`, partagé entre le parseur et le matching.
- Les mentions explicites telles que `Damen und Herren`, `m/w` et les formes inclusives (`Darsteller*innen`, `Kompars*innen`) peuvent être interprétées comme mixtes selon le contexte. Les mots génériques `Komparsen`, `Darsteller` et `Kleindarsteller` ne sont pas interprétés automatiquement comme masculins : si le sexe n'est pas précisé, l'annonce peut rester en revue.
- Les âges ouverts sont conservés sans inventer de borne : `ab 30 Jahren` devient `age_min=30`, `age_max=NULL`. `gemischtes Alter` reste une description, pas une tranche numérique.
- Une date exacte est stockée dans `shoot_date`. Les périodes (`Ende November 2026`) et modalités (`Nach Absprache`) sont conservées dans `shoot_date_text`; la durée et la logistique restent dans `shoot_duration_text`.
- Les champs de qualité de parsing sont définis dans `supabase/migrations/20261009_parser_quality_fields.sql`; les champs d'abonnements push multi-appareils sont définis dans `supabase/migrations/20261009_multi_browser_push.sql`.

## Données de référence et fixtures

Les captures HTML et les instantanés JSON utilisés pour les tests sont rangés dans `scraper/fixtures/`. Les tests et scripts de régression lisent ces fichiers statiques et ne contactent pas le site en direct. Les fichiers `komparse_offers.json` et `komparse_parsed_offers.json` générés pendant une exécution normale restent à la racine du projet et sont ignorés par Git.

Les anciennes notes d'installation et de patch sont archivées dans `docs/patch-archive/`.

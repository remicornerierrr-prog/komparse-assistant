# Komparse Assistant

Prototype d'un assistant destiné aux figurants en Allemagne.

## Objectif du MVP V1

Surveiller automatiquement les nouvelles annonces publiées sur Komparse.de
et identifier celles qui correspondent au profil d'un figurant.

## Zone géographique

- Köln
- Großraum Köln
- Großraum Bonn
- Großraum Düsseldorf
- Großraum Köln/Bonn/Düsseldorf

## Critères de matching

- Localisation
- Âge
- Sexe

## Fonctionnement prévu

Komparse.de
→ Scraper
→ Analyse des annonces
→ Matching avec les profils
→ Notification push
→ Préparation de la candidature
→ Email avec photos

## Règles de qualité du parsing

- Le titre de page « Aktuelle Gesuche » est retiré avant l'analyse de la localisation.
- Les localisations sont normalisées par `scraper/location_rules.py`, partagé entre le parseur et le matching. Les localisations nationales ou trop larges (par ex. `Bundesweit`, `NRW`) restent en revue manuelle.
- Les mentions explicites telles que `Damen und Herren`, `m/w` et les formes inclusives (`Darsteller*innen`, `Kompars*innen`) sont mixtes. Les mots génériques `Komparsen`, `Darsteller` et `Kleindarsteller` ne sont pas interprétés automatiquement comme masculins : le sexe est alors à vérifier et aucun match/Push automatique n'est déclenché.
- Les âges ouverts sont conservés sans inventer une borne : `ab 30 Jahren` devient `age_min=30`, `age_max=NULL`. `gemischtes Alter` reste une description d'âge, pas une tranche numérique.
- Une date exacte est stockée dans `shoot_date`. Les périodes (`Ende November 2026`) et modalités (`Nach Absprache`) sont conservées dans `shoot_date_text`; la durée/logistique reste dans `shoot_duration_text`. Aucune journée exacte n'est inventée pour une période.
- Avant de déployer, exécuter une fois le SQL `supabase/migrations/20261009_parser_quality_fields.sql` dans Supabase si ces colonnes n'existent pas encore.
- Chaque exécution du workflow imprime un bilan des Push : tentatives, acceptations par la passerelle, échecs, abonnements absents/invalides et matches déjà marqués notifiés. Une réponse positive de la passerelle ne garantit pas que le système d'exploitation affiche visuellement la notification.

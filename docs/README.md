# Documentation du dépôt

## Archives de patchs

`patch-archive/` conserve les instructions et notes associées aux correctifs ponctuels déjà intégrés. Ces fichiers sont historiques : ils ne sont pas nécessaires à l'exécution de l'application.

## Fixtures du scraper

Les captures de référence utilisées pour les tests se trouvent dans `../scraper/fixtures/`. Les fichiers générés pendant les exécutions du scraper restent à la racine locale et sont ignorés par Git.

## Tests GitHub Actions

Le workflow `Komparse scraper` lance la suite de tests en mode non bloquant, conformément au choix du projet : un échec est signalé comme avertissement, puis le scraper continue. Cela permet de surveiller les régressions sans interrompre les cycles de collecte.

# Flight Deal Alert Bot

Ce projet lit une feuille Google Sheet de destinations/prix via Sheety, compare les prix à ceux d’Amadeus, puis envoie un SMS via Twilio et un e-mail aux utilisateurs inscrits lorsque la meilleure offre est inférieure au prix cible.

## Structure principale

- `config.py` : charge les variables d’environnement avec `python-dotenv`, fournit les paramètres de base (Sheety, Amadeus, Twilio) et valide que les clés essentielles sont présentes.  
- `data_manager.py` : encapsule les appels Sheety (`GET`, `POST`, `PUT`) pour lire ou mettre à jour les lignes de la feuille.  
- `flight_data.py` : transforme une réponse Amadeus en objet immuable avec le prix, les aéroports, les dates et les escales.  
- `flight_search.py` : gère l’authentification OAuth, résout les codes IATA manquants via Amadeus et récupère le vol le moins cher.  
- `notification_manager.py` : compose un SMS avec les détails du deal, l’envoie via l’API REST Twilio et expédie en parallèle un e-mail à tous les utilisateurs listés dans l’onglet `users` de Sheety.
- `main.py` : script CLI qui assemble tout : lecture Sheety, synchronisation des codes IATA, requêtes Amadeus, comparaison des prix et envoi des notifications (SMS + e-mail).
- `.env.example` : modèle des variables sensibles à remplir localement (Sheety, Amadeus, Twilio, dates par défaut).  
- `.gitignore` : exclut les fichiers sensibles (`.env`, `.venv`, caches) pour protéger les clés.
- `.github/workflows/flight-deals.yml` : workflow GitHub Actions qui exécute quotidiennement `python main.py --search --notify`.

## Prérequis

1. Python 3.11 (ou similaire) avec `pip`.  
2. Installer les dépendances : `pip install -r requirements.txt` (ou `requests python-dotenv` si aucun fichier requirements).  
3. Copier `.env.example` en `.env` et renseigner :
   - `SHEETY_PRICES_ENDPOINT` (ou `SHEETY_ENDPOINT` pour compatibilité), `SHEETY_TOKEN`, `SHEETY_DATA_KEY` pour l’onglet `prices`.
   - `SHEETY_USERS_ENDPOINT` + `SHEETY_USERS_KEY` si nécessaire pour le second onglet `users`, ainsi que `SHEETY_USERNAME`/`SHEETY_PASSWORD` si ton projet Sheety utilise l’auth Basic.
   - `AMADEUS_API_KEY`, `AMADEUS_API_SECRET`.
   - `TWILIO_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`, `TWILIO_TO`.
   - `EMAIL_SENDER`, `EMAIL_PASSWORD` et éventuellement `SMTP_HOST`, `SMTP_PORT` pour expédier les notifications par e-mail.
   - Optionnel : `DEFAULT_DEPARTURE_DATE`, `DEFAULT_RETURN_DATE` si tu veux les fixer (sinon on part de +6 mois).
   - Le script utilise `python-dotenv` pour charger ces valeurs.

## Exécution manuelle

Tu peux tester en local avec :

```
python main.py --fetch                  # visualise les données Sheety
python main.py --sync-iata             # complète les codes IATA manquants via Amadeus
python main.py --search --notify        # compare les prix puis SMS + email si un deal est meilleur
```

Ajoute `--origin`, `--departure`, `--return` si tu veux composer des dates/IAta personnalisées.  
La combinaison `--search --notify` est celle utilisée dans le workflow GitHub Actions pour faire tourner la veille quotidienne.

## Workflow GitHub Actions

1. Crée un dépôt GitHub et pousse ton projet (avec `.gitignore`).  
2. Ajoute `.github/workflows/flight-deals.yml` (déjà présent ici) qui :
   - s’exécute tous les jours à 06:00 UTC (`cron`) et peut être déclenché manuellement (`workflow_dispatch`).  
   - installe Python 3.11, les dépendances, puis lance `python main.py --search --notify`.  
3. Dans « Settings > Secrets and variables > Actions » du repo, définis les secrets :  
   `SHEETY_ENDPOINT`, `SHEETY_TOKEN`, `SHEETY_DATA_KEY`, `AMADEUS_API_KEY`, `AMADEUS_API_SECRET`, `TWILIO_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`, `TWILIO_TO`.  
   Ces valeurs sont injectées dans le workflow via `env` ; le code lit ces variables comme si elles étaient dans un `.env`.
4. Une fois les Secrets en place, tu peux déclencher la première exécution depuis l’onglet « Actions » ou attendre la planification.

## Surveillance & logs

Chaque run GitHub Actions affiche :

- les étapes (checkout, setup, install, run).  
- la sortie de `main.py`, qui indique si un vol a été trouvé et si des SMS/e-mails ont été émis.
- les erreurs éventuelles (authentification Amadeus ou Twilio). Tu peux relancer le workflow manuellement après avoir corrigé.

## Étapes suivantes

1. Ajouter un module de tests ou un script de validation (optionnel).  
2. Ajouter un scheduler (facultatif) pour déclencher en local si tu veux tester à n’importe quel moment.  
3. Étendre `NotificationManager` pour envoyer des alertes sur d’autres canaux (mail, Slack, etc.).

Tu veux que je t’aide à vérifier que le workflow GitHub est bien actif une fois les secrets configurés ? !***  

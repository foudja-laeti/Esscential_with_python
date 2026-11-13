# Service Produits (port 8002)

Application autonome du mini-projet API Gateway (EADL FE). Elle expose le service Produits, avec un stockage en mémoire : les données sont réinitialisées à chaque démarrage.

## Prérequis

- Python 3.11 ou supérieur
- Un serveur MySQL 8 (WAMP, XAMPP, Docker...) démarré
- Accès à PyPI pour la première installation des dépendances

## Base de données

1. Créer la base et l'utilisateur (client MySQL ou phpMyAdmin, onglet SQL) :
```sql
CREATE DATABASE products_db CHARACTER SET utf8mb4;
CREATE USER 'products_user'@'localhost' IDENTIFIED BY 'choisissez-un-mot-de-passe';
GRANT ALL PRIVILEGES ON products_db.* TO 'products_user'@'localhost';
```
2. Créer la table et les 3 produits de départ : exécuter le contenu de `db/schema.sql` sur `products_db`.
3. Copier `.env.example` en `.env` et y mettre le mot de passe choisi. Le fichier `.env` n'est jamais versionné.

Les données sont **persistantes** : un redémarrage du service ne les réinitialise pas. Pour revenir aux 3 produits de départ (avant une démonstration ou une comparaison), exécuter `db/reset.sql`.

Si MySQL est arrêté ou injoignable, les routes métier répondent **503** `DATABASE_UNAVAILABLE` avec `Retry-After: 5` (connexion limitée à 3 secondes) ; `/health` reste disponible. Le service se rétablit seul au retour de MySQL.

## Installation

```sh
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell : .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
Dans chaque nouveau terminal, réactivez le venv avant de lancer le service.

## Lancement et arrêt

```sh
python run.py
```

Le service écoute sur `http://127.0.0.1:8002`. Arrêt : `Ctrl+C`.

Lancement alternatif :

```sh
python -m uvicorn products_service.app:app --host 127.0.0.1 --port 8002
```

## Routes

| Méthode | Chemin | Résultat |
|---|---|---|
| GET | `/api/products` | 200, liste `{data, meta}` ; paramètres `page`, `limit` (max 100), `q` |
| POST | `/api/products` | 201 + en-tête `Location` |
| GET | `/api/products/{id}` | 200, ou 404 si absent |
| PATCH | `/api/products/{id}` | 200, modification partielle |
| DELETE | `/api/products/{id}` | 204 sans corps |
| GET | `/health` | 200, toujours disponible |

Champs d'un produit : `name` (texte), `priceCents` (entier >= 0, en centimes), `stock` (entier >= 0).
Les erreurs ont toujours la forme `{"error": {"code": "...", "message": "..."}}`, avec un statut 400 (jamais 422) pour les données invalides.
Documentation interactive : `http://127.0.0.1:8002/docs`.

## Exemple d'appel

```sh
curl -i http://127.0.0.1:8002/api/products
curl -i -X POST http://127.0.0.1:8002/api/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Dior Sauvage 100 ml","priceCents":9900,"stock":3}'
```

Sous Windows PowerShell, utilisez `curl.exe`.

## Options de simulation

| Option | Variable d'environnement | Effet |
|---|---|---|
| `--port N` | `PRODUCTS_PORT` | Port d'écoute (défaut 8002) |
| `--host H` | `HOST` | Adresse d'écoute (défaut 127.0.0.1) |
| `--delay-ms N` | `PRODUCTS_DELAY_MS` | Retard de 0 à 30000 ms sur les routes métier |
| `--mode unavailable` | `PRODUCTS_MODE` | Réponse 503 avec `Retry-After: 5` sur les routes métier ; `/health` reste disponible |
| (aucune option) | `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` | Connexion MySQL (voir `.env.example`) |

Les options de ligne de commande ont priorité sur les variables d'environnement.

```sh
python run.py --mode unavailable
python run.py --delay-ms 3000
```

## Données de départ

Les données sont stockées dans MySQL. db/reset.sql rétablit ces 3 produits.

## Code commun

Le code utilitaire (gestion des erreurs, validation, hébergement Uvicorn) est dupliqué depuis le paquet fourni, car les trois services sont écrits dans des langages différents et ne peuvent pas partager de bibliothèque. Coût de maintenance : une correction commune doit être reportée à la main dans chaque service.
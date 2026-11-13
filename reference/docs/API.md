# Contrat des trois API REST

## Conventions communes

Les URL ci-dessous utilisent la configuration par défaut. Les corps de requête et de réponse sont en JSON UTF-8. Aucun secret ni en-tête d'authentification n'est requis pour un appel **direct** aux services.

- Ressource : réponse {"data": {...}}.
- Collection : réponse {"data": [...], "meta": {"page": 1, "limit": 20, "total": 3}}. total correspond au nombre de résultats filtrés avant pagination.
- Erreur : réponse {"error": {"code": "RESOURCE_NOT_FOUND", "message": "Ressource introuvable."}}.
- Une création produit 201 et un en-tête Location relatif, par exemple /api/users/4.
- Une modification partielle PATCH produit 200 avec la ressource complète.
- Une suppression produit 204 **sans corps**. Une deuxième suppression du même identifiant produit 404.
- Les identifiants sont des entiers positifs générés par le service. Vous ne fournissez jamais id dans un corps POST ou PATCH.
- Les chaînes name et email perdent leurs espaces de bord. Les emails passent en minuscules.
- Les champs inconnus, les corps vides, les tableaux à la place d'un objet et les champs manquants produisent 400.
- Les corps POST et PATCH doivent avoir Content-Type: application/json, un Content-Length unique et une taille maximale de 65536 octets. Les transferts chunked ne sont pas pris en charge.
- Les slashs finaux ne sont pas acceptés. Les chemins sont sensibles à la casse.
- Chaque réponse contient X-Service-Name, Cache-Control: no-store et Connection: close. Le serveur utilise HTTP/1.1 et ferme la connexion après chaque réponse.
- Un client qui expire peut recevoir une erreur de délai locale avant que le service réponde. Un POST peut néanmoins avoir été appliqué après cette expiration : ne le rejouez pas automatiquement.

### Pagination et filtres

Toutes les collections acceptent page (défaut 1, maximum 1000000) et limit (défaut 20, maximum 100). Ce sont des entiers décimaux strictement positifs. L'ordre est celui des identifiants croissants. Une page au-delà du résultat renvoie data: [] avec un total inchangé.

Les paramètres de liste inconnus ou répétés produisent 400. Ainsi ?page=1&page=2 est invalide. Au plus 20 paramètres sont analysés. Les filtres de liste sont combinés par ET. Les routes de détail, mutations et /health ignorent les paramètres de query string.

### HEAD, OPTIONS et méthodes non prévues

HEAD est disponible partout où GET l'est, avec le même statut et les mêmes en-têtes, mais sans corps. Pour les routes métier, OPTIONS renvoie 204 avec Allow. OPTIONS n'est pas une configuration CORS : aucun en-tête Access-Control-Allow-* n'est émis.

Sur une route connue, PUT ou une méthode implémentée mais non admise renvoie 405 avec Allow. Une méthode HTTP que le serveur ne prend pas en charge, par exemple TRACE, renvoie 501. Un chemin inconnu renvoie 404.

## Service Utilisateurs

Base : http://127.0.0.1:8001

| Méthode | Route | Corps ou paramètres | Résultat nominal |
|---|---|---|---|
| GET | /api/users | page, limit, q facultatifs | 200, collection |
| GET | /api/users/{id} | Aucun | 200, ressource |
| POST | /api/users | name, email, role facultatif | 201, ressource et Location |
| PATCH | /api/users/{id} | Au moins un champ parmi name, email, role | 200, ressource |
| DELETE | /api/users/{id} | Aucun | 204 |

Le filtre q recherche une sous-chaîne dans name ou email, sans distinction de casse. Il accepte au maximum 120 caractères. Un q vide ne filtre pas.

| Champ | Type et contraintes |
|---|---|
| id | Entier généré, en lecture seule |
| name | Chaîne de 1 à 120 caractères après nettoyage |
| email | Chaîne de 1 à 254 caractères, format simple local@domaine.extension, unique sans distinction de casse |
| role | customer ou staff, défaut customer à la création |

Exemple de création :

~~~json
{"name":"Zoé Petit","email":"zoe@example.test","role":"customer"}
~~~

Réponse après un démarrage neuf :

~~~json
{"data":{"id":4,"name":"Zoé Petit","email":"zoe@example.test","role":"customer"}}
~~~

Exemple de modification :

~~~json
{"name":"Zoé Dupont"}
~~~

Une création ou modification avec un email déjà utilisé renvoie 409 EMAIL_EXISTS. Une modification conserve les champs omis. Les utilisateurs ne possèdent ni mot de passe ni session dans ce scénario.

## Service Produits

Base : http://127.0.0.1:8002

| Méthode | Route | Corps ou paramètres | Résultat nominal |
|---|---|---|---|
| GET | /api/products | page, limit, q facultatifs | 200, collection |
| GET | /api/products/{id} | Aucun | 200, ressource |
| POST | /api/products | name, priceCents, stock | 201, ressource et Location |
| PATCH | /api/products/{id} | Au moins un champ parmi name, priceCents, stock | 200, ressource |
| DELETE | /api/products/{id} | Aucun | 204 |

q recherche dans name, sans distinction de casse, avec au maximum 120 caractères. La recherche conserve les accents : Écran et écran correspondent, mais ecran ne correspond pas automatiquement.

| Champ | Type et contraintes |
|---|---|
| id | Entier généré, en lecture seule |
| name | Chaîne de 1 à 120 caractères après nettoyage |
| priceCents | Entier de 0 à 1000000000, prix en centimes d'euro |
| stock | Entier de 0 à 1000000000, quantité de démonstration |

Les booléens et nombres fractionnaires ne sont pas des entiers acceptés. Exemple : 4990 représente 49,90 euros.

Exemple de création :

~~~json
{"name":"Support ordinateur","priceCents":3490,"stock":8}
~~~

Réponse après un démarrage neuf :

~~~json
{"data":{"id":4,"name":"Support ordinateur","priceCents":3490,"stock":8}}
~~~

Exemple de modification :

~~~json
{"stock":7}
~~~

La création d'une commande ne modifie pas ce stock. Un produit avec stock: 0 reste consultable.

## Service Commandes

Base : http://127.0.0.1:8003

| Méthode | Route | Corps ou paramètres | Résultat nominal |
|---|---|---|---|
| GET | /api/orders | page, limit, userId, status facultatifs | 200, collection |
| GET | /api/orders/{id} | Aucun | 200, ressource |
| POST | /api/orders | userId, items | 201, ressource pending et Location |
| PATCH | /api/orders/{id} | status uniquement | 200, ressource |
| DELETE | /api/orders/{id} | Aucun | 204, quel que soit le statut |

| Champ | Type et contraintes |
|---|---|
| id | Entier généré, en lecture seule |
| userId | Entier de 1 à 1000000000 |
| items | Tableau de 1 à 100 lignes |
| items[].productId | Entier de 1 à 1000000000, unique dans la commande |
| items[].quantity | Entier de 1 à 1000 |
| status | pending à la création, puis confirmed ou cancelled |

Les filtres userId et status sont des égalités exactes et peuvent être combinés. Exemple : /api/orders?userId=1&status=pending.

Exemple de création :

~~~json
{"userId":1,"items":[{"productId":1,"quantity":2},{"productId":2,"quantity":1}]}
~~~

Réponse après un démarrage neuf :

~~~json
{"data":{"id":3,"userId":1,"items":[{"productId":1,"quantity":2},{"productId":2,"quantity":1}],"status":"pending"}}
~~~

Exemple de confirmation :

~~~json
{"status":"confirmed"}
~~~

**Transitions** : pending peut devenir confirmed ou cancelled. confirmed et cancelled sont finaux. Répéter le statut courant est autorisé et renvoie 200. Une autre transition depuis un statut final produit 409 INVALID_TRANSITION. Vous ne modifiez ni userId ni items après création. POST interdit le champ status.

**Indépendance métier** : les références utilisateur et produit n'entraînent aucun appel réseau ni contrôle d'existence. Aucun total, paiement, réservation de stock ou suppression en cascade n'est implémenté. Il s'agit d'un scénario simplifié destiné aux exercices de passerelle.

## Santé des services et simulations

GET /health et HEAD /health existent sur chacun des trois ports. Exemple :

~~~json
{"service":"products","status":"ok","mode":"normal","delayMs":0}
~~~

/health vérifie que le processus répond. Cette route reste à 200, même avec mode: unavailable, et ne subit jamais le retard simulé. Ce n'est donc pas une garantie de disponibilité métier. La Gateway n'a pas besoin d'exposer cette route aux clients.

Pour les routes métier connues et les méthodes admises : le retard configuré s'applique avant le traitement, puis le mode unavailable produit 503. OPTIONS échappe aux simulations. Une route inconnue ou une méthode non admise conserve sa propre erreur sans attendre le retard.

## Codes d'erreur

| HTTP | code | Situation |
|---|---|---|
| 400 | VALIDATION_ERROR | Corps ou paramètres métier invalides |
| 400 | INVALID_JSON | JSON invalide, UTF-8 invalide ou corps incomplet |
| 400 | INVALID_TARGET | Cible de requête sous forme d'URL absolue |
| 400 | TRANSFER_ENCODING_UNSUPPORTED | Corps avec Transfer-Encoding |
| 404 | ROUTE_NOT_FOUND | Chemin non reconnu |
| 404 | RESOURCE_NOT_FOUND | Identifiant absent |
| 405 | METHOD_NOT_ALLOWED | Méthode non admise sur une route connue, avec Allow |
| 408 | REQUEST_TIMEOUT | Lecture du corps dépassant le budget de 10 secondes |
| 409 | EMAIL_EXISTS | Email déjà utilisé |
| 409 | INVALID_TRANSITION | Changement interdit d'un statut final |
| 411 | LENGTH_REQUIRED | Content-Length absent, répété ou invalide |
| 413 | BODY_TOO_LARGE | Corps supérieur à 65536 octets |
| 415 | UNSUPPORTED_MEDIA_TYPE | Corps qui n'annonce pas application/json |
| 500 | INTERNAL_ERROR | Erreur inattendue, sans détail interne dans la réponse |
| 503 | SERVICE_UNAVAILABLE | Mode de simulation unavailable, avec Retry-After: 5 |
| 405 | METHOD_NOT_ALLOWED | Méthode non autorisée sur une route FastAPI |

Exemple d'erreur métier :

~~~json
{"error":{"code":"EMAIL_EXISTS","message":"Cette adresse email est déjà utilisée."}}
~~~

Votre Gateway doit préserver les statuts et corps reçus. Elle produit elle-même ses refus 401 et 429, son erreur de communication 502 et son expiration 504. Un 503 reçu d'un service ne doit pas être converti automatiquement en 502.

## Documentation FastAPI

Chaque application expose /docs et /openapi.json directement sur son port. Ces routes techniques s’ajoutent aux contrats métier ci-dessus. Les erreurs de validation Pydantic sont traduites en 400 avec la même enveloppe JSON. Une requête HTTP mal formée rejetée par Uvicorn avant FastAPI peut recevoir une réponse protocolaire propre au serveur, hors de cette enveloppe.

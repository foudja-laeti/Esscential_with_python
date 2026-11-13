# Scénarios de vérification de votre Gateway

Ce guide utilise uniquement les trois services fournis. Vous adaptez l'adresse et le port de votre Gateway à votre réalisation. Pour les pannes isolées, lancez les services dans trois terminaux séparés avec --service.

## 1. Routage nominal

Appelez /api/users/1, /api/products/2 et /api/orders/1 directement, puis via votre Gateway. Comparez les statuts, les données et l'en-tête X-Service-Name. Ajoutez une clé valide pour les appels à votre Gateway, selon votre convention.

Vérifiez une query string : /api/products?q=Souris&page=1&limit=1. Vous devez obtenir le produit 2 et meta.total égal à 1. Pour vérifier les paramètres répétés, /api/products?page=1&page=2 doit conserver son erreur 400 si la Gateway relaie correctement la query string.

## 2. Méthodes, corps et réponses

Créez un utilisateur à partir de examples/user.json. Vérifiez 201, le corps data et Location. Utilisez l'identifiant retourné pour un GET, puis un PATCH avec examples/user-patch.json et un DELETE. La suppression doit répondre 204 avec un corps vide.

Refaites une création avec le même email avant suppression : vous devez recevoir 409. Un GET sur un identifiant absent retourne 404 RESOURCE_NOT_FOUND. Un chemin inconnu retourne 404 ROUTE_NOT_FOUND. La Gateway conserve ces erreurs métier et leur contenu.

## 3. Authentification et quota

Les services amont acceptent les appels directs sans clé. Via votre Gateway, essayez une clé valide, une clé invalide et l'absence de clé. Les deux derniers cas doivent être refusés avec 401, sans transmettre l'appel.

Avec une clé valide, appliquez votre convention de quota, par exemple 30 appels dans la même fenêtre puis un appel supplémentaire. Vérifiez 429 au dépassement et un quota indépendant pour un autre client. Utilisez vos propres tests ou compteurs d'appels pour prouver l'absence de transmission : les services fournis n'exposent pas de compteur d'administration.

## 4. Processus arrêté

Arrêtez uniquement Produits avec Ctrl+C dans son terminal. /api/users et /api/orders doivent encore répondre via votre Gateway. L'appel Produits doit produire l'erreur de communication prévue, généralement 502. Relancez Produits et vérifiez la reprise.

Le mode groupé s'arrête entièrement lorsqu'un de ses processus s'arrête. Il ne convient donc pas à cette démonstration de panne isolée.

## 5. Indisponibilité explicite

Arrêtez Produits, puis lancez :

~~~sh
python run.py --service products --mode unavailable
~~~

Un GET direct /api/products renvoie 503 avec Retry-After: 5 et le code SERVICE_UNAVAILABLE. Votre Gateway doit préserver ce statut. /health reste à 200 et annonce le mode unavailable. Pour revenir à la normale, relancez sans --mode.

## 6. Service lent

Arrêtez Commandes, puis lancez :

~~~sh
python run.py --service orders --delay-ms 5000
~~~

Configurez votre Gateway avec un délai plus court, par exemple 3 secondes. Appelez **GET** /api/orders à travers la Gateway : elle doit terminer avec 504 avant la réponse amont. Un appel direct finit par répondre 200 après environ 5 secondes. /health reste immédiat.

Utilisez GET pour cette démonstration. L'expiration côté client n'annule pas nécessairement un traitement métier : un POST retardé peut créer une ressource après le 504. Les relances automatiques d'écritures demanderaient une stratégie d'idempotence hors périmètre.

## 7. Journalisation et remise à zéro

Dans les journaux de votre Gateway, retrouvez un succès, un refus et une panne avec date, client, route, méthode, statut et durée. Vérifiez l'absence de clé, de corps sensible et de paramètres privés. Les services fournis n'impriment que leurs informations de démarrage.

Après les essais, arrêtez les simulations et relancez les services en mode normal. Le redémarrage restaure les données initiales. Gardez les essais destructifs et les tests automatisés de votre Gateway sur une instance dédiée lorsque d'autres équipes utilisent le même environnement.

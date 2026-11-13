# Services REST fournis pour le mini-projet API Gateway

Ce dossier contient les trois services métiers **Utilisateurs**, **Produits** et **Commandes** du mini-projet EADL FE. Vous les utilisez comme cibles de votre Gateway. Leur développement ne fait pas partie du travail demandé aux étudiants.

## Installation

### Prérequis et dossier de travail

Installer **Python 3.11 ou supérieur**, avec les modules standard venv et pip. Décompresser l’archive puis ouvrir un terminal dans le dossier **API_Gateway_Services**, celui qui contient ce README et requirements.txt. Python n’est pas inclus dans l’archive.

### Windows avec PowerShell

~~~powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -c "import sys; print(sys.executable); print(sys.version)"
~~~

Vérifier que la version affichée est au moins 3.11 et que le chemin de l’interpréteur pointe dans .venv. Si py n’est pas disponible mais que Python est dans le PATH, utiliser python à la place de py -3 pour les deux premières commandes.

Si PowerShell refuse Activate.ps1, l’activation est facultative : utiliser directement l’interpréteur du venv, sans changer la politique du poste :

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
~~~

Dans la suite, remplacer alors python par le chemin de cet interpréteur. Depuis un sous-dossier du projet, le chemin vers le venv racine commence par ..\.venv au lieu de .\.venv.

### Linux ou macOS avec bash/zsh

~~~sh
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -c "import sys; print(sys.executable); print(sys.version)"
~~~

Si la création échoue parce que venv ou ensurepip manque, installer le composant venv correspondant à votre Python avec le gestionnaire de votre système, puis reprendre la création. Par exemple, Debian/Ubuntu fournit généralement le paquet python3-venv. Sans activation, utiliser .venv/bin/python, ou ../.venv/bin/python depuis un sous-dossier.

### Dépendances et utilisation quotidienne

Le fichier requirements.txt fixe les versions testées de FastAPI, Uvicorn, Pydantic, HTTPX et pytest, ainsi que leurs dépendances transitives. **L’installation avec pip est obligatoire.** Une connexion à un index de paquets Python (ou un miroir/cache préparé par le formateur) est nécessaire à la première installation. HTTPX sert au relais de la Gateway et aux tests ; pytest lance toute la suite, y compris les anciens tests unittest.

Créer le venv et exécuter pip une seule fois par installation. Dans **chaque nouveau terminal**, revenir dans ce dossier et réactiver le venv avant les commandes de lancement, de vérification ou de test :

- PowerShell : .\.venv\Scripts\Activate.ps1
- bash/zsh : source .venv/bin/activate

Utiliser ensuite **python** pour conserver l’interpréteur du venv. Pour le quitter : deactivate. Arrêter d’abord les serveurs avec Ctrl+C. Ne pas copier ni distribuer .venv : le recréer après déplacement ou extraction du projet. Le dossier est exclu de Git et des archives fournies.

## Démarrage rapide

Depuis la racine du paquet, avec le venv actif :

~~~sh
python run.py
~~~

Garder le terminal ouvert. **Ctrl+C arrête les trois processus**. Dans un second terminal avec le même venv actif, les tests peuvent être lancés avec :

~~~sh
python -m pytest tests -v
~~~

Attendez une ligne d'écoute pour chacun des services :

| Service | Adresse par défaut | Contrôle de disponibilité |
|---|---|---|
| Utilisateurs | http://127.0.0.1:8001/api/users | http://127.0.0.1:8001/health |
| Produits | http://127.0.0.1:8002/api/products | http://127.0.0.1:8002/health |
| Commandes | http://127.0.0.1:8003/api/orders | http://127.0.0.1:8003/health |

Ouvrez ces URL dans votre navigateur ou utilisez, dans un second terminal :

~~~sh
curl http://127.0.0.1:8001/api/users
curl http://127.0.0.1:8002/api/products
curl http://127.0.0.1:8003/api/orders
~~~

Dans Windows PowerShell, utilisez **curl.exe** pour employer le véritable client curl, ou :

~~~powershell
Invoke-RestMethod http://127.0.0.1:8001/api/users | ConvertTo-Json -Depth 10
~~~

Chaque liste renvoie un objet avec data et meta. L'en-tête X-Service-Name vous permet d'identifier le service qui a réellement répondu.

## FastAPI et documentation interactive

Les commandes run.py sont conservées ; elles hébergent désormais de vraies applications FastAPI avec Uvicorn. Le stockage reste en mémoire et les contrats métier sont inchangés. La lecture explicite du corps conserve les limites de taille et les statuts du contrat. Les schémas Pydantic contrôlent les types sans coercition ; les erreurs métier et de validation restent au format error/code/message avec un statut 400, pas 422.

Après le démarrage, ouvrir directement :

| Service | Documentation interactive | Schéma OpenAPI |
|---|---|---|
| Utilisateurs | http://127.0.0.1:8001/docs | http://127.0.0.1:8001/openapi.json |
| Produits | http://127.0.0.1:8002/docs | http://127.0.0.1:8002/openapi.json |
| Commandes | http://127.0.0.1:8003/docs | http://127.0.0.1:8003/openapi.json |

Swagger UI permet d’essayer les routes avec leurs corps JSON. Ses ressources JavaScript/CSS sont chargées depuis un CDN par défaut : sans accès Internet, le schéma /openapi.json et les API restent disponibles, mais l’interface /docs peut ne pas s’afficher complètement.

Utiliser **un seul worker par application** : les données et quotas sont en mémoire. Le mode --reload est facultatif pour le développement et réinitialise ces états à chaque rechargement. Les simulations de panne et de délai restent accessibles via run.py.

## Branchement de votre Gateway

Les routes amont conservent les préfixes du sujet. Vous pouvez donc transmettre le chemin et la query string sans réécriture :

| Préfixe reçu par la Gateway | Base du service cible |
|---|---|
| /api/users | http://127.0.0.1:8001 |
| /api/products | http://127.0.0.1:8002 |
| /api/orders | http://127.0.0.1:8003 |

Exemple : /api/products/2 doit atteindre http://127.0.0.1:8002/api/products/2. Le chemin /api/users-old n'appartient pas au service Utilisateurs.

**Les services ne vérifient aucune clé API et n'appliquent aucun quota.** Ces contrôles appartiennent à votre Gateway. Un accès direct aux services fonctionne donc sans clé. Le paquet ne contient pas de solution de Gateway.

Les trois services fonctionnent dans des processus indépendants. Aucun ne contacte les deux autres. Ils partagent uniquement du code utilitaire sur disque, pas leur état en mémoire. Le lanceur groupé les arrête tous si l'un des processus s'arrête inopinément : utilisez le lancement séparé pour simuler la panne d'un seul service.

## Lancement séparé et configuration

Pour contrôler individuellement chaque service, utilisez trois terminaux :

~~~sh
python run.py --service users
python run.py --service products
python run.py --service orders
~~~

Ctrl+C dans le terminal Produits coupe alors uniquement ce service.

Options d'un lancement individuel :

~~~sh
python run.py --service products --host 127.0.0.1 --port 8102 --delay-ms 0 --mode normal
~~~

| Variable d'environnement | Valeur par défaut | Effet |
|---|---|---|
| HOST | 127.0.0.1 | Adresse d'écoute des services |
| USERS_PORT / PRODUCTS_PORT / ORDERS_PORT | 8001 / 8002 / 8003 | Ports distincts, entre 1 et 65535 |
| USERS_DELAY_MS / PRODUCTS_DELAY_MS / ORDERS_DELAY_MS | 0 | Retard de 0 à 30000 ms sur les routes métier |
| USERS_MODE / PRODUCTS_MODE / ORDERS_MODE | normal | normal ou unavailable |

Les options de ligne de commande ont priorité sur les variables d'environnement. --port, --delay-ms et --mode exigent --service. Les variables permettent également de configurer le lancement groupé. Aucun fichier .env n'est chargé automatiquement.

Exemple PowerShell pour le lancement groupé :

~~~powershell
$env:PRODUCTS_PORT = '8102'
python run.py
# Après l'arrêt, pour revenir à la configuration par défaut :
Remove-Item Env:PRODUCTS_PORT
~~~

Exemple macOS/Linux :

~~~sh
PRODUCTS_PORT=8102 python run.py
~~~

L'adresse 127.0.0.1 vise votre propre machine. Si votre Gateway tourne dans un conteneur, une VM ou sur un autre poste, adaptez l'adresse amont et éventuellement HOST à cet environnement. Ce serveur pédagogique HTTP local n'est pas destiné à un déploiement en production. Le paquet ne configure ni HTTPS ni CORS. Les essais en ligne de commande n'en ont pas besoin.

## Données et remise à zéro

Au démarrage, les services chargent :

- 3 utilisateurs, identifiants 1, 2 et 3, avec des adresses fictives example.test.
- 3 produits, identifiants 1, 2 et 3, prix en centimes d'euro et stock de démonstration.
- 2 commandes, identifiants 1 et 2, avec les statuts pending et confirmed.

Les créations, modifications et suppressions restent **en mémoire**. Arrêter puis relancer un service rétablit son jeu initial et réinitialise ses prochains identifiants. Il n'y a aucune route administrative de réinitialisation. Le redémarrage groupé réinitialise les trois services.

### Simplifications métier volontaires

Les commandes enregistrent userId et productId comme références opaques : elles vérifient leur format, mais pas leur existence dans les autres services. Elles ne calculent pas de total et ne réservent pas de stock. Supprimer un utilisateur ou un produit ne supprime pas les commandes correspondantes. Ces choix permettent de travailler sur une Gateway sans introduire de dépendances métier distribuées. Le champ role des utilisateurs est une donnée de démonstration, pas un contrôle d'autorisation.

## Scénarios de panne

La procédure détaillée se trouve dans [docs/SCENARIOS.md](docs/SCENARIOS.md).

~~~sh
# Produits répond 503 sur ses routes métier, /health reste accessible
python run.py --service products --mode unavailable

# Commandes répond après 5 secondes, /health reste immédiat
python run.py --service orders --delay-ms 5000
~~~

Arrêtez d'abord l'instance normale du service concerné pour libérer son port. Pour revenir au fonctionnement nominal, arrêtez la simulation et relancez sans ces options, en vérifiant aussi les variables d'environnement.

Une connexion refusée permet de tester l'erreur 502 de la Gateway. Une réponse amont 503 reste 503. Un délai de Gateway inférieur au retard du service permet de tester 504. Les services fournis ne génèrent pas eux-mêmes de 401, 429 ou 504.

## Tests automatisés du paquet

Depuis ce dossier :

~~~sh
python -m pytest tests -v
~~~

Les tests ouvrent des ports locaux temporaires. Ils couvrent les routes, les validations, les filtres, les transitions de commandes, les appels concurrents, l'isolation des données, les simulations et le démarrage/arrêt des trois processus. Ils ne modifient pas les données de services déjà lancés. Une politique réseau locale doit autoriser les échanges avec 127.0.0.1.

Ces tests vérifient **les services fournis**. Vous devez écrire séparément les tests de votre Gateway.

## Documentation et exemples

- [Documentation complète des routes](docs/API.md) : corps JSON, filtres, statuts et exemples de réponses.
- [Scénarios de vérification de la Gateway](docs/SCENARIOS.md).
- [Requêtes HTTP prêtes à utiliser](examples/requests.http), avec un client compatible avec ce format.
- Fichiers JSON dans examples/ pour les appels curl et PowerShell.

Exemple de création, depuis la racine du paquet :

~~~sh
curl -i -X POST http://127.0.0.1:8001/api/users -H "Content-Type: application/json" --data-binary @examples/user.json
~~~

Version PowerShell :

~~~powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/users -ContentType 'application/json' -InFile examples/user.json
~~~

## Dépannage

**Adresse déjà utilisée** : un autre processus occupe un port. Arrêtez votre ancien lancement ou changez le port, puis adaptez la configuration de votre Gateway. Le lanceur ne termine pas les processus étrangers qui occupent les ports.

**Connexion refusée** : vérifiez la ligne d'écoute, l'URL et /health. Pour une Gateway en conteneur, 127.0.0.1 désigne le conteneur, pas votre ordinateur.

**Erreur 404** : conservez /api/users, /api/products ou /api/orders. Les slashs finaux ne sont pas acceptés. Un identifiant absent donne aussi 404, avec un autre code d'erreur.

**Erreur 415 ou 411** : envoyez un JSON avec Content-Type: application/json et une longueur de corps connue. Les clients usuels calculent Content-Length automatiquement. Le transfert chunked des corps n'est pas pris en charge par ce serveur pédagogique.

**Erreur 409 après plusieurs essais** : une adresse email existe déjà, ou une commande a atteint un statut final. Choisissez une nouvelle adresse, une nouvelle commande ou redémarrez le service pour réinitialiser ses données.

## Organisation du code

~~~text
requirements.txt       Dépendances FastAPI, Uvicorn, HTTPX et pytest figées
.venv/                 Environnement local créé à l’installation, non distribué
run.py                 Lance un service ou les trois processus
services/data.py       Données initiales et ports par défaut
services/domain.py     Validation et opérations métier en mémoire
services/http.py       Fabrique FastAPI et routes métier
services/models.py     Schémas Pydantic stricts
services/runtime.py    Hébergement Uvicorn des lanceurs et tests
services/users.py      Entrée ASGI Utilisateurs (idem products et orders)
services/__init__.py   Déclaration du paquet Python
tests/                 Tests unitaires et d'intégration HTTP
docs/                  Contrats et scénarios
examples/              Corps JSON et requêtes HTTP
~~~

Références : [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [HTTPX](https://www.python-httpx.org/) et [pytest](https://docs.pytest.org/).

## Lancement ASGI direct facultatif

Dans trois terminaux avec le venv actif, depuis ce dossier :

    python -m uvicorn services.users:app --host 127.0.0.1 --port 8001
    python -m uvicorn services.products:app --host 127.0.0.1 --port 8002
    python -m uvicorn services.orders:app --host 127.0.0.1 --port 8003

Choisir ces commandes ou le lanceur run.py ; ne pas démarrer deux instances sur les mêmes ports. Après le premier routage réussi de votre Gateway, l’exercice de séparation consiste à rendre chaque application autonome, avec ses sources, ses dépendances et ses tests.

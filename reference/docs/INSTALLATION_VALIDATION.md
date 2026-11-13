# Validation du paquet FastAPI

Validation du 2 novembre 2026 sous Windows avec Python 3.12.14, dans une copie vierge avec un nouveau venv et installation de requirements.txt.

Commande : python -m pytest tests -v.

Résultat : **19 tests réussis**. Ils couvrent les contrats métier et HTTP, le lanceur de trois processus, les schémas OpenAPI, l’interface /docs, les erreurs Pydantic conservées en 400 et la disponibilité de /health pendant une lenteur simulée.

Les trois commandes Uvicorn directes services.users:app, services.products:app et services.orders:app ont également été vérifiées avec /health et /openapi.json sur des ports temporaires.

Les versions exactes sont figées dans requirements.txt. Starlette émet un avertissement de dépréciation pour son client de test HTTPX avec ces versions ; les tests réussissent. Les instructions Linux/macOS sont fournies mais n’ont pas été exécutées sur ces systèmes. Les venv et caches ne sont pas inclus dans l’archive.

## Installation reproductible

La création d’un venv vierge, l’installation des versions figées avec python -m pip install -r requirements.txt et l’utilisation de cet interpréteur ont été vérifiées dans une copie indépendante. Les tests ont réussi avec ces dépendances. La suite finale ajoute aussi le contrôle d’une erreur interne JSON 500 sans fuite de détail technique.

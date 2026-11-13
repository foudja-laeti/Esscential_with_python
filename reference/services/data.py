"""Jeux de données fictifs, rechargés à chaque démarrage."""
SEEDS = {
    "users": [
        {"id": 1, "name": "Alice Martin", "email": "alice@example.test", "role": "customer"},
        {"id": 2, "name": "Samir Durand", "email": "samir@example.test", "role": "customer"},
        {"id": 3, "name": "Léa Bernard", "email": "lea@example.test", "role": "staff"},
    ],
    "products": [
        {"id": 1, "name": "Clavier compact", "priceCents": 4990, "stock": 12},
        {"id": 2, "name": "Souris ergonomique", "priceCents": 2990, "stock": 25},
        {"id": 3, "name": "Écran 24 pouces", "priceCents": 15900, "stock": 0},
    ],
    "orders": [
        {"id": 1, "userId": 1, "items": [{"productId": 1, "quantity": 1}, {"productId": 2, "quantity": 2}], "status": "pending"},
        {"id": 2, "userId": 2, "items": [{"productId": 3, "quantity": 1}], "status": "confirmed"},
    ],
}
DEFAULT_PORTS = {"users": 8001, "products": 8002, "orders": 8003}

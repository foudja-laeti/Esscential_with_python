"""Stockage indépendant en mémoire et règles métier minimales."""
from copy import deepcopy
from threading import RLock
import re
from .data import SEEDS


class ApiError(Exception):
    def __init__(self, status, code, message, headers=None):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
        self.headers = headers or {}


def invalid(message):
    raise ApiError(400, "VALIDATION_ERROR", message)


def integer(value, field, minimum=1, maximum=1_000_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        invalid(f"{field} doit être un entier entre {minimum} et {maximum}.")
    return value


def string(value, field, maximum=120):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        invalid(f"{field} doit contenir de 1 à {maximum} caractères après suppression des espaces de bord.")
    return value.strip()


def fields(body, allowed, required):
    if not isinstance(body, dict) or not body:
        invalid("Le corps doit être un objet JSON non vide.")
    if set(body) - set(allowed):
        invalid("Le corps contient des champs non autorisés.")
    if set(required) - set(body):
        invalid("Champs obligatoires manquants : " + ", ".join(sorted(set(required) - set(body))))


class Store:
    def __init__(self, service):
        self.service = service
        self.rows = {row["id"]: deepcopy(row) for row in SEEDS[service]}
        self.next_id = max(self.rows) + 1
        self.lock = RLock()

    def validate(self, body, partial=False):
        if self.service == "users":
            fields(body, {"name", "email", "role"}, set() if partial else {"name", "email"})
            result = {}
            if "name" in body:
                result["name"] = string(body["name"], "name")
            if "email" in body:
                email = string(body["email"], "email", 254).lower()
                if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                    invalid("email doit avoir un format valide.")
                result["email"] = email
            if "role" in body:
                if body["role"] not in ("customer", "staff"):
                    invalid("role doit valoir customer ou staff.")
                result["role"] = body["role"]
            elif not partial:
                result["role"] = "customer"
            return result
        if self.service == "products":
            fields(body, {"name", "priceCents", "stock"}, set() if partial else {"name", "priceCents", "stock"})
            result = {}
            if "name" in body:
                result["name"] = string(body["name"], "name")
            for key in ("priceCents", "stock"):
                if key in body:
                    result[key] = integer(body[key], key, 0)
            return result
        if partial:
            fields(body, {"status"}, {"status"})
            if body["status"] not in ("pending", "confirmed", "cancelled"):
                invalid("status doit valoir pending, confirmed ou cancelled.")
            return {"status": body["status"]}
        fields(body, {"userId", "items"}, {"userId", "items"})
        user_id = integer(body["userId"], "userId")
        if not isinstance(body["items"], list) or not 1 <= len(body["items"]) <= 100:
            invalid("items doit contenir de 1 à 100 lignes.")
        items, seen = [], set()
        for item in body["items"]:
            fields(item, {"productId", "quantity"}, {"productId", "quantity"})
            product_id = integer(item["productId"], "productId")
            quantity = integer(item["quantity"], "quantity", 1, 1000)
            if product_id in seen:
                invalid("Un productId ne doit apparaître qu'une seule fois.")
            seen.add(product_id)
            items.append({"productId": product_id, "quantity": quantity})
        return {"userId": user_id, "items": items, "status": "pending"}

    def unique_email(self, row, except_id=None):
        if self.service == "users" and any(r["email"] == row["email"] and i != except_id for i, r in self.rows.items()):
            raise ApiError(409, "EMAIL_EXISTS", "Cette adresse email est déjà utilisée.")

    def get(self, ident):
        with self.lock:
            if ident not in self.rows:
                raise ApiError(404, "RESOURCE_NOT_FOUND", "Ressource introuvable.")
            return deepcopy(self.rows[ident])

    def create(self, body):
        with self.lock:
            row = self.validate(body)
            self.unique_email(row)
            row = {"id": self.next_id, **row}
            self.next_id += 1
            self.rows[row["id"]] = row
            return deepcopy(row)

    def update(self, ident, body):
        with self.lock:
            old = self.get(ident)
            changes = self.validate(body, partial=True)
            if self.service == "orders" and changes["status"] != old["status"] and old["status"] != "pending":
                raise ApiError(409, "INVALID_TRANSITION", "Une commande finale ne peut plus changer de statut.")
            new = {**old, **changes}
            self.unique_email(new, ident)
            self.rows[ident] = new
            return deepcopy(new)

    def delete(self, ident):
        with self.lock:
            self.get(ident)
            del self.rows[ident]

    def listing(self, query):
        allowed = {"page", "limit"} | ({"status", "userId"} if self.service == "orders" else {"q"})
        if set(query) - allowed or any(len(v) != 1 for v in query.values()):
            invalid("Paramètre de recherche inconnu ou répété.")
        def number(key, default, maximum):
            raw = query.get(key, [str(default)])[0]
            if not re.fullmatch(r"[0-9]{1,10}", raw):
                invalid(f"{key} doit être un entier positif.")
            return integer(int(raw), key, 1, maximum)
        page, limit = number("page", 1, 1_000_000), number("limit", 20, 100)
        with self.lock:
            rows = deepcopy(list(self.rows.values()))
        if "q" in query:
            term = query["q"][0].casefold()
            if len(term) > 120:
                invalid("q ne peut pas dépasser 120 caractères.")
            rows = [r for r in rows if term in r["name"].casefold() or term in r.get("email", "").casefold()]
        if "status" in query:
            status = query["status"][0]
            if status not in ("pending", "confirmed", "cancelled"):
                invalid("status doit valoir pending, confirmed ou cancelled.")
            rows = [r for r in rows if r["status"] == status]
        if "userId" in query:
            user_id = number("userId", 1, 1_000_000_000)
            rows = [r for r in rows if r["userId"] == user_id]
        rows.sort(key=lambda r: r["id"])
        start = (page - 1) * limit
        return {"data": rows[start:start + limit], "meta": {"page": page, "limit": limit, "total": len(rows)}}

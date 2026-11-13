"""Stockage en mémoire et règles métier du service Produits."""
from copy import deepcopy
from threading import RLock
import re
from .data import SEED


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
    def __init__(self):
        self.rows = {row["id"]: deepcopy(row) for row in SEED}
        self.next_id = max(self.rows) + 1
        self.lock = RLock()

    def validate(self, body, partial=False):
        fields(body, {"name", "priceCents", "stock"}, set() if partial else {"name", "priceCents", "stock"})
        result = {}
        if "name" in body:
            result["name"] = string(body["name"], "name")
        for key in ("priceCents", "stock"):
            if key in body:
                result[key] = integer(body[key], key, 0)
        return result

    def get(self, ident):
        with self.lock:
            if ident not in self.rows:
                raise ApiError(404, "RESOURCE_NOT_FOUND", "Ressource introuvable.")
            return deepcopy(self.rows[ident])

    def create(self, body):
        with self.lock:
            row = {"id": self.next_id, **self.validate(body)}
            self.next_id += 1
            self.rows[row["id"]] = row
            return deepcopy(row)

    def update(self, ident, body):
        with self.lock:
            old = self.get(ident)
            new = {**old, **self.validate(body, partial=True)}
            self.rows[ident] = new
            return deepcopy(new)

    def delete(self, ident):
        with self.lock:
            self.get(ident)
            del self.rows[ident]

    def listing(self, query):
        allowed = {"page", "limit", "q"}
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
            rows = [r for r in rows if term in r["name"].casefold()]
        rows.sort(key=lambda r: r["id"])
        start = (page - 1) * limit
        return {"data": rows[start:start + limit], "meta": {"page": page, "limit": limit, "total": len(rows)}}
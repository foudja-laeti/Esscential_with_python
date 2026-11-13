"""Entrée ASGI du service products."""
from .http import create_app

app = create_app("products")

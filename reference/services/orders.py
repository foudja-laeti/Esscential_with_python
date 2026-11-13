"""Entrée ASGI du service orders."""
from .http import create_app

app = create_app("orders")

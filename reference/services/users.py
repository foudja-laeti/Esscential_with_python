"""Entrée ASGI du service users."""
from .http import create_app

app = create_app("users")

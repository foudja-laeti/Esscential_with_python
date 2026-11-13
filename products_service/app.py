"""Entrée ASGI du service Produits (lancement direct avec uvicorn)."""
from .http import create_app

app = create_app()
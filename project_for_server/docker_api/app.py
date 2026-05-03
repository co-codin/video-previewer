"""Тонкая обёртка для Docker-деплоя. Вся логика — в previewer_core."""
from previewer_core import create_app

app = create_app()

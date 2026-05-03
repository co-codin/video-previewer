"""Python-клиент для сервиса генерации превью."""
from previewer_client.client import (
    DEFAULT_BASE_URL,
    VideoPreviewClient,
    quick_preview,
    quick_preview_sync,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "VideoPreviewClient",
    "quick_preview",
    "quick_preview_sync",
]

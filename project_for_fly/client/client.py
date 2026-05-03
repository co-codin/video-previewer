"""Тонкая обёртка над previewer_client с дефолтным URL Fly-деплоя.

Сохраняет обратную совместимость: ``from client import VideoPreviewClient``.
"""
from previewer_client import (
    VideoPreviewClient as _BaseClient,
    quick_preview as _quick_preview,
    quick_preview_sync as _quick_preview_sync,
)

DEFAULT_API_URL = "https://yv-preview.fly.dev"


class VideoPreviewClient(_BaseClient):
    def __init__(self, base_url: str = DEFAULT_API_URL, **kwargs):
        super().__init__(base_url=base_url, **kwargs)


async def quick_preview(url, save_path=None, api_url: str = DEFAULT_API_URL):
    return await _quick_preview(url, save_path=save_path, api_url=api_url)


def quick_preview_sync(url, save_path=None, api_url: str = DEFAULT_API_URL):
    return _quick_preview_sync(url, save_path=save_path, api_url=api_url)


__all__ = ["VideoPreviewClient", "quick_preview", "quick_preview_sync", "DEFAULT_API_URL"]

"""Конфигурация сервиса. Все значения переопределяемы через переменные окружения."""
import os

WIDTH: int = int(os.environ.get("PREVIEW_WIDTH", "640"))
TIMEOUT: int = int(os.environ.get("PREVIEW_TIMEOUT", "10"))  # секунды
NET_CONCURRENCY: int = int(os.environ.get("PREVIEW_NET_CONCURRENCY", "20"))
PAGE_CONCURRENCY: int = int(os.environ.get("PREVIEW_PAGE_CONCURRENCY", "4"))
PLAYER_PREFIX: str = os.environ.get(
    "PREVIEW_PLAYER_PREFIX",
    "https://runtime.video.cloud.yandex.net/player/video/",
)

JPEG_QUALITY: int = int(os.environ.get("PREVIEW_JPEG_QUALITY", "90"))
VIEWPORT_WIDTH: int = int(os.environ.get("PREVIEW_VIEWPORT_WIDTH", "1280"))
VIEWPORT_HEIGHT: int = int(os.environ.get("PREVIEW_VIEWPORT_HEIGHT", "720"))

# Доп. флаг для Chromium. На server раньше передавали --headless=new.
# Допустимые значения: "" (старый headless), "new" (новый headless)
CHROMIUM_HEADLESS_MODE: str = os.environ.get("PREVIEW_HEADLESS_MODE", "new")

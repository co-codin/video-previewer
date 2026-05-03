"""Создание HTTPS-клиента httpx с правильным SSL-контекстом."""
import ssl

import certifi
import httpx

from previewer_core.config import NET_CONCURRENCY


def make_async_client() -> httpx.AsyncClient:
    """Возвращает httpx.AsyncClient с certifi-сертификатами и лимитами."""
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    limits = httpx.Limits(max_connections=NET_CONCURRENCY)
    return httpx.AsyncClient(verify=ssl_ctx, limits=limits)

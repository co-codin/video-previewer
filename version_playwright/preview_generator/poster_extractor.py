"""Извлечение URL постера из элементов страницы и его скачивание через httpx."""
import logging
from typing import Optional
from urllib.parse import urljoin

import httpx
from playwright.async_api import Error as PlaywrightError, Page

from preview_generator.constants import (
    DOWNLOAD_TIMEOUT_SEC,
    MIN_IMAGE_BYTES,
    POSTER_MAX_BYTES,
    POSTER_PROBE_TIMEOUT_MS,
)

logger = logging.getLogger(__name__)


async def _try_attribute(page: Page, selector: str, attr: str) -> Optional[str]:
    """Пытается прочитать атрибут у первого элемента, подходящего под селектор."""
    try:
        return await page.locator(selector).first.get_attribute(
            attr, timeout=POSTER_PROBE_TIMEOUT_MS,
        )
    except PlaywrightError:
        return None


async def extract_poster_url(page: Page) -> Optional[str]:
    """Пытается извлечь URL постера из разных источников страницы."""
    logger.debug("Поиск URL постера...")

    sources = [
        ("video[poster]", "poster"),
        ('meta[property="og:image"]', "content"),
        ('meta[name="twitter:image"]', "content"),
        ('video img, [role="video"] img', "src"),
    ]

    for selector, attr in sources:
        value = await _try_attribute(page, selector, attr)
        if value:
            logger.debug("Найден постер через %s: %s", selector, value)
            return urljoin(page.url, value)

    logger.debug("URL постера не найден.")
    return None


async def download_image(client: httpx.AsyncClient, url: str) -> Optional[bytes]:
    """Скачивает изображение через переиспользуемый httpx-клиент.

    Возвращает None при любых ошибках или некорректном содержимом.
    """
    logger.debug("Попытка скачать постер: %s", url)
    try:
        response = await client.get(url, timeout=DOWNLOAD_TIMEOUT_SEC)
    except httpx.HTTPError:
        logger.warning("Ошибка httpx при скачивании постера %s", url, exc_info=True)
        return None

    if response.status_code != 200:
        logger.warning("Ошибка при скачивании постера %s: статус %s", url, response.status_code)
        return None

    content_type = response.headers.get("Content-Type", "").lower()
    if "image" not in content_type:
        logger.warning("Неверный Content-Type для постера %s: %s", url, content_type)
        return None

    content_length = int(response.headers.get("Content-Length", 0))
    if content_length and content_length > POSTER_MAX_BYTES:
        logger.warning(
            "Размер постера %s (%s байт) превышает лимит %s",
            url, content_length, POSTER_MAX_BYTES,
        )
        return None

    img_bytes = response.content
    if len(img_bytes) < MIN_IMAGE_BYTES:
        logger.warning("Скачанный постер %s слишком мал (%s байт)", url, len(img_bytes))
        return None

    logger.debug("Постер успешно скачан: %s (%s байт)", url, len(img_bytes))
    return img_bytes

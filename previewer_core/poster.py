"""Извлечение URL постера из HTML страницы видеоплеера."""
import json
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from previewer_core.config import TIMEOUT

logger = logging.getLogger(__name__)

_RE_POSTER_JSON = re.compile(r'"poster"\s*:\s*"((?:[^"\\]|\\.)*)"')
_RE_CSS_URL = re.compile(r'url\(\s*["\']?([^"\')]+)["\']?\s*\)')


async def fetch_html(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """Скачивает HTML страницы. Возвращает None при любой ошибке."""
    try:
        response = await client.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError:
        logger.exception("Не удалось скачать HTML для %s", url)
        return None


async def download(client: httpx.AsyncClient, url: str) -> Optional[bytes]:
    """Скачивает бинарный контент по URL. Возвращает None при ошибке."""
    try:
        response = await client.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.content
    except httpx.HTTPError:
        logger.exception("Не удалось скачать ресурс %s", url)
        return None


def _decode_json_string(raw: str) -> str:
    """Декодирует строку из inline-JSON: \\u002F → /, \\/ → / и т.п.

    Используем json.loads, который корректно обрабатывает все JSON-эскейпы.
    """
    try:
        return json.loads(f'"{raw}"')
    except json.JSONDecodeError:
        return raw


def extract_poster(html: str) -> Optional[str]:
    """Пытается найти URL постера в HTML несколькими способами по убыванию надёжности."""
    soup = BeautifulSoup(html, "html.parser")

    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        return meta["content"]

    twitter = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter and twitter.get("content"):
        return twitter["content"]

    div = soup.find("div", class_="vjs-poster")
    if div and (style := div.get("style")):
        m = _RE_CSS_URL.search(style)
        if m:
            return m.group(1)

    m = _RE_POSTER_JSON.search(html)
    if m:
        return _decode_json_string(m.group(1))

    return None

"""FastAPI-сервис генерации превью."""
import asyncio
import base64
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from previewer_core.browser import browser_lifespan, grab_with_browser
from previewer_core.config import PAGE_CONCURRENCY, PLAYER_PREFIX
from previewer_core.http_client import make_async_client
from previewer_core.image import to_jpeg
from previewer_core.poster import download, extract_poster, fetch_html

logger = logging.getLogger(__name__)


class Items(BaseModel):
    items: List[str]


async def _generate(
    urls: List[str],
    http_client: httpx.AsyncClient,
    browser,
    page_semaphore: asyncio.Semaphore,
) -> Dict[str, Optional[bytes]]:
    """Для каждого URL пытается достать постер из HTML, иначе — через браузер."""
    result: Dict[str, Optional[bytes]] = {}

    async def handle(url: str) -> None:
        html = await fetch_html(http_client, url)
        poster_url = extract_poster(html) if html else None
        if poster_url:
            img = await download(http_client, poster_url)
            if img:
                result[url] = img
                return
        async with page_semaphore:
            result[url] = await grab_with_browser(browser, url)

    await asyncio.gather(*(handle(u) for u in urls))
    return result


def create_app() -> FastAPI:
    """FastAPI-app с lifespan: один browser и один httpx-client на всё приложение."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with browser_lifespan() as browser, make_async_client() as client:
            app.state.browser = browser
            app.state.http_client = client
            app.state.page_semaphore = asyncio.Semaphore(PAGE_CONCURRENCY)
            logger.info("Сервис инициализирован: браузер и httpx-клиент готовы")
            yield

    app = FastAPI(title="Yandex-video preview", lifespan=lifespan)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/preview")
    async def preview(data: Items) -> Dict[str, Optional[str]]:
        if not data.items:
            raise HTTPException(400, "items list is empty")

        urls = [
            x if x.startswith("http") else f"{PLAYER_PREFIX}{x}"
            for x in data.items
        ]

        raw = await _generate(
            urls,
            app.state.http_client,
            app.state.browser,
            app.state.page_semaphore,
        )
        return {
            url: (base64.b64encode(to_jpeg(img)).decode() if img else None)
            for url, img in raw.items()
        }

    return app

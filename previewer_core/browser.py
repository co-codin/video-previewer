"""Захват превью через headless-браузер, когда HTML-парсинг не дал результата."""
import base64
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Playwright,
    async_playwright,
)

from previewer_core.config import (
    CHROMIUM_HEADLESS_MODE,
    TIMEOUT,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)

logger = logging.getLogger(__name__)


_CANVAS_CAPTURE_JS = """v => {
    const c = document.createElement('canvas');
    c.width = v.videoWidth || v.clientWidth;
    c.height = v.videoHeight || v.clientHeight;
    const ctx = c.getContext('2d');
    try {
        ctx.drawImage(v, 0, 0, c.width, c.height);
        return c.toDataURL('image/png').split(',')[1];
    } catch (e) {
        return null;
    }
}"""


def _chromium_launch_args() -> list[str]:
    args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--ignore-certificate-errors",
        "--autoplay-policy=no-user-gesture-required",
    ]
    if CHROMIUM_HEADLESS_MODE == "new":
        args.append("--headless=new")
    return args


@asynccontextmanager
async def browser_lifespan() -> AsyncIterator[Browser]:
    """Запускает Playwright + Chromium на время жизни приложения."""
    pw: Playwright = await async_playwright().start()
    try:
        browser = await pw.chromium.launch(
            channel="chrome",
            headless=True,
            args=_chromium_launch_args(),
        )
        try:
            yield browser
        finally:
            await browser.close()
    finally:
        await pw.stop()


async def grab_with_browser(browser: Browser, url: str) -> Optional[bytes]:
    """Открывает URL, пытается извлечь постер, иначе скриншотит видео-элемент.

    Контекст всегда закрывается в finally.
    """
    ctx: BrowserContext = await browser.new_context(
        ignore_https_errors=True,
        viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
    )
    try:
        page = await ctx.new_page()
        full_url = url + ("&" if "?" in url else "?") + "autoplay=1"

        try:
            await page.goto(full_url, timeout=TIMEOUT * 1000)
            await page.wait_for_selector("video", timeout=TIMEOUT * 1000)
        except Exception:
            logger.exception("Не удалось открыть страницу %s", url)
            return None

        poster = await page.eval_on_selector("video", "v => v?.poster") or ""
        if poster:
            try:
                await page.goto(poster, timeout=TIMEOUT * 1000)
                return await page.screenshot(type="png", full_page=True)
            except Exception:
                logger.exception("Не удалось скачать постер %s через браузер", poster)

        try:
            video_handle = await page.query_selector("video")
            if video_handle:
                b64 = await page.evaluate(_CANVAS_CAPTURE_JS, video_handle)
                if b64:
                    return base64.b64decode(b64)
        except Exception:
            logger.exception("Canvas-захват видео не удался для %s", url)

        try:
            return await page.screenshot(type="png")
        except Exception:
            logger.exception("Скриншот страницы не удался для %s", url)
            return None
    finally:
        await ctx.close()

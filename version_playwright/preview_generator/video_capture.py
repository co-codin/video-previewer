"""Работа с <video>: ожидание готовности, seek, скриншот элемента."""
import logging

from playwright.async_api import (
    ElementHandle,
    Error as PlaywrightError,
    Page,
)

from preview_generator.constants import (
    POST_SEEK_PAUSE_MS,
    SEEK_FALLBACK_PAUSE_MS,
    SEEK_TIMEOUT_MS,
)
from preview_generator.exceptions import VideoElementNotFoundError

logger = logging.getLogger(__name__)


_SEEK_AND_WAIT_JS = """async (element) => {
    if (!element) return;
    if (element.readyState < element.HAVE_METADATA) {
        await new Promise(resolve =>
            element.addEventListener('loadedmetadata', resolve, { once: true })
        );
    }
    const duration = element.duration || 1;
    const seekTime = Math.min(1, duration);

    return new Promise((resolve, reject) => {
        const timeout = %d;
        const timeoutId = setTimeout(() => {
            reject(new Error(`Timeout ${timeout}ms waiting for seeked`));
        }, timeout);

        const onSeeked = () => {
            clearTimeout(timeoutId);
            element.removeEventListener('seeked', onSeeked);
            resolve();
        };
        element.addEventListener('seeked', onSeeked);
        element.currentTime = seekTime;

        if (element.currentTime === seekTime &&
            element.readyState >= element.HAVE_CURRENT_DATA) {
            onSeeked();
        }
    });
}""" % SEEK_TIMEOUT_MS


async def wait_for_video_element(page: Page, timeout_ms: int, url: str) -> ElementHandle:
    """Ждёт появления <video>; пробрасывает VideoElementNotFoundError если не нашли."""
    logger.info("Ожидание видео-элемента для %s", url)
    element = await page.wait_for_selector("video", timeout=timeout_ms)
    if not element:
        raise VideoElementNotFoundError(
            f"Элемент <video> не найден после ожидания на {url}"
        )
    return element


async def wait_for_first_frame(page: Page, video_element: ElementHandle, timeout_ms: int) -> None:
    """Ждёт, пока у video readyState >= 2 (HAVE_CURRENT_DATA) или появится poster."""
    await page.wait_for_function(
        "element => element.readyState >= 2 || element.poster",
        arg=video_element,
        timeout=timeout_ms,
    )


async def seek_to_first_second(page: Page, video_element: ElementHandle, url: str) -> None:
    """Перематывает видео на 1с и ждёт события 'seeked'.

    На ошибках логирует и делает короткую паузу — скриншот всё равно попробуют сделать.
    """
    try:
        logger.info("Установка video.currentTime = 1 и ожидание 'seeked' для %s", url)
        await page.evaluate(_SEEK_AND_WAIT_JS, video_element)
        await page.wait_for_timeout(POST_SEEK_PAUSE_MS)
        logger.info("Событие 'seeked' получено для %s", url)
    except PlaywrightError:
        logger.warning(
            "Ошибка при установке currentTime / ожидании 'seeked' для %s",
            url, exc_info=True,
        )
        await page.wait_for_timeout(SEEK_FALLBACK_PAUSE_MS)

"""Основной класс PreviewGenerator: связывает все шаги обработки URL."""
import asyncio
import logging
import os
from typing import List, Optional, Tuple

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    async_playwright,
)

from preview_generator.constants import (
    USER_AGENT,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)
from preview_generator.consent import dismiss_cookie_consent
from preview_generator.exceptions import (
    PlaywrightInitError,
    PreviewGeneratorError,
    ScreenshotError,
    VideoElementNotFoundError,
)
from preview_generator.filename import generate_output_filename
from preview_generator.image_io import resize_to_jpeg, validate_screenshot
from preview_generator.video_capture import (
    seek_to_first_second,
    wait_for_first_frame,
    wait_for_video_element,
)

logger = logging.getLogger("preview_generator_service_pw")


SUPPORTED_BROWSERS = ("chromium", "firefox", "webkit")


class PreviewGenerator:
    """Генерирует превью из видео по URL через Playwright."""

    def __init__(
        self,
        width: int = 640,
        max_workers: int = 5,
        timeout: int = 10,
        browser_type: str = "chromium",
    ):
        if browser_type not in SUPPORTED_BROWSERS:
            raise ValueError(
                f"Неверный тип браузера. Допустимые значения: {SUPPORTED_BROWSERS}"
            )

        self.width = width
        self.max_workers = max_workers
        self.timeout_ms = timeout * 1000
        self.browser_type_name = browser_type
        self.semaphore = asyncio.Semaphore(max_workers)

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

        logger.info(
            "Инициализирован PreviewGenerator: width=%s, workers=%s, "
            "timeout=%ss, browser=%s",
            width, max_workers, timeout, browser_type,
        )

    async def _initialize(self) -> None:
        """Поднимает Playwright и браузер однажды; повторные вызовы — no-op."""
        if self._browser:
            return

        try:
            logger.info("Инициализация Playwright...")
            self._playwright = await async_playwright().start()
            launcher = getattr(self._playwright, self.browser_type_name)

            logger.info("Запуск браузера %s...", self.browser_type_name)
            self._browser = await launcher.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--mute-audio",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            logger.info("Браузер %s успешно запущен", self.browser_type_name)
        except Exception as e:
            logger.exception("Ошибка при инициализации Playwright/браузера")
            await self.close()
            raise PlaywrightInitError(
                f"Не удалось инициализировать Playwright/браузер: {e}"
            )

    async def _process_single_url(self, url: str) -> Tuple[str, Optional[bytes]]:
        """Обрабатывает один URL и возвращает (url, jpeg_bytes | None)."""
        await self._initialize()
        if not self._browser:
            logger.error("Браузер не инициализирован для обработки %s", url)
            return url, None

        async with self.semaphore:
            return await self._process_with_browser(url)

    async def _process_with_browser(self, url: str) -> Tuple[str, Optional[bytes]]:
        """Открывает контекст/страницу и делает превью. Контекст всегда закрывается."""
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None
        try:
            logger.info("Начало обработки URL: %s", url)
            context = await self._browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            )
            page = await context.new_page()

            logger.info("Переход на страницу: %s", url)
            await page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")

            await dismiss_cookie_consent(page, url)

            video_element = await wait_for_video_element(page, self.timeout_ms, url)
            await wait_for_first_frame(page, video_element, self.timeout_ms)
            await seek_to_first_second(page, video_element, url)

            logger.info("Создание скриншота видео-элемента для %s", url)
            png_data = await video_element.screenshot()
            validate_screenshot(png_data, url)

            jpeg_bytes = resize_to_jpeg(png_data, self.width, url)
            logger.info("Успешно создано превью для %s", url)
            return url, jpeg_bytes

        except PlaywrightError:
            logger.exception("Ошибка Playwright при обработке %s", url)
            return url, None
        except (VideoElementNotFoundError, ScreenshotError):
            logger.exception("Ошибка генерации превью для %s", url)
            return url, None
        except PreviewGeneratorError:
            logger.exception("Ошибка генератора превью для %s", url)
            return url, None
        except Exception:
            logger.exception("Непредвиденная ошибка при обработке %s", url)
            return url, None
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def process_url_list(
        self, urls: List[str]
    ) -> List[Tuple[str, Optional[bytes]]]:
        """Параллельно обрабатывает список URL."""
        if not urls:
            return []

        await self._initialize()
        logger.info("Начало обработки %s URL с помощью Playwright", len(urls))

        tasks = [self._process_single_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        logger.info("Завершена обработка %s URL", len(urls))
        return [(url, data) for url, data in results if isinstance(url, str)]

    async def process_url_list_to_files(
        self, urls: List[str], output_dir: str,
    ) -> List[Tuple[str, Optional[str]]]:
        """Параллельно обрабатывает URL и сохраняет результаты в файлы."""
        os.makedirs(output_dir, exist_ok=True)

        pairs = await self.process_url_list(urls)
        result_paths: List[Tuple[str, Optional[str]]] = []

        for url, img_bytes in pairs:
            if not img_bytes:
                result_paths.append((url, None))
                continue

            filename = generate_output_filename(url)
            output_path = os.path.join(output_dir, filename)
            try:
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                logger.info("Сохранено изображение для %s в %s", url, output_path)
                result_paths.append((url, output_path))
            except OSError:
                logger.exception(
                    "Ошибка при сохранении изображения для %s в %s", url, output_path,
                )
                result_paths.append((url, None))

        return result_paths

    async def close(self) -> None:
        """Освобождает все ресурсы: браузер и Playwright."""
        if self._browser:
            try:
                await self._browser.close()
                logger.info("Браузер %s закрыт", self.browser_type_name)
            except Exception:
                logger.exception("Ошибка при закрытии браузера")
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
                logger.info("Playwright остановлен")
            except Exception:
                logger.exception("Ошибка при остановке Playwright")
            self._playwright = None

        logger.info("PreviewGenerator закрыт")

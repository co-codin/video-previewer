import asyncio
import logging
import os
import io
from typing import List, Tuple, Optional  # Убрали Dict, Any
from urllib.parse import urlparse, parse_qs  # Добавили parse_qs
# Убрали concurrent.futures

from PIL import Image
# Убрали Page из импорта playwright
import aiohttp # Добавили aiohttp

from playwright.async_api import (
    async_playwright, Playwright, Browser, Page, Error as PlaywrightError
) # Вернули Page

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('preview_generator_service_pw')


# --- Custom Exceptions ---


class PreviewGeneratorError(Exception):
    """Базовый класс для исключений генератора превью."""


class PlaywrightInitError(PreviewGeneratorError):
    """Ошибка инициализации Playwright или браузера."""


class VideoElementNotFoundError(PreviewGeneratorError):
    """Ошибка поиска видео-элемента на странице."""


class ScreenshotError(PreviewGeneratorError):
    """Ошибка создания скриншота."""


class PageLoadError(PreviewGeneratorError):
    """Ошибка загрузки страницы."""


# --- Preview Generator Class ---


class PreviewGenerator:
    """
    Класс для генерации превью-изображений из видео по URL
    с использованием Playwright.
    """

    def __init__(
        self,
        width: int = 640,
        max_workers: int = 5,
        timeout: int = 10,
        browser_type: str = 'chromium'  # 'chromium', 'firefox', 'webkit'
    ):
        """
        Инициализация генератора превью.

        Args:
            width: Ширина выходного изображения в пикселях.
            max_workers: Максимальное количество параллельных
                         обработчиков (страниц).
            timeout: Таймаут ожидания загрузки элементов в секундах.
            browser_type: Тип браузера для использования
                          ('chromium', 'firefox', 'webkit').
        """
        if browser_type not in ['chromium', 'firefox', 'webkit']:
            raise ValueError(
                "Неверный тип браузера. Допустимые значения: "
                "'chromium', 'firefox', 'webkit'"
            )

        self.width = width
        self.max_workers = max_workers
        self.timeout_ms = timeout * 1000  # Playwright использует миллисекунды
        self.browser_type_name = browser_type
        self.semaphore = asyncio.Semaphore(max_workers)

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

        logger.info(
            f"Инициализирован генератор превью (Playwright) с шириной "
            f"{width}px, {max_workers} обработчиками, таймаутом {timeout}s, "
            f"браузер: {browser_type}"
        )

    async def _initialize(self):
        """Асинхронно инициализирует Playwright и запускает браузер."""
        if self._browser:
            return  # Уже инициализирован

        try:
            logger.info("Инициализация Playwright...")
            self._playwright = await async_playwright().start()
            browser_launcher = getattr(
                self._playwright, self.browser_type_name
            )

            logger.info(f"Запуск браузера {self.browser_type_name}...")
            self._browser = await browser_launcher.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--mute-audio",
                    # Попытка скрыть автоматизацию
                    "--disable-blink-features=AutomationControlled",
                ]
            )
            logger.info(f"Браузер {self.browser_type_name} успешно запущен.")
        except Exception as e:
            logger.error(
                "Ошибка при инициализации Playwright или запуске браузера: "
                f"{e}"
            )
            await self.close()  # Попытка очистить ресурсы
            raise PlaywrightInitError(
                f"Не удалось инициализировать Playwright/браузер: {e}"
            )

    def _generate_output_filename(self, url: str) -> str:
        """
        Генерирует имя выходного файла на основе URL.
        Для YouTube извлекает video ID.
        """
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        base_name = None

        # Обработка YouTube URL
        is_youtube = ('youtube.com' in parsed_url.netloc or
                      'youtu.be' in parsed_url.netloc)
        if is_youtube:
            # Получаем первый 'v' параметр
            video_id = query_params.get('v', [None])[0]
            if video_id:
                base_name = video_id
            # Для коротких ссылок youtu.be/VIDEOID
            elif (parsed_url.path and len(parsed_url.path) > 1 and
                  'youtu.be' in parsed_url.netloc):
                base_name = parsed_url.path.lstrip('/')

        # Если не YouTube или не удалось извлечь ID, используем старую логику
        if not base_name:
            path_part = parsed_url.path
            base_name = os.path.splitext(os.path.basename(path_part))[0]
            # Если путь пустой или корневой
            if not base_name or base_name == '/':
                # Заменяем точки, двоеточия
                base_name = parsed_url.netloc.replace('.', '_')
                base_name = base_name.replace(':', '_')

        # Очистка имени файла от нежелательных символов
        safe_chars = ('_', '-')
        safe_base_name = "".join(
            c for c in base_name if c.isalnum() or c in safe_chars
        ).rstrip()
        # Если имя стало пустым после очистки
        if not safe_base_name:
            safe_base_name = "preview"  # Имя по умолчанию

        return f"{safe_base_name}_poster_pw.jpg"

    async def _extract_poster_url(self, page: Page) -> Optional[str]:
        """Пытается извлечь URL постера из разных источников на странице."""
        logger.debug("Поиск URL постера...")

        # 1. Атрибут poster у video
        try:
            poster = await page.locator('video').get_attribute('poster', timeout=500)
            if poster:
                logger.debug(f"Найден poster в <video>: {poster}")
                return poster
        except PlaywrightError:
            logger.debug("Атрибут poster у <video> не найден или таймаут.")

        # 2. Open Graph image
        try:
            og_image = await page.locator('meta[property="og:image"]').get_attribute('content', timeout=500)
            if og_image:
                logger.debug(f"Найден og:image: {og_image}")
                return og_image
        except PlaywrightError:
            logger.debug("Мета-тег og:image не найден или таймаут.")

        # 3. Twitter Card image
        try:
            twitter_image = await page.locator('meta[name="twitter:image"]').get_attribute('content', timeout=500)
            if twitter_image:
                logger.debug(f"Найден twitter:image: {twitter_image}")
                return twitter_image
        except PlaywrightError:
            logger.debug("Мета-тег twitter:image не найден или таймаут.")

        # 4. Первая img внутри video-контейнера (если есть)
        # Этот селектор может быть не универсальным
        try:
            # Ищем img внутри элемента с тегом video или атрибутом role=video (для некоторых плееров)
            img_in_video = await page.locator('video img, [role="video"] img').first.get_attribute('src', timeout=500)
            if img_in_video:
                 logger.debug(f"Найден src у img внутри video: {img_in_video}")
                 # Иногда src может быть относительным, делаем его абсолютным
                 return page.urljoin(img_in_video)
        except PlaywrightError:
            logger.debug("Img внутри video не найден или таймаут.")


        logger.debug("URL постера не найден.")
        return None

    async def _download_image(self, url: str) -> Optional[bytes]:
        """Скачивает изображение по URL с помощью aiohttp."""
        logger.debug(f"Попытка скачать постер: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                # Устанавливаем таймаут на скачивание
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '').lower()
                        if 'image' in content_type:
                            # Ограничение размера скачиваемого файла (например, 10 МБ)
                            max_size = 10 * 1024 * 1024
                            content_length = int(response.headers.get('Content-Length', 0))
                            if content_length > max_size:
                                logger.warning(f"Размер постера {url} ({content_length} байт) превышает лимит {max_size}.")
                                return None

                            img_bytes = await response.read()
                            if len(img_bytes) > 100: # Проверка на минимальный размер
                                logger.debug(f"Постер успешно скачан: {url} ({len(img_bytes)} байт)")
                                return img_bytes
                            else:
                                logger.warning(f"Скачанный постер {url} слишком мал ({len(img_bytes)} байт).")
                                return None
                        else:
                            logger.warning(f"Неверный Content-Type для постера {url}: {content_type}")
                            return None
                    else:
                        logger.warning(f"Ошибка при скачивании постера {url}: статус {response.status}")
                        return None
        except asyncio.TimeoutError:
             logger.warning(f"Таймаут при скачивании постера: {url}")
             return None
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка aiohttp при скачивании постера {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при скачивании постера {url}: {e}")
            return None


    async def _process_single_url(
        self, url: str
    ) -> Tuple[str, Optional[bytes]]:
        """
        Обрабатывает одну ссылку и возвращает пару (url, image_bytes).
        Использует существующий браузер, но создает новый контекст и страницу.
        """
        await self._initialize()  # Убедимся, что браузер запущен
        if not self._browser:
            # Если инициализация не удалась ранее
            logger.error(f"Браузер не инициализирован для обработки {url}")
            return url, None

        context = None
        page = None
        # Ограничиваем количество одновременных страниц
        async with self.semaphore:
            try:
                logger.info(f"Начало обработки URL: {url}")
                # User agent для маскировки
                user_agent = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
                context = await self._browser.new_context(
                    user_agent=user_agent,
                    # Устанавливаем размер окна
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()

                logger.info(f"Переход на страницу: {url}")
                # Ждем загрузки DOM
                await page.goto(
                    url,
                    timeout=self.timeout_ms,
                    wait_until='domcontentloaded'
                )

                # --- Обработка плашки Cookie Consent (YouTube) ---
                try:
                    # Ищем форму согласия cookie
                    consent_form_selector = (
                        'ytd-consent-bump-v2-lightbox, '
                        'form[action*="consent.youtube.com"]'
                    )
                    consent_form = await page.query_selector(
                        consent_form_selector
                    )

                    if consent_form:
                        logger.info(
                            f"Найдена форма согласия cookie для {url}, "
                            f"ищем кнопку 'Принять все'..."
                        )
                        # Ищем кнопку внутри формы
                        accept_button_selector = (
                            'button[aria-label*="Accept"], '
                            'button[aria-label*="Agree"], '
                            'button:has-text("Accept all"), '
                            'button:has-text("Agree")'
                        )
                        accept_button = await consent_form.query_selector(
                            accept_button_selector
                        )
                        if accept_button:
                            logger.info(
                                "Найдена кнопка 'Принять все', кликаем..."
                            )
                            # Таймаут на клик
                            await accept_button.click(timeout=3000)
                            # Пауза после клика
                            await page.wait_for_timeout(500)
                            logger.info(
                                f"Клик по кнопке согласия выполнен для {url}"
                            )
                        else:
                            logger.warning(
                                f"Форма согласия найдена, но кнопка "
                                f"'Принять все' - нет для {url}"
                            )
                    else:
                        logger.info(
                            f"Форма/кнопка согласия cookie не найдена "
                            f"для {url} (возможно, уже принята)"
                        )
                except PlaywrightError as consent_err:
                    logger.warning(
                        f"Ошибка при обработке согласия cookie для {url}: "
                        f"{consent_err}"
                    )
                    # Продолжаем выполнение

                logger.info(f"Ожидание видео-элемента для {url}")
                video_element = await page.wait_for_selector(
                    'video', timeout=self.timeout_ms
                )
                # Доп. проверка, хотя wait_for_selector должен выбросить искл.
                if not video_element:
                    raise VideoElementNotFoundError(
                        f"Элемент <video> не найден после ожидания на {url}"
                    )

                logger.info(
                    f"Ожидание загрузки постера/первого кадра для {url}"
                )
                # Ждем, пока readyState >= 2 (HAVE_CURRENT_DATA)
                # или есть атрибут poster
                await page.wait_for_function(
                    "element => element.readyState >= 2 || element.poster",
                    arg=video_element,
                    timeout=self.timeout_ms
                )

                # --- Попытка №4: Установить currentTime и ждать 'seeked' ---
                try:
                    logger.info(
                        f"Установка video.currentTime = 1 и ожидание 'seeked' "
                        f"для {url}"
                    )
                    # Ожидаем промис, который разрешится при событии 'seeked'
                    await page.evaluate(
                        """async (element) => {
                            if (!element) return;
                            // Убедимся, что метаданные загружены
                            if (element.readyState < element.HAVE_METADATA) {
                                await new Promise(resolve =>
                                    element.addEventListener(
                                        'loadedmetadata',
                                        resolve,
                                        { once: true }
                                    )
                                );
                            }
                            // Не перематываем за пределы видео
                            const duration = element.duration || 1;
                            const seekTime = Math.min(1, duration);

                            return new Promise((resolve, reject) => {
                                const timeout = 5000; // 5 sec timeout
                                const timeoutId = setTimeout(() => {
                                    const msg = `Timeout ${timeout}ms ` +
                                                `waiting for seeked`;
                                    console.error(msg);
                                    reject(new Error(msg));
                                }, timeout);

                                const onSeeked = () => {
                                    clearTimeout(timeoutId);
                                    console.log('Seeked event received');
                                    element.removeEventListener(
                                        'seeked', onSeeked
                                    );
                                    resolve();
                                };
                                element.addEventListener('seeked', onSeeked);
                                element.currentTime = seekTime;

                                // Если currentTime уже там и данные есть,
                                // событие 'seeked' может не сработать.
                                // Вызываем обработчик вручную.
                                const minReadyState =
                                    element.HAVE_CURRENT_DATA;
                                if (element.currentTime === seekTime &&
                                    element.readyState >= minReadyState
                                ) {
                                    console.log(
                                        'currentTime already set, ' +
                                        'resolving early'
                                    );
                                    onSeeked();
                                }
                            });
                        }""",
                        video_element
                    )
                    # Пауза после seeked для стабильности
                    await page.wait_for_timeout(200)
                    logger.info(f"Событие 'seeked' получено для {url}")

                except PlaywrightError as seek_err:
                    logger.warning(
                        f"Ошибка при установке currentTime / ожидании "
                        f"'seeked' для {url}: {seek_err}"
                    )
                    # Пробуем сделать скриншот в любом случае
                    await page.wait_for_timeout(500)

                logger.info(f"Создание скриншота видео-элемента для {url}")
                png_data = await video_element.screenshot()
                # Добавим проверку на размер png данных перед обработкой
                # Произвольный порог > пустого файла
                min_screenshot_size = 100
                if not png_data or len(png_data) < min_screenshot_size:
                    raise ScreenshotError(
                        f"Получен пустой или слишком маленький скриншот "
                        f"({len(png_data)} байт) для {url}"
                    )

                # Обработка изображения с помощью Pillow
                img = Image.open(io.BytesIO(png_data))
                original_width, original_height = img.size
                if original_width == 0 or original_height == 0:
                    raise ScreenshotError(
                        f"Получен скриншот нулевого размера для {url}"
                    )

                aspect_ratio = original_height / original_width
                new_height = int(self.width * aspect_ratio)

                logger.info(
                    f"Изменение размера до {self.width}x{new_height} для {url}"
                )
                img_resized = img.resize(
                    (self.width, new_height), Image.Resampling.LANCZOS
                )

                # Сохраняем в байтовый буфер
                img_byte_arr = io.BytesIO()
                # Добавим качество JPEG
                img_resized.save(img_byte_arr, format='JPEG', quality=85)
                img_bytes = img_byte_arr.getvalue()

                logger.info(f"Успешно создано превью для {url}")
                return url, img_bytes

            except PlaywrightError as e:
                # Обрабатываем специфичные ошибки Playwright
                if "Timeout" in str(e):
                    logger.error(
                        f"Таймаут Playwright при обработке {url}: {e}"
                    )
                    return url, None
                elif "net::ERR" in str(e):
                    logger.error(
                        f"Ошибка сети Playwright при загрузке {url}: {e}"
                    )
                    return url, None
                else:
                    logger.error(
                        f"Ошибка Playwright при обработке {url}: {e}"
                    )
                    return url, None
            except VideoElementNotFoundError as e:
                logger.error(f"Ошибка поиска видео: {e}")
                return url, None
            except ScreenshotError as e:
                logger.error(f"Ошибка скриншота: {e}")
                return url, None
            except Exception as e:
                logger.error(
                    f"Непредвиденная ошибка при обработке {url}: {e}"
                )
                return url, None
            finally:
                if page:
                    await page.close()
                    logger.debug(f"Страница для {url} закрыта")
                if context:
                    await context.close()
                    logger.debug(f"Контекст для {url} закрыт")

    async def process_url_list(
        self, urls: List[str]
    ) -> List[Tuple[str, Optional[bytes]]]:
        """
        Асинхронно обрабатывает список URL и возвращает список пар
        (url, image_bytes).
        """
        if not urls:
            return []

        # Убедимся, что браузер запущен перед созданием задач
        await self._initialize()

        logger.info(f"Начало обработки {len(urls)} URL с помощью Playwright")

        tasks = [self._process_single_url(url) for url in urls]
        # Не прерываемся на ошибках отдельных URL
        results = await asyncio.gather(*tasks, return_exceptions=False)

        logger.info(f"Завершена обработка {len(urls)} URL")
        # Фильтруем None результаты (ошибки)
        processed_results = [
            (url, data) for url, data in results if isinstance(url, str)
        ]

        return processed_results

    async def process_url_list_to_files(
        self,
        urls: List[str],
        output_dir: str
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Асинхронно обрабатывает список URL и сохраняет изображения в файлы.
        """
        os.makedirs(output_dir, exist_ok=True)

        url_image_pairs = await self.process_url_list(urls)

        result_paths = []
        for url, img_bytes in url_image_pairs:
            output_path = None  # Инициализируем None
            if img_bytes:
                filename = self._generate_output_filename(url)
                output_path_candidate = os.path.join(output_dir, filename)
                try:
                    with open(output_path_candidate, 'wb') as f:
                        f.write(img_bytes)
                    logger.info(
                        "Сохранено изображение для %s в %s",
                        url, output_path_candidate
                    )
                    output_path = output_path_candidate  # Успешно сохранено
                except Exception as e:
                    logger.error(
                        f"Ошибка при сохранении изображения для {url} "
                        f"в {output_path_candidate}: {e}"
                    )
                    # output_path остается None
            # Добавляем результат в любом случае (успех или ошибка)
            result_paths.append((url, output_path))

        return result_paths

    async def close(self):
        """Закрывает браузер и Playwright."""
        if self._browser:
            try:
                await self._browser.close()
                logger.info(f"Браузер {self.browser_type_name} закрыт.")
            except Exception as e:
                logger.error(f"Ошибка при закрытии браузера: {e}")
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
                logger.info("Playwright остановлен.")
            except Exception as e:
                logger.error(f"Ошибка при остановке Playwright: {e}")
            self._playwright = None
        logger.info("Генератор превью (Playwright) закрыт")


# Пример использования убран, будет в main_service.py

if __name__ == "__main__":
    # Этот блок теперь пуст или содержит только базовую информацию
    print(
        "Этот модуль предназначен для импорта. "
        "Запустите main_service.py для тестирования."
    )
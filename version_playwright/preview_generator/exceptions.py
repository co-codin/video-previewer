"""Исключения генератора превью."""


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

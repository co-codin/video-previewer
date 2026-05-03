"""Числовые константы генератора превью."""

# Размер вьюпорта для контекста браузера
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)

# Таймауты для проверок meta-тегов postera (мс)
POSTER_PROBE_TIMEOUT_MS = 500

# Скачивание постера через HTTP
DOWNLOAD_TIMEOUT_SEC = 5
POSTER_MAX_BYTES = 10 * 1024 * 1024
MIN_IMAGE_BYTES = 100

# Скриншот видео-элемента
MIN_SCREENSHOT_BYTES = 100

# Ожидание seek
SEEK_TIMEOUT_MS = 5000
POST_SEEK_PAUSE_MS = 200
SEEK_FALLBACK_PAUSE_MS = 500

# Параметры сохраняемого JPEG
JPEG_QUALITY = 85

# Постфикс выходного файла
OUTPUT_FILE_SUFFIX = "_poster_pw.jpg"
DEFAULT_OUTPUT_BASENAME = "preview"

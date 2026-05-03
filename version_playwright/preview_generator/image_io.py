"""Конвертация PNG-скриншота в JPEG нужной ширины."""
import io
import logging

from PIL import Image

from preview_generator.constants import JPEG_QUALITY, MIN_SCREENSHOT_BYTES
from preview_generator.exceptions import ScreenshotError

logger = logging.getLogger(__name__)


def validate_screenshot(png_data: bytes, url: str) -> None:
    """Бросает ScreenshotError, если PNG отсутствует или слишком мал."""
    if not png_data or len(png_data) < MIN_SCREENSHOT_BYTES:
        size = len(png_data) if png_data else 0
        raise ScreenshotError(
            f"Получен пустой или слишком маленький скриншот ({size} байт) для {url}"
        )


def resize_to_jpeg(png_data: bytes, target_width: int, url: str) -> bytes:
    """Ресайзит PNG к нужной ширине с сохранением пропорций и сериализует в JPEG."""
    img = Image.open(io.BytesIO(png_data))
    original_width, original_height = img.size
    if original_width == 0 or original_height == 0:
        raise ScreenshotError(f"Получен скриншот нулевого размера для {url}")

    aspect_ratio = original_height / original_width
    new_height = int(target_width * aspect_ratio)

    logger.info("Изменение размера до %sx%s для %s", target_width, new_height, url)
    resized = img.resize((target_width, new_height), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    resized.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()

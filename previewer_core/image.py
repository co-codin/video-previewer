"""Конвертация изображений в JPEG с ресайзом."""
import io

from PIL import Image

from previewer_core.config import JPEG_QUALITY, WIDTH


def to_jpeg(raw: bytes, width: int = WIDTH, quality: int = JPEG_QUALITY) -> bytes:
    """Преобразует произвольное изображение в JPEG нужной ширины.

    Прозрачные форматы (RGBA/LA/P) сводятся на белый фон.
    Если исходник уже не шире target — оставляем без ресайза.
    """
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, "white")
        mask = img.split()[-1] if "A" in img.mode else None
        bg.paste(img, mask=mask)
        img = bg
    else:
        img = img.convert("RGB")

    if img.width > width:
        new_height = int(img.height * width / img.width)
        img = img.resize((width, new_height), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()

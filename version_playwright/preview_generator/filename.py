"""Генерация имени выходного файла из URL видео."""
import os
from urllib.parse import parse_qs, urlparse

from preview_generator.constants import DEFAULT_OUTPUT_BASENAME, OUTPUT_FILE_SUFFIX


def generate_output_filename(url: str) -> str:
    """Имя выходного файла на основе URL. Для YouTube использует video ID."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    base = None

    is_youtube = "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc
    if is_youtube:
        video_id = query.get("v", [None])[0]
        if video_id:
            base = video_id
        elif parsed.path and len(parsed.path) > 1 and "youtu.be" in parsed.netloc:
            base = parsed.path.lstrip("/")

    if not base:
        base = os.path.splitext(os.path.basename(parsed.path))[0]
        if not base or base == "/":
            base = parsed.netloc.replace(".", "_").replace(":", "_")

    safe_chars = ("_", "-")
    safe_base = "".join(
        c for c in base if c.isalnum() or c in safe_chars
    ).rstrip()
    if not safe_base:
        safe_base = DEFAULT_OUTPUT_BASENAME

    return f"{safe_base}{OUTPUT_FILE_SUFFIX}"

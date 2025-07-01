# client_preview.py
import asyncio
import  base64
import json
import os
import ssl
from pathlib import Path
from typing import Dict, List, Optional
import certifi
import httpx

PLAYER_PREFIX = "https://runtime.video.cloud.yandex.net/player/video/"

# ---------- заготовка под Object Storage -------------------------------------

def _upload_to_object_storage(key: str, data: bytes) -> str:
    """
    Пока заглушка.
    Верните URL внутри бакета, например:
    s3://my-bucket/previews/<key>.jpg   или
    https://storage.yandexcloud.net/my-bucket/previews/<key>.jpg
    """
    # TODO: реализовать через boto3 / yandexcloud SDK
    raise NotImplementedError


# ---------- основная асинхронная функция -------------------------------------
async def get_previews(
    items: List[str],
    *,
    endpoint: str = "http://localhost:8080/preview",
    out_dir: Path = Path("previews"),
    upload: bool = False,                   # True → кладём в Object Storage
) -> Dict[str, Optional[Path]]:
    """
    Возвращает mapping canonical_url -> Path к JPEG (или None, если не получили)
    """
    if not items:
        return {}

    out_dir.mkdir(exist_ok=True)

    # 1. канонизируем ID → URL
    urls = [
        x if x.startswith("http")
        else f"{PLAYER_PREFIX}{x}"
        for x in items
    ]

    # 2. делаем POST к сервису
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    async with httpx.AsyncClient(verify=ssl_ctx, timeout=30) as client:
        r = await client.post(endpoint, json={"items": urls})
        r.raise_for_status()
        data: Dict[str, Optional[str]] = r.json()

    # 3. записываем файлы (или грузим в объектное хранилище)
    result: Dict[str, Optional[Path]] = {}
    for url, b64 in data.items():
        if not b64:
            result[url] = None
            continue

        jpeg_bytes = base64.b64decode(b64)

        if upload:
            # ключ в бакете = <id>.jpg
            key = f"previews/{Path(url).stem}.jpg"
            object_url = _upload_to_object_storage(key, jpeg_bytes)
            result[url] = Path(object_url)           # типовая заглушка
        else:
            path = out_dir / f"{Path(url).stem}.jpg"
            path.write_bytes(jpeg_bytes)
            result[url] = path

    return result


# ---------- удобный синхронный враппер --------------------------------------
def get_previews_sync(
    items: List[str],
    **kwargs,
) -> Dict[str, Optional[Path]]:
    return asyncio.run(get_previews(items, **kwargs))


# ---------- пример использования --------------------------------------------
if __name__ == "__main__":
    previews = get_previews_sync(
        ["vplvlm2tgrhg5e7iijtg", "vplvs2hcyadjk5noqxcn"],
        # endpoint="http://localhost:8080/preview",
        endpoint="https://yv-preview.fly.dev/preview",
        out_dir=Path("previews"),               # куда писать локально
        upload=False                       # True → сразу в YC Object Storage
    )

    for url, location in previews.items():
        print(f"{url:<80} -> {location}")
    
"""Клиент для сервиса генерации превью видео.

Поддерживает асинхронный и синхронный API. Дефолтный URL берётся из
переменной окружения ``PREVIEW_API_URL``, иначе — ``http://localhost:8080``.
"""
import asyncio
import base64
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from httpx import HTTPError, TimeoutException

logger = logging.getLogger(__name__)


DEFAULT_BASE_URL: str = os.environ.get("PREVIEW_API_URL", "http://localhost:8080")


class VideoPreviewClient:
    """HTTP-клиент сервиса /preview."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "VideoPreviewClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        client = await self._ensure_client()
        try:
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except HTTPError:
            logger.exception("Health check failed")
            raise

    async def generate_preview(
        self,
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        save_path: Optional[Union[str, Path]] = None,
    ) -> Tuple[str, Optional[bytes]]:
        result = await self.generate_previews(
            [url],
            width=width,
            height=height,
            save_dir=Path(save_path).parent if save_path else None,
        )
        return url, result.get(url)

    async def generate_previews(
        self,
        urls: List[str],
        width: Optional[int] = None,
        height: Optional[int] = None,
        save_dir: Optional[Union[str, Path]] = None,
        max_workers: Optional[int] = None,
    ) -> Dict[str, Optional[bytes]]:
        if not urls:
            return {}

        client = await self._ensure_client()
        params = {"items": urls}

        response = None
        for attempt in range(self.max_retries):
            try:
                response = await client.post("/preview", json=params)
                response.raise_for_status()
                break
            except (HTTPError, TimeoutException):
                if attempt == self.max_retries - 1:
                    logger.exception(
                        "Failed to generate previews after %s attempts", self.max_retries,
                    )
                    raise
                logger.warning("Attempt %s failed, retrying...", attempt + 1)
                await asyncio.sleep(2 ** attempt)

        results = response.json()
        decoded: Dict[str, Optional[bytes]] = {}
        for u, preview_b64 in results.items():
            if not preview_b64:
                decoded[u] = None
                continue
            try:
                preview_bytes = base64.b64decode(preview_b64)
                decoded[u] = preview_bytes
                if save_dir:
                    self._save_preview(preview_bytes, u, save_dir)
            except Exception:
                logger.exception("Failed to process preview for %s", u)
                decoded[u] = None

        return decoded

    @staticmethod
    def _save_preview(preview_bytes: bytes, url: str, save_dir: Union[str, Path]) -> None:
        save_dir_path = Path(save_dir)
        save_dir_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = url.split("/")[-1].split("?")[0] or f"preview_{hash(url)}"
        file_path = save_dir_path / f"{safe_name}_{timestamp}.jpg"
        file_path.write_bytes(preview_bytes)
        logger.info("Saved preview to %s", file_path)

    async def get_info(self) -> Dict[str, Any]:
        client = await self._ensure_client()
        response = await client.get("/")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # --- Синхронные обёртки ---

    def health_check_sync(self) -> Dict[str, Any]:
        return asyncio.run(self.health_check())

    def generate_preview_sync(
        self,
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        save_path: Optional[Union[str, Path]] = None,
    ) -> Tuple[str, Optional[bytes]]:
        return asyncio.run(self.generate_preview(url, width, height, save_path))

    def generate_previews_sync(
        self,
        urls: List[str],
        width: Optional[int] = None,
        height: Optional[int] = None,
        save_dir: Optional[Union[str, Path]] = None,
        max_workers: Optional[int] = None,
    ) -> Dict[str, Optional[bytes]]:
        return asyncio.run(
            self.generate_previews(urls, width, height, save_dir, max_workers)
        )

    def get_info_sync(self) -> Dict[str, Any]:
        return asyncio.run(self.get_info())


async def quick_preview(
    url: str,
    save_path: Optional[str] = None,
    api_url: str = DEFAULT_BASE_URL,
) -> Optional[bytes]:
    """Быстрая генерация превью для одного URL."""
    async with VideoPreviewClient(api_url) as client:
        _, preview_data = await client.generate_preview(url, save_path=save_path)
        return preview_data


def quick_preview_sync(
    url: str,
    save_path: Optional[str] = None,
    api_url: str = DEFAULT_BASE_URL,
) -> Optional[bytes]:
    return asyncio.run(quick_preview(url, save_path, api_url))

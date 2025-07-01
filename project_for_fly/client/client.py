import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime

import httpx
from httpx import HTTPError, TimeoutException

logger = logging.getLogger(__name__)


class VideoPreviewClient:
    """
    Клиент для работы с сервисом генерации превью видео.
    
    Поддерживает:
    - Генерацию превью по одному или нескольким URL
    - Получение статуса сервиса
    - Сохранение превью в файлы
    - Асинхронные и синхронные методы
    """
    
    def __init__(
        self,
        base_url: str = "https://yv-preview.fly.dev",
        timeout: float = 120.0,
        max_retries: int = 3
    ):
        """
        Инициализация клиента.
        
        Args:
            base_url: Базовый URL API сервиса
            timeout: Таймаут для HTTP запросов в секундах
            max_retries: Максимальное количество попыток при ошибках
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Вход в контекстный менеджер."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        """Убедиться, что клиент инициализирован."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client
    
    async def health_check(self) -> Dict[str, any]:
        """
        Проверка состояния сервиса.
        
        Returns:
            Dict с информацией о состоянии сервиса
        """
        client = await self._ensure_client()
        try:
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            logger.error(f"Health check failed: {e}")
            raise
    
    async def generate_preview(
        self,
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        save_path: Optional[Union[str, Path]] = None
    ) -> Tuple[str, Optional[bytes]]:
        """
        Генерация превью для одного URL.
        
        Args:
            url: URL видео
            width: Ширина превью (опционально)
            height: Высота превью (опционально)
            save_path: Путь для сохранения файла (опционально)
            
        Returns:
            Tuple (url, preview_bytes или None при ошибке)
        """
        result = await self.generate_previews(
            [url], 
            width=width, 
            height=height,
            save_dir=Path(save_path).parent if save_path else None
        )
        
        preview_data = result.get(url)
        return url, preview_data
    
    async def generate_previews(
        self,
        urls: List[str],
        width: Optional[int] = None,
        height: Optional[int] = None,
        save_dir: Optional[Union[str, Path]] = None,
        max_workers: Optional[int] = None
    ) -> Dict[str, Optional[bytes]]:
        """
        Генерация превью для списка URL.
        
        Args:
            urls: Список URL видео
            width: Ширина превью (опционально)
            height: Высота превью (опционально)
            save_dir: Директория для сохранения файлов (опционально)
            max_workers: Максимальное количество параллельных обработчиков
            
        Returns:
            Dict {url: preview_bytes или None при ошибке}
        """
        if not urls:
            return {}
        
        client = await self._ensure_client()
        
        # Подготовка параметров запроса для API как в Fly.io
        params = {"items": urls}
        
        # Выполнение запроса с повторными попытками
        for attempt in range(self.max_retries):
            try:
                response = await client.post("/preview", json=params)
                response.raise_for_status()
                break
            except (HTTPError, TimeoutException) as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to generate previews after {self.max_retries} attempts: {e}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
        
        # Обработка результата - API возвращает словарь напрямую
        results = response.json()
        
        # Декодирование base64 и сохранение файлов
        decoded_results = {}
        for url, preview_b64 in results.items():
            if preview_b64:
                try:
                    preview_bytes = base64.b64decode(preview_b64)
                    decoded_results[url] = preview_bytes
                    
                    # Сохранение в файл, если указана директория
                    if save_dir:
                        save_dir = Path(save_dir)
                        save_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Генерация имени файла
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_name = url.split("/")[-1].split("?")[0]
                        if not safe_name:
                            safe_name = f"preview_{hash(url)}"
                        filename = f"{safe_name}_{timestamp}.jpg"
                        
                        file_path = save_dir / filename
                        file_path.write_bytes(preview_bytes)
                        logger.info(f"Saved preview to {file_path}")
                except Exception as e:
                    logger.error(f"Failed to process preview for {url}: {e}")
                    decoded_results[url] = None
            else:
                decoded_results[url] = None
        
        return decoded_results
    
    async def get_info(self) -> Dict[str, any]:
        """
        Получение информации о сервисе.
        
        Returns:
            Dict с информацией о сервисе и его возможностях
        """
        client = await self._ensure_client()
        response = await client.get("/")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Закрытие HTTP клиента."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # Синхронные методы для удобства
    
    def health_check_sync(self) -> Dict[str, any]:
        """Синхронная версия health_check."""
        return asyncio.run(self.health_check())
    
    def generate_preview_sync(
        self,
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        save_path: Optional[Union[str, Path]] = None
    ) -> Tuple[str, Optional[bytes]]:
        """Синхронная версия generate_preview."""
        return asyncio.run(self.generate_preview(url, width, height, save_path))
    
    def generate_previews_sync(
        self,
        urls: List[str],
        width: Optional[int] = None,
        height: Optional[int] = None,
        save_dir: Optional[Union[str, Path]] = None,
        max_workers: Optional[int] = None
    ) -> Dict[str, Optional[bytes]]:
        """Синхронная версия generate_previews."""
        return asyncio.run(self.generate_previews(urls, width, height, save_dir, max_workers))
    
    def get_info_sync(self) -> Dict[str, any]:
        """Синхронная версия get_info."""
        return asyncio.run(self.get_info())


# Удобная функция для быстрого создания превью
async def quick_preview(
    url: str,
    save_path: Optional[str] = None,
    api_url: str = "https://yv-preview.fly.dev"
) -> Optional[bytes]:
    """
    Быстрая генерация превью для одного URL.
    
    Args:
        url: URL видео
        save_path: Путь для сохранения (опционально)
        api_url: URL API сервиса
        
    Returns:
        bytes превью или None при ошибке
    """
    async with VideoPreviewClient(api_url) as client:
        _, preview_data = await client.generate_preview(url, save_path=save_path)
        return preview_data


def quick_preview_sync(
    url: str,
    save_path: Optional[str] = None,
    api_url: str = "https://yv-preview.fly.dev"
) -> Optional[bytes]:
    """Синхронная версия quick_preview."""
    return asyncio.run(quick_preview(url, save_path, api_url))
#!/usr/bin/env python3
"""
Примеры использования VideoPreviewClient для работы с сервисом генерации превью.
"""

import asyncio
import logging
from pathlib import Path
from client import VideoPreviewClient, quick_preview_sync

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_quick_preview():
    """Пример 1: Быстрая генерация превью для одного URL."""
    print("\n=== Пример 1: Быстрая генерация превью ===")
    
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # Генерация превью с сохранением в файл
    preview_data = quick_preview_sync(
        url=url,
        save_path="preview_example1.jpg",
        api_url="http://localhost:8000"
    )
    
    if preview_data:
        print(f"✓ Превью успешно создано: {len(preview_data)} байт")
    else:
        print("✗ Не удалось создать превью")


def example_2_sync_client():
    """Пример 2: Использование синхронных методов клиента."""
    print("\n=== Пример 2: Синхронный клиент ===")
    
    client = VideoPreviewClient(base_url="http://localhost:8000")
    
    # Проверка здоровья сервиса
    try:
        health = client.health_check_sync()
        print(f"Статус сервиса: {health}")
    except Exception as e:
        print(f"Ошибка проверки здоровья: {e}")
        return
    
    # Получение информации о сервисе
    info = client.get_info_sync()
    print(f"Информация о сервисе: {info}")
    
    # Генерация превью с кастомными размерами
    url = "https://vimeo.com/148751763"
    _, preview_data = client.generate_preview_sync(
        url=url,
        width=1280,
        height=720,
        save_path="preview_example2_hd.jpg"
    )
    
    if preview_data:
        print(f"✓ HD превью создано: {len(preview_data)} байт")


def example_3_batch_processing():
    """Пример 3: Пакетная обработка нескольких URL."""
    print("\n=== Пример 3: Пакетная обработка ===")
    
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://vimeo.com/148751763",
        "https://www.dailymotion.com/video/x5w5x5c",
        "https://invalid-url-test.com/video.mp4"
    ]
    
    client = VideoPreviewClient(
        base_url="http://localhost:8000",
        timeout=180.0  # Увеличенный таймаут для пакетной обработки
    )
    
    # Генерация превью для всех URL
    results = client.generate_previews_sync(
        urls=urls,
        width=640,
        height=360,
        save_dir="batch_previews",
        max_workers=3
    )
    
    # Вывод результатов
    for url, preview_data in results.items():
        if preview_data:
            print(f"✓ {url}: {len(preview_data)} байт")
        else:
            print(f"✗ {url}: не удалось создать превью")


async def example_4_async_context_manager():
    """Пример 4: Асинхронное использование с контекстным менеджером."""
    print("\n=== Пример 4: Асинхронный контекстный менеджер ===")
    
    urls = [
        "https://www.youtube.com/watch?v=9bZkp7q19f0",
        "https://player.vimeo.com/video/76979871"
    ]
    
    async with VideoPreviewClient("http://localhost:8000") as client:
        # Проверка здоровья
        health = await client.health_check()
        print(f"Асинхронная проверка здоровья: {health}")
        
        # Генерация превью
        results = await client.generate_previews(
            urls=urls,
            save_dir="async_previews"
        )
        
        for url, preview_data in results.items():
            status = "✓" if preview_data else "✗"
            size = f"{len(preview_data)} байт" if preview_data else "ошибка"
            print(f"{status} {url}: {size}")


async def example_5_error_handling():
    """Пример 5: Обработка ошибок и повторные попытки."""
    print("\n=== Пример 5: Обработка ошибок ===")
    
    # Клиент с настройками для демонстрации обработки ошибок
    client = VideoPreviewClient(
        base_url="http://localhost:8000",
        timeout=10.0,  # Короткий таймаут
        max_retries=2   # Меньше попыток
    )
    
    problematic_urls = [
        "https://this-domain-does-not-exist-12345.com/video.mp4",
        "not-a-valid-url",
        "https://www.youtube.com/watch?v=invalid_id_12345"
    ]
    
    async with client:
        for url in problematic_urls:
            try:
                _, preview = await client.generate_preview(url)
                if preview:
                    print(f"✓ Неожиданный успех для {url}")
                else:
                    print(f"✗ Ожидаемая ошибка для {url}")
            except Exception as e:
                print(f"✗ Исключение для {url}: {type(e).__name__}: {e}")


async def example_6_custom_processing():
    """Пример 6: Кастомная обработка результатов."""
    print("\n=== Пример 6: Кастомная обработка ===")
    
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://vimeo.com/148751763"
    ]
    
    async with VideoPreviewClient("http://localhost:8000") as client:
        results = await client.generate_previews(urls)
        
        # Кастомная обработка: создание HTML галереи
        html_content = ["<html><body><h1>Галерея превью</h1>"]
        
        for url, preview_data in results.items():
            if preview_data:
                # Сохранение превью
                filename = f"gallery_{hash(url)}.jpg"
                Path(filename).write_bytes(preview_data)
                
                # Добавление в HTML
                html_content.append(
                    f'<div>'
                    f'<h3><a href="{url}">{url}</a></h3>'
                    f'<img src="{filename}" width="320">'
                    f'</div>'
                )
            else:
                html_content.append(
                    f'<div>'
                    f'<h3>{url}</h3>'
                    f'<p>Превью недоступно</p>'
                    f'</div>'
                )
        
        html_content.append("</body></html>")
        
        # Сохранение HTML
        Path("preview_gallery.html").write_text("\n".join(html_content))
        print("✓ HTML галерея создана: preview_gallery.html")


def example_7_parallel_clients():
    """Пример 7: Параллельная работа с несколькими серверами."""
    print("\n=== Пример 7: Работа с несколькими серверами ===")
    
    async def process_on_server(server_url: str, video_urls: list):
        """Обработка на конкретном сервере."""
        async with VideoPreviewClient(server_url) as client:
            try:
                results = await client.generate_previews(video_urls)
                success_count = sum(1 for v in results.values() if v)
                return server_url, success_count, len(video_urls)
            except Exception as e:
                return server_url, 0, len(video_urls)
    
    async def run_parallel():
        # Список серверов (для примера используем один и тот же)
        servers = [
            "http://localhost:8000",
            "http://localhost:8001",  # Предполагаемый второй инстанс
            "http://localhost:8002"   # Предполагаемый третий инстанс
        ]
        
        video_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://vimeo.com/148751763"
        ]
        
        # Запуск параллельной обработки
        tasks = [
            process_on_server(server, video_urls) 
            for server in servers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Вывод результатов
        for result in results:
            if isinstance(result, Exception):
                print(f"✗ Ошибка: {result}")
            else:
                server, success, total = result
                print(f"Сервер {server}: {success}/{total} успешно")
    
    # Запуск
    asyncio.run(run_parallel())


def main():
    """Запуск всех примеров."""
    print("🎬 Примеры использования VideoPreviewClient")
    print("=" * 50)
    
    # Создание директорий для сохранения
    Path("batch_previews").mkdir(exist_ok=True)
    Path("async_previews").mkdir(exist_ok=True)
    
    # Запуск примеров
    try:
        # Синхронные примеры
        example_1_quick_preview()
        example_2_sync_client()
        example_3_batch_processing()
        
        # Асинхронные примеры
        asyncio.run(example_4_async_context_manager())
        asyncio.run(example_5_error_handling())
        asyncio.run(example_6_custom_processing())
        
        # Параллельная работа
        example_7_parallel_clients()
        
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        print(f"\n\nОшибка: {e}")
    
    print("\n" + "=" * 50)
    print("✓ Все примеры выполнены")


if __name__ == "__main__":
    main()
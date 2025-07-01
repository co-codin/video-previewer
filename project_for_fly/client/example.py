#!/usr/bin/env python3
"""
Пример использования клиента для Fly.io версии сервиса.
"""

from client import VideoPreviewClient, quick_preview_sync

# Пример 1: Быстрое использование
print("Пример 1: Быстрая генерация превью")
preview = quick_preview_sync(
    "vplvlm2tgrhg5e7iijtg",  # ID видео Яндекс.Видео
    save_path="yandex_preview.jpg"
)
if preview:
    print(f"✓ Превью сохранено: {len(preview)} байт")

# Пример 2: Использование клиента
print("\nПример 2: Пакетная обработка")
client = VideoPreviewClient()  # Использует https://yv-preview.fly.dev по умолчанию

video_ids = [
    "vplvlm2tgrhg5e7iijtg",
    "vplvs2hcyadjk5noqxcn", 
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
]

results = client.generate_previews_sync(
    urls=video_ids,
    save_dir="fly_previews/"
)

for url, data in results.items():
    status = "✓" if data else "✗"
    print(f"{status} {url}")

# Пример 3: Использование с другим сервером
print("\nПример 3: Локальный сервер")
local_client = VideoPreviewClient("http://localhost:8080")
try:
    health = local_client.health_check_sync()
    print(f"Локальный сервер: {health}")
except Exception as e:
    print(f"Локальный сервер недоступен: {e}")
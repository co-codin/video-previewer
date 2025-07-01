# Python клиент для Fly.io версии сервиса

Этот клиент настроен для работы с развернутым на Fly.io сервисом генерации превью.

## Установка

```bash
pip install httpx
```

## Использование

```python
from client import VideoPreviewClient, quick_preview_sync

# Быстрый способ
preview = quick_preview_sync("vplvlm2tgrhg5e7iijtg")

# С клиентом
client = VideoPreviewClient()  # Использует https://yv-preview.fly.dev
results = client.generate_previews_sync(["video_id1", "video_id2"])
```

## Отличия от локального клиента

1. **URL по умолчанию**: `https://yv-preview.fly.dev` вместо `http://localhost:8080`
2. **HTTPS**: Безопасное соединение
3. **Производственная среда**: Оптимизирован для работы через интернет

## Примеры

Смотрите `example.py` для полных примеров использования.
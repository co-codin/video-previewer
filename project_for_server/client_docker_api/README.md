# Python клиент для сервиса генерации превью видео

Этот модуль содержит Python клиент для работы с API сервиса генерации превью.

## Установка

```bash
cd client_docker_api
pip install -r requirements.txt
```

## Быстрый старт

### Простейший пример

```python
from client import quick_preview_sync

# Генерация превью
preview_data = quick_preview_sync(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    save_path="preview.jpg",
    api_url="http://localhost:8000"
)
```

### Использование клиента

```python
from client import VideoPreviewClient

# Создание клиента
client = VideoPreviewClient(
    base_url="http://localhost:8000",
    timeout=120.0,
    max_retries=3
)

# Проверка сервиса
health = client.health_check_sync()
print(f"Статус: {health}")

# Генерация превью
url, preview_data = client.generate_preview_sync(
    url="https://vimeo.com/148751763",
    width=1280,
    height=720,
    save_path="hd_preview.jpg"
)
```

## Примеры использования

Запустите файл `using_client.py` для демонстрации всех возможностей:

```bash
python using_client.py
```

Включены примеры:
1. Быстрая генерация превью
2. Синхронный клиент с настройками
3. Пакетная обработка URL
4. Асинхронное использование
5. Обработка ошибок
6. Кастомная обработка результатов
7. Работа с несколькими серверами

## API Reference

### VideoPreviewClient

#### Инициализация

```python
client = VideoPreviewClient(
    base_url="http://localhost:8000",  # URL сервиса
    timeout=120.0,                      # Таймаут в секундах
    max_retries=3                       # Количество повторных попыток
)
```

#### Методы

##### health_check() / health_check_sync()
Проверка состояния сервиса.

```python
# Асинхронно
health = await client.health_check()

# Синхронно
health = client.health_check_sync()
```

##### generate_preview() / generate_preview_sync()
Генерация превью для одного URL.

```python
# Асинхронно
url, preview_bytes = await client.generate_preview(
    url="https://example.com/video.mp4",
    width=640,           # Опционально
    height=360,          # Опционально
    save_path="out.jpg"  # Опционально
)

# Синхронно
url, preview_bytes = client.generate_preview_sync(...)
```

##### generate_previews() / generate_previews_sync()
Пакетная генерация превью.

```python
# Асинхронно
results = await client.generate_previews(
    urls=["url1", "url2", "url3"],
    width=640,
    height=360,
    save_dir="previews/",    # Опционально
    max_workers=3            # Опционально
)

# Синхронно
results = client.generate_previews_sync(...)
```

Возвращает словарь `{url: preview_bytes или None}`.

##### get_info() / get_info_sync()
Получение информации о сервисе.

```python
info = await client.get_info()
```

### Контекстный менеджер

```python
# Асинхронный
async with VideoPreviewClient("http://localhost:8000") as client:
    results = await client.generate_previews(urls)

# Синхронный (требует ручного закрытия)
client = VideoPreviewClient("http://localhost:8000")
try:
    results = client.generate_previews_sync(urls)
finally:
    asyncio.run(client.close())
```

### Быстрые функции

```python
# Асинхронная
preview = await quick_preview(
    url="https://example.com/video.mp4",
    save_path="preview.jpg",
    api_url="http://localhost:8000"
)

# Синхронная
preview = quick_preview_sync(...)
```

## Обработка ошибок

```python
from httpx import HTTPError, TimeoutException

try:
    url, preview = client.generate_preview_sync(video_url)
    if preview:
        print("Успешно")
    else:
        print("Не удалось создать превью")
except TimeoutException:
    print("Превышен таймаут")
except HTTPError as e:
    print(f"HTTP ошибка: {e}")
except Exception as e:
    print(f"Неожиданная ошибка: {e}")
```

## Настройка логирования

```python
import logging

# Включить debug логи
logging.basicConfig(level=logging.DEBUG)

# Только для клиента
logger = logging.getLogger('client')
logger.setLevel(logging.INFO)
```

## Производительность

### Рекомендации

1. **Используйте пакетную обработку** для множества URL
2. **Настройте max_workers** в зависимости от мощности сервера
3. **Увеличьте timeout** для медленных видео
4. **Используйте асинхронные методы** для параллельной обработки

### Пример оптимизированной обработки

```python
import asyncio
from client import VideoPreviewClient

async def process_large_batch(urls: list, batch_size: int = 10):
    """Обработка большого количества URL батчами."""
    async with VideoPreviewClient("http://localhost:8000") as client:
        results = {}
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            batch_results = await client.generate_previews(
                urls=batch,
                max_workers=5
            )
            results.update(batch_results)
            
            # Небольшая пауза между батчами
            if i + batch_size < len(urls):
                await asyncio.sleep(1)
        
        return results

# Использование
urls = ["url1", "url2", ..., "url100"]
results = asyncio.run(process_large_batch(urls))
```

## Интеграция

### Flask пример

```python
from flask import Flask, jsonify, request
from client import VideoPreviewClient

app = Flask(__name__)
client = VideoPreviewClient("http://preview-service:8000")

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    try:
        _, preview = client.generate_preview_sync(url)
        if preview:
            return jsonify({
                'success': True,
                'preview': base64.b64encode(preview).decode()
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

### FastAPI пример

```python
from fastapi import FastAPI, HTTPException
from client import VideoPreviewClient

app = FastAPI()
client = VideoPreviewClient("http://preview-service:8000")

@app.post("/generate")
async def generate(url: str):
    try:
        _, preview = await client.generate_preview(url)
        if preview:
            return {
                "success": True,
                "size": len(preview),
                "preview": base64.b64encode(preview).decode()
            }
        else:
            raise HTTPException(400, "Failed to generate preview")
    except Exception as e:
        raise HTTPException(500, str(e))
```
# Video Preview Service

Сервис для генерации превью-изображений (постеров) из видео по URL. Поддерживает различные видеохостинги и предоставляет несколько вариантов развертывания.

## 🚀 Возможности

- **Генерация превью из видео** по URL
- **Извлечение готовых постеров** (og:image, video poster)
- **Поддержка популярных платформ**: YouTube, Vimeo, Dailymotion, Яндекс.Видео
- **Современная технология**: использует Playwright для быстрой работы
- **REST API** для интеграции
- **Асинхронная обработка** для высокой производительности

## 📋 Содержание

- [Быстрый старт](#быстрый-старт)
- [Варианты развертывания](#варианты-развертывания)
- [Архитектура проекта](#архитектура-проекта)
- [API документация](#api-документация)
- [Разработка](#разработка)

## 🏃 Быстрый старт

### Локальный запуск

```bash
# Клонирование репозитория
git clone <repository-url>
cd service_video_preview

# Установка зависимостей
pip install -r requirements.txt

# Установка Playwright браузера
playwright install chromium

# Запуск тестового скрипта
python version_playwright/main_service.py
```

### Использование API

```bash
# Генерация превью
curl -X POST http://localhost:8080/preview \
  -H "Content-Type: application/json" \
  -d '{
    "items": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
  }'
```

## 🚢 Варианты развертывания

### 1. Fly.io (Облачное развертывание)

Оптимизированное решение для Яндекс.Видео с минимальными зависимостями.

```bash
cd project_for_fly/project
fly deploy
```

[Подробнее о развертывании на Fly.io →](project_for_fly/README.md)

**Особенности:**
- Минимальный размер образа
- Быстрое извлечение постеров
- Автоматическое масштабирование
- Endpoint: `/preview`

### 2. VPS/Dedicated Server (Docker)

Полнофункциональное решение для собственного сервера.

```bash
cd project_for_server/docker_api
docker-compose up -d
```

[Подробнее о развертывании на VPS →](project_for_server/docker_api/README.md)

**Особенности:**
- Полный контроль над ресурсами
- Поддержка всех функций
- Настраиваемые лимиты
- Health checks и мониторинг

## 🏗️ Архитектура проекта

```
service_video_preview/
├── version_playwright/          # Основная реализация с Playwright
│   ├── preview_generate_service.py
│   └── main_service.py
├── project_for_fly/            # Развертывание на Fly.io
│   └── project/
│       ├── app.py              # FastAPI сервер
│       ├── fly.toml            # Конфигурация Fly.io
│       └── Dockerfile
├── project_for_server/         # Развертывание на VPS
│   ├── docker_api/             # Docker конфигурация
│   │   ├── app.py              # FastAPI сервер (тот же)
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   └── deploy.sh
│   └── client_docker_api/      # Python клиент
│       ├── client.py
│       └── using_client.py
└── drafts/                     # Черновики (исключено из git)
```

## 📡 API документация

### Endpoint: `POST /preview`

Генерация превью для списка URL видео.

**Запрос:**
```json
{
  "items": ["video_id_or_url", "..."]
}
```

**Ответ:**
```json
{
  "url1": "base64_encoded_image",
  "url2": null
}
```

**Пример:**
```bash
curl -X POST http://localhost:8080/preview \
  -H "Content-Type: application/json" \
  -d '{
    "items": ["dQw4w9WgXcQ", "https://vimeo.com/148751763"]
  }'
```

Для Яндекс.Видео можно передавать как ID видео, так и полные URL. ID автоматически преобразуются в URL формата:
`https://runtime.video.cloud.yandex.net/player/video/{id}`

## 💻 Разработка

### Архитектура

Проект использует **Playwright** для генерации превью:
- Высокая скорость работы
- Асинхронная архитектура
- Низкое потребление памяти
- Поддержка современных веб-технологий

Основные модули:
- `version_playwright/` - основная реализация с Playwright
- `project_for_fly/project/app.py` - FastAPI сервер для production
- `project_for_server/docker_api/app.py` - тот же сервер для VPS

### Запуск тестов

```bash
# Тестовый скрипт
python version_playwright/main_service.py
```

### Добавление новых платформ

1. Добавьте обработчик в `PreviewGenerator.extract_poster_url()`
2. При необходимости добавьте специальную логику в `PreviewGenerator.take_screenshot()`
3. Протестируйте с различными URL платформы

## 🐳 Docker

### Сборка образа

```bash
docker build -t video-preview-service .
```

### Запуск контейнера

```bash
docker run -p 8000:8000 video-preview-service
```

## 📚 Клиентские библиотеки

### Python клиент

```python
from client import VideoPreviewClient

async with VideoPreviewClient("http://localhost:8080") as client:
    results = await client.generate_previews(
        urls=["https://youtube.com/watch?v=..."]
    )
```

[Документация Python клиента →](project_for_server/client_docker_api/README.md)

## 🔧 Конфигурация

### Переменные окружения

- `MAX_WORKERS` - Количество параллельных обработчиков (по умолчанию: 5)
- `PREVIEW_WIDTH` - Ширина превью по умолчанию (640)
- `PREVIEW_HEIGHT` - Высота превью по умолчанию (360)
- `SCREENSHOT_TIMEOUT` - Таймаут для скриншота в секундах (30)
- `LOG_LEVEL` - Уровень логирования (INFO)

## 📋 Требования

- Python 3.8+
- Chrome/Chromium браузер
- Для Playwright: `playwright install chromium`
- Для Docker: Docker Engine 20.10+

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для фичи (`git checkout -b feature/amazing-feature`)
3. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
4. Запушьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

MIT License - см. файл LICENSE для деталей.
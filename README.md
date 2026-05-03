# video-previewer

HTTP-сервис для генерации JPEG-превью из видео по URL. Сначала пытается извлечь
постер из HTML страницы (og:image, twitter:image, vjs-poster, inline-JSON), и
только если не получилось — открывает страницу в Chromium и делает скриншот.

## Структура репозитория

```
previewer_core/                   # Общая библиотека (FastAPI-app + парсеры + браузер)
project_for_fly/
  ├── project/                    # Деплой во Fly.io (тонкая обёртка над previewer_core)
  └── client/                     # Python-клиент
project_for_server/
  ├── docker_api/                 # Docker-деплой (тонкая обёртка над previewer_core)
  └── client_docker_api/          # Python-клиент
version_playwright/               # Альтернативная реализация: только-браузер
                                  # с seek+screenshot (используется как библиотека)
docs/                             # План оптимизации и заметки
```

## API

### `POST /preview`

Принимает массив URL видео или коротких ID:

```json
{ "items": ["vplvlm2tgrhg5e7iijtg", "https://runtime.video.cloud.yandex.net/player/video/..."] }
```

Возвращает мапу URL → base64-JPEG (либо `null`, если превью не удалось):

```json
{ "https://...": "<base64>", "https://...": null }
```

### `GET /health`

Простой liveness-чек: `{ "status": "ok" }`. Используется в healthcheck контейнера.

## Запуск (Fly.io)

```bash
cd project_for_fly/project
fly deploy
```

## Запуск (Docker)

```bash
cd project_for_server/docker_api
cp .env.example .env
docker compose up -d --build
curl http://localhost:8080/health
```

## Запуск локально

```bash
pip install -r requirements.txt
python -m playwright install --with-deps chromium
uvicorn previewer_core:create_app --factory --host 0.0.0.0 --port 8080
```

## Конфигурация

Все настройки переопределяются через переменные окружения. См.
`previewer_core/config.py` и `project_for_server/docker_api/.env.example`.

## Альтернативная реализация (`version_playwright/`)

Полностью браузерная реализация с seek-к-1-й секунде и скриншотом видео-элемента.
Используется как Python-библиотека:

```python
from preview_generator import PreviewGenerator

gen = PreviewGenerator(width=720, max_workers=3, timeout=20)
results = await gen.process_url_list_to_files(urls, output_dir="previews_pw")
await gen.close()
```

Запуск примера: `cd version_playwright && python main_service.py`.

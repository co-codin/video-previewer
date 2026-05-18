# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## О проекте

Сервис генерации превью-изображений из видео по URL. Полностью на Playwright (Chromium), асинхронный. Доставляется в двух формах: HTTP API (FastAPI) и батч-CLI для офлайн-обработки списков URL.

## Архитектура

### Пакеты

- **`previewer_core/`** — ядро HTTP-сервиса.
  - `service.py` — FastAPI-приложение, эндпоинты `/health` и `/preview`, фабрика `create_app()`.
  - `browser.py` — жизненный цикл Playwright и захват кадра/canvas.
  - `poster.py` — извлечение `og:image` и `video.poster` из HTML.
  - `image.py`, `http_client.py`, `config.py` — утилиты.

- **`previewer_client/`** — клиентская библиотека для обращения к API.
  - `client.py` — `VideoPreviewClient` (async + sync враппер).

- **`version_playwright/`** — самостоятельный батч-генератор (НЕ интегрирован с `previewer_core`).
  - `main_service.py` — точка входа для тестов.
  - `preview_generator/` — модули `generator.py`, `video_capture.py`, `poster_extractor.py`, `consent.py` (YouTube cookie), `image_io.py`, `filename.py`, `constants.py`, `exceptions.py`.

### Деплой-таргеты

- **`project_for_fly/`** — Fly.io. `project/app.py` импортирует `previewer_core.create_app()`; `client/` — тонкий враппер над `previewer_client` с дефолтным URL Fly.
- **`project_for_server/`** — Docker Compose / удалённый сервер. `docker_api/app.py` идентичен Fly-варианту; `client_docker_api/` — клиент-обёртка с локальным URL по умолчанию.

⚠️ `project_for_fly/client` и `project_for_server/client_docker_api` сейчас почти дубликаты `previewer_client` — кандидат на консолидацию.

## Основные команды

### Запуск HTTP-сервиса

```bash
# Локально (uvicorn)
uvicorn previewer_core.service:create_app --factory --host 0.0.0.0 --port 8080
```

### Запуск батч-CLI

```bash
python version_playwright/main_service.py
```

### Docker (project_for_server)

```bash
cd project_for_server/docker_api
docker-compose up -d --build
docker-compose logs -f
```

Healthcheck контейнера: `GET /health`.

### Установка зависимостей

```bash
pip install -r requirements.txt
playwright install chromium
```

## Важные моменты при разработке

1. **Обработка ошибок**: всегда возвращать результат для каждого URL, даже при ошибке (`url, None`).
2. **Таймауты**: использовать разумные значения для загрузки страниц и элементов.
3. **User-Agent**: устанавливается явно, чтобы не нарваться на блокировки.
4. **Cookie Consent**: для YouTube — специальная обработка в `version_playwright/preview_generator/consent.py`.
5. **Логирование**: `logger`, а не `print`.
6. **Тестов нет** — перед любым крупным рефакторингом стоит добавить хотя бы smoke-тесты на `/health` и `/preview` и юнит на `poster.py`.

## Документация

- `docs/preview_generator_plan.md` — план оптимизации (извлечение готовых постеров вместо скриншотов).

## Язык общения

При работе с этим проектом общайтесь на русском языке.

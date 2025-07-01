# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## О проекте

Это сервис для генерации превью-изображений (скриншотов первых кадров) из видео по URL. Проект написан на Python и использует как Selenium (старая версия), так и Playwright (новая версия) для автоматизации браузера.

## Основные команды

### Запуск сервиса

```bash
# Основной скрипт (использует Selenium)
python main.py --urls https://example.com/video1 --width 640

# Версия с Playwright
python version_playwright/main_service.py

# FastAPI сервис
python client_preview_service.py
```

### Docker

```bash
# Сборка образа
docker build -t preview-generator .

# Запуск контейнера
docker run --rm \
    -v "$(pwd)/test_urls.json:/app/test_urls.json" \
    -v "$(pwd)/output:/app/previews" \
    preview-generator \
    --input-file test_urls.json \
    --output-dir previews

# Тестирование Docker
chmod +x docker_test.sh
./docker_test.sh
```

### Установка зависимостей

```bash
pip install -r requirements.txt

# Для Playwright также нужно установить браузеры
playwright install chromium
```

## Архитектура

### Основные компоненты

1. **generate_preview_service.py** - старая версия с Selenium для генерации превью
2. **version_playwright/** - новая версия с Playwright:
   - `preview_generate_service.py` - основной класс PreviewGenerator
   - `main_service.py` - точка входа для тестирования
3. **client_preview_service.py** - FastAPI сервис для HTTP API
4. **docs/preview_generator_plan.md** - план оптимизации (извлечение постеров вместо скриншотов)

### Ключевые особенности

- Асинхронная обработка списков URL
- Параллельная обработка с ограничением количества воркеров
- Поддержка извлечения готовых постеров (og:image, video.poster)
- Обработка YouTube cookie consent
- Автоматическое изменение размера изображений
- Детальное логирование

### Различия между версиями

- **Selenium версия**: использует webdriver.Chrome, синхронный подход с ThreadPoolExecutor
- **Playwright версия**: полностью асинхронная, поддержка разных браузеров, более быстрая работа

## Важные моменты при разработке

1. **Обработка ошибок**: Всегда возвращать результат для каждого URL, даже при ошибке (url, None)
2. **Таймауты**: Использовать разумные таймауты для загрузки страниц и элементов
3. **User-Agent**: Установлен для избежания блокировок
4. **Cookie Consent**: Специальная обработка для YouTube
5. **Логирование**: Использовать logger вместо print для отладки

## Язык общения

При работе с этим проектом общайтесь на русском языке.
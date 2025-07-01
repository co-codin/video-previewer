# Docker API для сервиса генерации превью видео

Этот модуль содержит Docker-конфигурацию для развертывания сервиса генерации превью на удаленном сервере.

## Структура

```
docker_api/
├── Dockerfile          # Образ для сервиса
├── docker-compose.yml  # Конфигурация для развертывания
├── .env.example       # Пример переменных окружения
└── README.md          # Этот файл
```

## Быстрый старт

### 1. Подготовка

```bash
# Клонирование репозитория
git clone <repository-url>
cd service_video_preview/docker_api

# Создание .env файла
cp .env.example .env
# Отредактируйте .env при необходимости
```

### 2. Сборка и запуск

```bash
# Сборка образа
docker-compose build

# Запуск сервиса
docker-compose up -d

# Проверка логов
docker-compose logs -f

# Остановка сервиса
docker-compose down
```

### 3. Проверка работоспособности

```bash
# Проверка здоровья сервиса
curl http://localhost:8000/health

# Информация о сервисе
curl http://localhost:8000/
```

## Использование API

### Генерация одного превью

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    "width": 640,
    "height": 360
  }'
```

### Пакетная генерация

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "https://vimeo.com/148751763",
      "https://www.dailymotion.com/video/x5w5x5c"
    ],
    "max_workers": 3
  }'
```

## Развертывание на удаленном сервере

### 1. Подготовка сервера

```bash
# Установка Docker и Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo systemctl enable docker
```

### 2. Копирование файлов

```bash
# На локальной машине
rsync -avz docker_api/ user@server:/path/to/deployment/

# Или через git
ssh user@server
git clone <repository-url>
cd service_video_preview/docker_api
```

### 3. Настройка и запуск

```bash
# На сервере
cd /path/to/deployment
cp .env.example .env
vim .env  # Настройте параметры

# Запуск
docker-compose up -d

# Настройка автозапуска
sudo systemctl enable docker
```

### 4. Настройка Nginx (опционально)

```nginx
server {
    listen 80;
    server_name preview.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Таймауты для длительной генерации
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

## Конфигурация

### Переменные окружения

- `API_HOST` - Хост для API (по умолчанию: 0.0.0.0)
- `API_PORT` - Порт для API (по умолчанию: 8000)
- `MAX_WORKERS` - Количество воркеров (по умолчанию: 5)
- `PREVIEW_WIDTH` - Ширина превью по умолчанию (640)
- `PREVIEW_HEIGHT` - Высота превью по умолчанию (360)
- `SCREENSHOT_TIMEOUT` - Таймаут для скриншота в секундах (30)
- `LOG_LEVEL` - Уровень логирования (INFO)

### Ресурсы

В `docker-compose.yml` настроены лимиты:
- CPU: 2 ядра (резерв: 1 ядро)
- Память: 2GB (резерв: 1GB)

Измените при необходимости в зависимости от нагрузки.

## Мониторинг

### Логи

```bash
# Все логи
docker-compose logs

# Только последние 100 строк
docker-compose logs --tail 100

# Следить за логами в реальном времени
docker-compose logs -f
```

### Метрики

```bash
# Использование ресурсов
docker stats video-preview-api

# Детальная информация
docker inspect video-preview-api
```

## Обновление

```bash
# Остановка сервиса
docker-compose down

# Обновление кода
git pull

# Пересборка и запуск
docker-compose build
docker-compose up -d
```

## Безопасность

1. **Ограничение доступа**: Используйте firewall или настройте доступ только из внутренней сети
2. **HTTPS**: Настройте SSL сертификат через Let's Encrypt
3. **Rate limiting**: Добавьте ограничение запросов в Nginx
4. **Аутентификация**: При необходимости добавьте API ключи

## Troubleshooting

### Сервис не запускается

```bash
# Проверка логов
docker-compose logs

# Проверка портов
sudo netstat -tlnp | grep 8000

# Перезапуск Docker
sudo systemctl restart docker
```

### Превью не генерируются

1. Проверьте доступность URL видео
2. Увеличьте таймауты в переменных окружения
3. Проверьте доступную память: `docker stats`

### Высокое потребление памяти

1. Уменьшите `MAX_WORKERS`
2. Настройте лимиты в `docker-compose.yml`
3. Включите swap на сервере
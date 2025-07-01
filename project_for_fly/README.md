# Развертывание на Fly.io

Оптимизированная версия сервиса для развертывания на платформе Fly.io, специально адаптированная для работы с Яндекс.Видео.

## Особенности

- **Минимальный размер образа** - использует alpine-based образ
- **Быстрое извлечение постеров** - приоритет на готовые изображения
- **Автоматическое масштабирование** - управляется Fly.io
- **Простой API** - один endpoint `/preview` для всех операций

## Структура

```
project_for_fly/
└── project/
    ├── app.py         # FastAPI приложение
    ├── Dockerfile     # Оптимизированный образ
    ├── fly.toml       # Конфигурация Fly.io
    └── requirements.txt
```

## Развертывание

### Предварительные требования

1. Установите [flyctl](https://fly.io/docs/hands-on/install-flyctl/)
2. Создайте аккаунт на [Fly.io](https://fly.io)
3. Войдите в систему: `fly auth login`

### Шаги развертывания

```bash
# Перейдите в директорию проекта
cd project_for_fly/project

# Создайте приложение (если еще не создано)
fly apps create yv-preview

# Развертывание
fly deploy

# Проверка статуса
fly status

# Просмотр логов
fly logs
```

### Обновление

```bash
# Внесите изменения в код
# Затем развертывание новой версии
fly deploy

# Откат к предыдущей версии (если нужно)
fly releases
fly deploy --image <previous-image-id>
```

## API использование

### Endpoint: POST /preview

Принимает список ID видео Яндекс.Видео и возвращает base64 изображения.

**Запрос:**
```json
{
  "items": ["vplvlm2tgrhg5e7iijtg", "vplvs2hcyadjk5noqxcn"]
}
```

**Ответ:**
```json
{
  "https://runtime.video.cloud.yandex.net/player/video/vplvlm2tgrhg5e7iijtg": "base64_image_data",
  "https://runtime.video.cloud.yandex.net/player/video/vplvs2hcyadjk5noqxcn": null
}
```

### Пример использования

```python
import httpx
import base64

async def get_previews(video_ids):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://yv-preview.fly.dev/preview",
            json={"items": video_ids}
        )
        data = response.json()
        
        for url, image_b64 in data.items():
            if image_b64:
                image_bytes = base64.b64decode(image_b64)
                # Сохранение или обработка изображения
```

## Конфигурация

### fly.toml

Основные параметры:
- `app = "yv-preview"` - имя приложения
- `primary_region = "waw"` - регион развертывания (Варшава)
- `internal_port = 8080` - внутренний порт приложения

### Масштабирование

```bash
# Изменение количества инстансов
fly scale count 2

# Изменение размера VM
fly scale vm shared-cpu-1x

# Автомасштабирование
fly autoscale set min=1 max=5
```

## Мониторинг

```bash
# Метрики
fly metrics

# Dashboard
fly dashboard

# Статус здоровья
curl https://yv-preview.fly.dev/preview
```

## Безопасность

1. **HTTPS** - автоматически предоставляется Fly.io
2. **Secrets** - для чувствительных данных используйте:
   ```bash
   fly secrets set API_KEY=your-secret-key
   ```
3. **IP whitelist** - настройте в dashboard при необходимости

## Troubleshooting

### Приложение не запускается

```bash
# Проверьте логи
fly logs

# Проверьте конфигурацию
fly config validate

# SSH в контейнер
fly ssh console
```

### Проблемы с Playwright

- Убедитесь, что в Dockerfile установлены все зависимости
- Проверьте размер VM (минимум 512MB RAM)

### Высокая задержка

1. Проверьте регион развертывания
2. Включите кеширование в приложении
3. Рассмотрите использование CDN для изображений

## Стоимость

- **Free tier**: 3 shared-cpu-1x VMs, 160GB bandwidth
- **Дополнительно**: ~$0.0000008/request
- Детали: https://fly.io/docs/about/pricing/
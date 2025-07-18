FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY docker_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка браузеров Playwright
RUN playwright install chromium chrome

# Копирование кода приложения
COPY docker_api/app.py .

# Создание директории для превью
RUN mkdir -p /app/previews

# Экспорт порта
EXPOSE 8080

# Запуск FastAPI сервера
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
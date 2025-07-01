FROM python:3.11-slim

# базовые утилиты
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg fonts-liberation libu2f-udev libvulkan1

# 1. Кладём публичный ключ в keyring-файл
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | \
    gpg --batch --yes --dearmor -o /usr/share/keyrings/google-linux-signing.gpg

# 2. Добавляем репозиторий с опцией signed-by
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing.gpg] \
      http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list

# 3. Ставим Chrome
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ---------- дальше ваш обычный пайплайн ----------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m playwright install --with-deps chromium

COPY app.py /app/app.py
WORKDIR /app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
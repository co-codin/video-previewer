# План ускорения генерации превью

## Ключевая идея  
1. **Сначала** пытаемся извлечь уже готовый постер/обложку, которую видеоплеер отдаёт в DOM.  
2. **Если постера нет** — делаем _быстрый_ скриншот (без `seeked`, `currentTime = 0`, пауза < 1 с).  
Так мы избегаем долгого ожидания загрузки кадра.

---

## Алгоритм

### 1. Получение постера  
`extract_poster_url(page)` возвращает первый валидный URL:  
| Приём | Селектор / источник |
|-------|---------------------|
| `video.poster` | `video.getAttribute("poster")` |
| Open Graph      | `meta[property="og:image"]` |
| Twitter card    | `meta[name="twitter:image"]` |
| Встроенный `img`| `video img[src]` в контейнере |

### 2. Загрузка постера  
`download_image(url)` (через `aiohttp`) ≤ 3 с:  
* проверка `content-type` на `image/*`  
* максимум 5 МБ, иначе прерываем  
* возвр. `bytes` либо `None`.

### 3. Обработка в `_process_single_url`  
```text
  ┌ after page.goto(...)
  │
  ├─ try extract_poster_url
  │   ├ if found → download_image → resize(Pillow) → DONE
  │   └ else → fallback_screenshot()
  │
  └ fallback_screenshot():
        video.currentTime = 0
        page.wait_for_timeout(500ms)
        video.screenshot(timeout=1000ms)
```

### 4. Тайминг  
* Поиск постера – < 50 мс  
* Скачивание – 150–300 мс  
* Fallback-скриншот – ≤ 1 с  
* Всего на превью: **≈ 0.2-1.3 с** вместо 3-5 с+.

---

## Mermaid-диаграмма
```mermaid
flowchart TD
    A[goto(URL)] --> B{video\nнайден?}
    B -- нет --> Z[Ошибка]
    B -- да --> C{poster URL?}
    C -- есть --> D[download\nposter]
    D --> E[resize & save]
    C -- нет --> F[fast screenshot]
    F --> E
```

---

## Изменения в коде  

1. **preview_generate_service.py**  
   * новая `extract_poster_url`, `download_image`, `fallback_screenshot`.  
   * упрощённая логика `_process_single_url`.

2. **requirements.txt** – добавить `aiohttp>=3.9`.

3. **main_service.py** — без изменений.

---

## Тест-кейс  
URLs:  
* `https://runtime.video.cloud.yandex.net/player/video/vplvlm2tgrhg5e7iijtg`  
* YouTube / Vimeo для проверки fallback.

Ожидаемое время генерации < 1.5 с на ссылку.
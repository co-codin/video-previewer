import asyncio
import json
import logging
import os
from typing import List

# Импортируем новый класс генератора
from preview_generate_service import PreviewGenerator, PreviewGeneratorError

# Настройка логирования (можно использовать ту же конфигурацию)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('preview_generator_test_client')

# --- Константы и Настройки ---
# Используем существующий файл с тестовыми URL
TEST_URL_FILE = "test_urls.json"
# Директория для сохранения превью от Playwright-версии
OUTPUT_DIR = "previews_pw"
# Параметры для генератора
GENERATOR_WIDTH = 720
GENERATOR_WORKERS = 3
GENERATOR_TIMEOUT = 20  # Увеличим таймаут для тестов


def load_test_urls(file_path: str) -> List[str]:
    """Загружает URL из JSON-файла для теста."""
    if not os.path.exists(file_path):
        logger.warning(
            f"Файл с тестовыми URL не найден: {file_path}. "
            "Используется пустой список."
        )
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return [url for url in data if isinstance(url, str)]
            elif isinstance(data, dict) and 'urls' in data:
                urls = data.get('urls', [])
                return [url for url in urls if isinstance(url, str)]
            else:
                logger.error(f"Неподдерживаемый формат JSON в {file_path}")
                return []
    except json.JSONDecodeError:
        logger.error(f"Ошибка декодирования JSON в {file_path}")
        return []
    except Exception as e:
        logger.error(f"Ошибка загрузки URL из {file_path}: {e}")
        return []


async def run_test():
    """Основная асинхронная функция для тестирования генератора."""
    logger.info(
        "--- Запуск тестового клиента для PreviewGenerator (Playwright) ---"
    )

    # Используем только тестовый URL Yandex
    test_url_yandex = "https://runtime.video.cloud.yandex.net/player/video/" \
                      "vplvlm2tgrhg5e7iijtg"
    test_urls = [test_url_yandex]
    logger.info(f"Используется тестовый URL: {test_urls[0]}")
    logger.info(f"Превью будут сохранены в директорию: {OUTPUT_DIR}")

    # Создаем экземпляр генератора
    generator = PreviewGenerator(
        width=GENERATOR_WIDTH,
        max_workers=GENERATOR_WORKERS,
        timeout=GENERATOR_TIMEOUT
    )

    try:
        logger.info("Вызов process_url_list_to_files...")
        # Запускаем обработку и сохранение в файлы
        results = await generator.process_url_list_to_files(
            test_urls, OUTPUT_DIR
        )

        logger.info("--- Результаты обработки ---")
        successful_count = 0
        failed_count = 0
        for url, file_path in results:
            if file_path:
                logger.info(f"  [+] Успех: {url} -> {file_path}")
                successful_count += 1
            else:
                logger.warning(
                    f"  [-] Ошибка: {url} -> Не удалось создать превью"
                )
                failed_count += 1

        logger.info("--- Итоги ---")
        logger.info(f"  Всего URL: {len(test_urls)}")
        logger.info(f"  Успешно обработано: {successful_count}")
        logger.info(f"  Ошибок: {failed_count}")

    except PreviewGeneratorError as e:
        logger.error(f"Критическая ошибка генератора превью: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка в тестовом клиенте: {e}")
    finally:
        # Важно закрыть ресурсы генератора
        logger.info("Закрытие генератора...")
        await generator.close()
        logger.info("Генератор закрыт.")

    logger.info("--- Тестовый клиент завершил работу ---")


if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(run_test())
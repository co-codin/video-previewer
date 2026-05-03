"""Обработка плашки cookie consent (в первую очередь YouTube)."""
import logging

from playwright.async_api import Error as PlaywrightError, Page

logger = logging.getLogger(__name__)

CONSENT_FORM_SELECTOR = (
    'ytd-consent-bump-v2-lightbox, '
    'form[action*="consent.youtube.com"]'
)
ACCEPT_BUTTON_SELECTOR = (
    'button[aria-label*="Accept"], '
    'button[aria-label*="Agree"], '
    'button:has-text("Accept all"), '
    'button:has-text("Agree")'
)
CLICK_TIMEOUT_MS = 3000
POST_CLICK_PAUSE_MS = 500


async def dismiss_cookie_consent(page: Page, url: str) -> None:
    """Если на странице есть форма согласия cookie — кликает 'Принять все'.

    Любые ошибки логируются и игнорируются: продолжать обработку имеет смысл
    даже при сбое в обработке консента.
    """
    try:
        consent_form = await page.query_selector(CONSENT_FORM_SELECTOR)
        if not consent_form:
            logger.info(
                "Форма/кнопка согласия cookie не найдена для %s "
                "(возможно, уже принята)", url,
            )
            return

        logger.info("Найдена форма согласия cookie для %s, ищем кнопку 'Принять все'", url)
        accept_button = await consent_form.query_selector(ACCEPT_BUTTON_SELECTOR)
        if not accept_button:
            logger.warning(
                "Форма согласия найдена, но кнопка 'Принять все' — нет для %s", url,
            )
            return

        await accept_button.click(timeout=CLICK_TIMEOUT_MS)
        await page.wait_for_timeout(POST_CLICK_PAUSE_MS)
        logger.info("Клик по кнопке согласия выполнен для %s", url)
    except PlaywrightError:
        logger.warning("Ошибка при обработке согласия cookie для %s", url, exc_info=True)

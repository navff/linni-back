import asyncio
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .config import settings

logger = logging.getLogger(__name__)

bot: Bot | None = None


def get_bot() -> Bot | None:
    global bot
    if bot is None and settings.BOT_TOKEN:
        bot = Bot(token=settings.BOT_TOKEN)
    return bot


async def send_rating_request(user_id: int) -> None:
    """Отправляет однократный запрос оценки после 1-й записи."""
    b = get_bot()
    if b is None:
        return
    try:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Оценить Линни",
                        url=f"https://max.ru/{settings.BOT_NAME}",
                    )
                ]
            ]
        )
        await b.send_message(
            chat_id=user_id,
            text=(
                "Первая запись добавлена 👍\n\n"
                "Если приложение нравится — поставьте оценку в каталоге MAX, "
                "это очень помогает нам развиваться."
            ),
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.warning("Failed to send rating request to %s: %s", user_id, e)

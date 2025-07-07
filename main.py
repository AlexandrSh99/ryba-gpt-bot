import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from g4f.client import Client
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
gpt_client = Client()

# Хранилище количества запросов
user_requests = {}

# Максимум бесплатных запросов
FREE_LIMIT = 6

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎣 Привет! Я бот для обучения рыбалке.\n"
        "Можешь задать любой вопрос про снасти, водоёмы, наживки и т.д.\n\n"
        "Бесплатно доступно 6 запросов, дальше — оплата 💰"
    )

@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_requests[user_id] = user_requests.get(user_id, 0)

    if user_requests[user_id] >= FREE_LIMIT:
        await message.answer("🔒 Лимит из 6 бесплатных сообщений исчерпан. Чтобы продолжить — оплати доступ.")
        return

    await message.answer("🕔 Думаю...")

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        user_requests[user_id] += 1
        await message.answer(response.choices[0].message.content)

    except Exception as e:
        logging.exception(e)
        await message.answer("⚠️ Ошибка при обращении к AI.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

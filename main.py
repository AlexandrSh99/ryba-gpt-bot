import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv
from collections import defaultdict
import g4f

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Память на запросы пользователей
user_requests = defaultdict(int)

# Ответы
START_MESSAGE = (
    "👋 Привет! Я РыбаГид — бот для помощи в обучении рыбалке.\n"
    "Я подскажу по снастям, техникам ловли и особенностям водоёмов.\n\n"
    "Бесплатно доступно 6 запросов. Потом — доступ после оплаты."
)
LIMIT_MESSAGE = "❌ Вы израсходовали 6 бесплатных запросов. Для продолжения — оплатите доступ."

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(START_MESSAGE)

@dp.message(F.text)
async def handle_request(message: Message):
    user_id = message.from_user.id
    if user_requests[user_id] >= 6:
        await message.answer(LIMIT_MESSAGE)
        return

    user_requests[user_id] += 1
    await message.answer("🔄 Обрабатываю запрос...")

    try:
        response = await g4f.ChatCompletion.create_async(
            model="gpt-4o-mini",
            provider=g4f.Provider.You,
            messages=[{"role": "user", "content": message.text}]
        )
        await message.answer(response)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при обращении к AI: {e}")

async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)


def create_app():
    app = web.Application()
    dp.startup.register(on_startup)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), port=int(os.environ.get("PORT", 10000)))

import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv
import g4f

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
bot.set_current(bot)
dp = Dispatcher(storage=MemoryStorage())

user_requests = {}
FREE_LIMIT = 6

async def ask_gpt(message_text: str) -> str:
    try:
        response = await g4f.ChatCompletion.create_async(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message_text}],
            provider=g4f.Provider.You
        )
        return response
    except Exception as e:
        return f"⚠️ Ошибка при обращении к AI: {e}"

@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer(
        "Привет! 🎣 Я бот, который поможет тебе разобраться в рыбалке: где ловить, на что, когда и как.\n\n"
        "Ты можешь задать вопрос — например: ‘Где ловить щуку летом?’\n\n"
        "🔹 Доступно 6 бесплатных запросов, далее — нужна оплата."
    )

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    count = user_requests.get(user_id, 0)

    if count >= FREE_LIMIT:
        await message.answer("🚫 Лимит бесплатных запросов исчерпан. Чтобы продолжить — оплатите подписку.")
        return

    user_requests[user_id] = count + 1
    await message.answer("⌛ Обрабатываю запрос...")
    reply = await ask_gpt(message.text)
    await message.answer(reply)

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

def create_app():
    app = web.Application()
    dp.startup.register(on_startup)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp)
    return app

if __name__ == '__main__':
    web.run_app(create_app(), port=int(os.environ.get('PORT', 10000)))

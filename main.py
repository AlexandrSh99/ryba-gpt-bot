import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = "user_data.json"

# ——— Helpers ———
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

user_data = load_data()

# ——— Handlers ———
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"used": 0, "unlimited": False}
        save_data(user_data)

    await message.answer(
        "👋 Привет! Я бот, который помогает с рыбалкой — рассказываю где ловить, на что и как.\n\n"
        "Ты можешь задать до 6 вопросов бесплатно, а потом потребуется оплата для безлимитного доступа."
    )

@dp.message()
async def handle_message(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"used": 0, "unlimited": False}

    user = user_data[user_id]

    if not user["unlimited"] and user["used"] >= 6:
        await message.answer("💸 Лимит исчерпан. Чтобы продолжить — нужно оплатить доступ.")
        return

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        reply = response.choices[0].message.content
    except Exception as e:
        await message.answer("⚠️ Ошибка при обращении к AI.")
        return

    await message.answer(reply)

    if not user["unlimited"]:
        user["used"] += 1
        save_data(user_data)

# ——— Webhook Setup ———
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

def create_app():
    app = web.Application()
    dp.startup.register(on_startup)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), port=int(os.environ.get("PORT", 10000)))

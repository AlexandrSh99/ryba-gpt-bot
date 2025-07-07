import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Состояния
class UserState(StatesGroup):
    region = State()
    lake = State()
    allowed_requests = State()

# Приветствие и старт
@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(requests_left=6)
    await message.answer("🎣 Привет! Я бот, который поможет тебе научиться рыбалке.\n\nГде ты ловишь рыбу? Напиши область (например, Ленинградская):")
    await state.set_state(UserState.region)

# Шаг 1 — Область
@dp.message(UserState.region)
async def get_region(message: Message, state: FSMContext):
    await state.update_data(region=message.text)
    await message.answer("Уточни водоём — озеро или река:")
    await state.set_state(UserState.lake)

# Шаг 2 — Водоём
@dp.message(UserState.lake)
async def get_lake(message: Message, state: FSMContext):
    await state.update_data(lake=message.text)
    data = await state.get_data()
    await message.answer(f"Отлично! 📍 Район: {data['region']}, водоём: {data['lake']}\n\nМожешь задать свой вопрос по рыбалке.")
    await state.set_state(None)

# Основной хендлер
@dp.message()
async def handle_question(message: Message, state: FSMContext):
    data = await state.get_data()
    requests_left = data.get("requests_left", 0)

    if requests_left == 0:
        await message.answer("🔒 Лимит из 6 бесплатных вопросов исчерпан.\nДля продолжения отправь оплату.")
        return

    try:
        await message.answer("⏳ Думаю...")
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response.choices[0].message.content.strip()
        await message.answer(answer)

        await state.update_data(requests_left=requests_left - 1)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка при обращении к AI: {e}")

# Запуск вебхука
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

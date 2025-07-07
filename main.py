import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# База данных
conn = sqlite3.connect("requests.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, count INTEGER)")
conn.commit()

# Состояния FSM
class AskState(StatesGroup):
    waiting_for_question = State()

# Клавиатура
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎣 Задать вопрос", callback_data="ask")]
    ])

# Команда /start
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я помогу тебе разобраться в рыбалке: снасти, техника, места и другое.\n\n"
        "Ты можешь задать до 6 вопросов бесплатно.\n\n"
        "Готов? Жми кнопку 👇",
        reply_markup=get_main_keyboard()
    )

# Нажатие на кнопку
@dp.callback_query(F.data == "ask")
async def on_ask(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cursor.execute("SELECT count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute("INSERT INTO users (user_id, count) VALUES (?, ?)", (user_id, 0))
        conn.commit()
        row = (0,)

    if row[0] < 6:
        await state.set_state(AskState.waiting_for_question)
        await callback.message.answer("✍️ Введи свой вопрос:")
    else:
        await callback.message.answer("⚠️ Лимит бесплатных вопросов исчерпан. Чтобы продолжить — оплати доступ.")

    await callback.answer()

# Получение вопроса
@dp.message(AskState.waiting_for_question)
async def handle_question(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_question = message.text

    # Лимит
    cursor.execute("SELECT count FROM users WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    if count >= 6:
        await message.answer("⚠️ Лимит бесплатных вопросов исчерпан.")
        await state.clear()
        return

    # Увеличиваем счётчик
    cursor.execute("UPDATE users SET count = ? WHERE user_id = ?", (count + 1, user_id))
    conn.commit()

    await message.answer("🔄 Думаю...")

    # ChatGPT
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_question}]
        )
        answer = response.choices[0].message.content
        await message.answer(f"🎣 Ответ:\n\n{answer}")
    except Exception as e:
        await message.answer(f"❌ Ошибка запроса: {e}")

    await state.clear()

# Webhook
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

def create_app():
    app = web.Application()
    dp.startup.register(on_startup)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp)
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(create_app(), port=int(os.getenv("PORT", 10000)))

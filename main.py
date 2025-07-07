import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# --- Инициализация ---
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# --- База данных для учёта запросов ---
conn = sqlite3.connect("requests.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, count INTEGER)")
conn.commit()

# --- Кнопки ---
def get_main_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎣 Задать вопрос", callback_data="ask")]
    ])
    return kb

# --- Старт ---
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я помогу тебе разобраться в рыбалке — расскажу про снасти, технику, места и многое другое.\n\n"
        "Ты можешь задать до 6 вопросов бесплатно.\n\n"
        "Готов? Жми кнопку 👇",
        reply_markup=get_main_keyboard()
    )

# --- Обработка кнопки ---
@dp.callback_query(F.data == "ask")
async def on_ask(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute("INSERT INTO users (user_id, count) VALUES (?, ?)", (user_id, 1))
        conn.commit()
        await callback.message.answer("✅ Вопрос принят! (1 из 6)")
    elif row[0] < 6:
        new_count = row[0] + 1
        cursor.execute("UPDATE users SET count = ? WHERE user_id = ?", (new_count, user_id))
        conn.commit()
        await callback.message.answer(f"✅ Вопрос принят! ({new_count} из 6)")
    else:
        await callback.message.answer("⚠️ Лимит бесплатных вопросов исчерпан.\nЧтобы продолжить, нужно оплатить доступ.")

    await callback.answer()

# --- Webhook ---
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

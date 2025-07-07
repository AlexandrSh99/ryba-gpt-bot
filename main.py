
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("Привет! Я рыба-гид. Задай вопрос про снасти, озёра, способы ловли.")

@dp.message_handler()
async def handle_message(message: types.Message):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты помощник-рыболов. Отвечай кратко и по делу."},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

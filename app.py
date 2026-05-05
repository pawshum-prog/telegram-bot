import asyncio
import requests
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp_socks import ProxyConnector
import sys

logging.basicConfig(level=logging.INFO)

TOKEN = '8382164433:AAEUA5dqWWqf1fZ-pZXY9hZtGWRlOo_kF0U'
DIFY_API_KEY = 'app-oecgBMrh2zfX3b1GmkVnb4SV'
DIFY_URL = 'https://api.dify.ai/v1/chat-messages'

# Используем SOCKS5 прокси для Telegram API
PROXY_URL = 'socks5://95.164.17.24:13058'

# Сессия с SOCKS5 прокси
connector = ProxyConnector.from_url(PROXY_URL)
session = AiohttpSession(connector=connector)
bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

@dp.message()
async def handle_message(message: types.Message):
    if not message.text:
        return
    
    logging.info(f"Сообщение: {message.text}")
    
    try:
        res = requests.post(
            DIFY_URL,
            headers={
                "Authorization": f"Bearer {DIFY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": {},
                "query": message.text,
                "response_mode": "blocking",
                "user": f"user_{message.from_user.id}"
            },
            timeout=60
        )
        
        if res.status_code == 200:
            answer = res.json().get("answer", "")
            await message.answer(answer if answer else "Пустой ответ от Dify")
        else:
            await message.answer(f"Ошибка: {res.status_code}")
            
    except Exception as e:
        logging.error(e)
        await message.answer("Ошибка обработки")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import json
import logging
import requests
from contextlib import asynccontextmanager
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from fastapi import FastAPI, Request

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = '8382164433:AAEUA5dqWWqf1fZ-pZXY9hZtGWRlOo_kF0U'
DIFY_API_KEY = 'app-oecgBMrh2zfX3b1GmkVnb4SV'
DIFY_URL = 'https://api.dify.ai/v1/chat-messages'
RENDER_URL = 'https://telegram-bot-om1g.onrender.com'

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Lifespan для управления вебхуком
@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.delete_webhook(drop_pending_updates=True)
    webhook_url = f"{RENDER_URL}/webhook"
    await bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook установлен: {webhook_url}")
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

# Webhook endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"📨 Получено сообщение от Telegram")
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"❌ Ошибка в вебхуке: {e}")
    return {"ok": True}

# Health-check
@app.get("/")
async def health():
    return {"status": "ALIVE"}

# Обработчик сообщений
@dp.message()
async def handle_message(message: types.Message):
    if not message.text:
        return
    
    logger.info(f"💬 От пользователя: {message.text}")
    
    try:
        # Отправляем запрос в Dify (streaming режим)
        res = requests.post(
            DIFY_URL,
            headers={
                "Authorization": f"Bearer {DIFY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": {},
                "query": message.text,
                "response_mode": "streaming",
                "user": f"user_{message.from_user.id}"
            },
            timeout=120,
            stream=True
        )
        
        logger.info(f"🤖 Dify ответил: {res.status_code}")
        
        if res.status_code == 200:
            # Собираем ответ из потока
            full_answer = ""
            for line in res.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data:'):
                        try:
                            data = json.loads(line_str[5:])
                            if data.get("event") in ["message", "agent_message"]:
                                full_answer += data.get("answer", "")
                        except:
                            continue
            
            if full_answer:
                await message.answer(full_answer)
                logger.info("✅ Ответ отправлен пользователю")
            else:
                await message.answer("Dify не вернул ответ")
                logger.warning("⚠️ Пустой ответ от Dify")
        else:
            logger.error(f"Dify Error: {res.text}")
            await message.answer(f"❌ Ошибка Dify API: {res.status_code}")
            
    except Exception as e:
        logger.error(f"🔥 Критическая ошибка: {e}")
        await message.answer("🔄 Сервис временно недоступен, попробуйте позже.")

if __name__ == "__main__":
    logger.info("🚀 Запуск сервера...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

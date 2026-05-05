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
DIFY_API_KEY = 'app-0ByvHoyrt2GYUvHXJ89N1YsV'  # ← ЗАМЕНИТЕ
DIFY_URL = 'https://api.dify.ai/v1/workflows/run'
RENDER_URL = 'https://telegram-bot-om1g.onrender.com'

bot = Bot(token=TOKEN)
dp = Dispatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.delete_webhook(drop_pending_updates=True)
    webhook_url = f"{RENDER_URL}/webhook"
    await bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook установлен: {webhook_url}")
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

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

@app.get("/")
async def health():
    return {"status": "ALIVE"}

@dp.message()
async def handle_message(message: types.Message):
    if not message.text:
        return
    
    logger.info(f"💬 От пользователя: {message.text}")
    
    try:
        res = requests.post(
            DIFY_URL,
            headers={
                "Authorization": f"Bearer {DIFY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": {"query": message.text},
                "response_mode": "streaming",
                "user": f"user_{message.from_user.id}"
            },
            timeout=180,
            stream=True
        )
        
        logger.info(f"🤖 Workflow ответил: {res.status_code}")
        
        if res.status_code == 200:
            raw_text = res.text
            logger.info(f"RAW FULL: {raw_text[:500]}")
            
            full_answer = ""
            
            for line in raw_text.split('\n'):
                if line.startswith('data:'):
                    try:
                        data = json.loads(line[5:])
                        if "outputs" in data and "text" in data["outputs"]:
                            full_answer = data["outputs"]["text"]
                        elif "answer" in data:
                            full_answer += str(data.get("answer", ""))
                    except:
                        continue
            
            if not full_answer:
                try:
                    json_data = res.json()
                    logger.info(f"JSON: {json_data}")
                    if "data" in json_data:
                        full_answer = json_data["data"].get("outputs", {}).get("text", "")
                    elif "outputs" in json_data:
                        full_answer = json_data["outputs"].get("text", "")
                except:
                    pass
            
            if full_answer:
                await message.answer(full_answer)
                logger.info("✅ Ответ отправлен")
            else:
                await message.answer("Workflow не вернул ответ")
                logger.warning("⚠️ Не смогли извлечь ответ")
        else:
            logger.error(f"Workflow Error: {res.text}")
            await message.answer(f"❌ Ошибка Workflow API: {res.status_code}")
            
    except requests.exceptions.ReadTimeout:
        logger.error("🔥 Таймаут при ожидании ответа от Dify")
        await message.answer("🔄 Сервис выполняется слишком долго. Попробуйте уточнить запрос или повторите позже.")
    except Exception as e:
        logger.error(f"🔥 Критическая ошибка: {e}")
        await message.answer("🔄 Сервис временно недоступен, попробуйте позже.")

if __name__ == "__main__":
    logger.info("🚀 Запуск сервера...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

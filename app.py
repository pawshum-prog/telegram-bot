import requests
import logging
from aiogram import Bot, Dispatcher, types
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import uvicorn

logging.basicConfig(level=logging.INFO)

TOKEN = '8382164433:AAEUA5dqWWqf1fZ-pZXY9hZtGWRlOo_kF0U'
DIFY_API_KEY = 'app-oecgBMrh2zfX3b1GmkVnb4SV'
DIFY_URL = 'https://api.dify.ai/v1/chat-messages'

# Render даст вам URL после деплоя, пока ставим заглушку
RENDER_URL = 'https://ваш-сервис.onrender.com'

bot = Bot(token=TOKEN)
dp = Dispatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_url = f"{RENDER_URL}/webhook"
    await bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook установлен: {webhook_url}")
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.get("/")
async def health():
    return {"status": "ok"}

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

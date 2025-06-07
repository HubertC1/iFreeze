from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
import os
from dotenv import load_dotenv
from .line_bot.handler import handle_text_message
from .models.database import Base
from .database import engine, get_db
from sqlalchemy.orm import Session

# Create database tables
Base.metadata.create_all(bind=engine)

load_dotenv()

app = FastAPI(title="iFreeze API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LINE Bot setup
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

@app.post("/webhook")
async def line_webhook(request: Request):
    signature = request.headers["X-Line-Signature"]
    body = await request.body()
    
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    return {"status": "ok"}

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    handle_text_message(event)

@app.get("/")
async def root():
    return {"message": "Welcome to iFreeze API"}

@app.get("/fridge/status")
async def get_status(db: Session = Depends(get_db)):
    from .services.fridge_service import get_fridge_status
    return {"status": get_fridge_status(db)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
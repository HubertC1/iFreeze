from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage
import os
from dotenv import load_dotenv
from .line_bot.handler import handle_text_message, handle_image_message
from .models.database import Base
from .database import engine, get_db
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from .models.database import FoodItem

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

# Serve LIFF frontend at /liff
liff_path = os.path.join(os.path.dirname(__file__), 'static', 'liff')
if os.path.exists(liff_path):
    app.mount("/liff", StaticFiles(directory=liff_path, html=True), name="liff")

# LINE Bot setup
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

STATIC_IMAGE_DIR = os.path.join(os.path.dirname(__file__), 'static', 'images')
os.makedirs(STATIC_IMAGE_DIR, exist_ok=True)

@app.post("/webhook")
async def line_webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    print("[WEBHOOK] Received body:", body)
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        print("[WEBHOOK] Invalid signature error")
        return {"status": "invalid signature"}
    except Exception as e:
        print("[WEBHOOK] Exception:", e)
        print("[WEBHOOK] Raw body:", body)
        return {"status": "error", "error": str(e)}
    return {"status": "ok"}

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    handle_text_message(event)

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    handle_image_message(event)

@app.get("/")
async def root():
    return {"message": "Welcome to iFreeze API"}

@app.get("/fridge/status")
async def get_status(db: Session = Depends(get_db)):
    from .services.fridge_service import get_fridge_status
    return {"status": get_fridge_status(db)}

@app.get("/fridge/foods")
async def get_foods(db: Session = Depends(get_db)):
    foods = db.query(FoodItem).all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "added_date": f.added_date.strftime('%Y-%m-%d'),
            "expiry_date": f.expiry_date.strftime('%Y-%m-%d') if f.expiry_date else None,
            "status": f.status
        }
        for f in foods
    ]

@app.post("/fridge/image")
async def process_fridge_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    logging.info(f"[DEBUG] Received file: {file.filename}, size: {len(image_bytes)} bytes, content_type: {file.content_type}")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Save with original filename and extension, prefixed with timestamp
    filename = f"api_{timestamp}_{file.filename}"
    filepath = os.path.join(STATIC_IMAGE_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(image_bytes)
    return {"status": "success", "message": f"[DEBUG] File received and saved as: {filepath}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
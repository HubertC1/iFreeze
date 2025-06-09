from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage
import os
from dotenv import load_dotenv
from .line_bot.handler import handle_text_message, handle_image_message, process_image
from .models.database import Base
from .database import engine, get_db
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from .models.database import FoodItem
from fastapi.responses import FileResponse

# Global variable to track photo request state
take_photo_requested = False

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
frontend_build_dir = os.path.join(os.path.dirname(__file__), '../liff-frontend/dist')
app.mount("/liff", StaticFiles(directory=frontend_build_dir, html=True), name="liff")

# Mount static images directory
# STATIC_IMAGE_DIR = os.path.join(os.path.dirname(__file__), 'static', 'images')
STATIC_IMAGE_DIR = "/Users/hubert/NTU/Courses/WebLab/iFreeze/app/static/images"
os.makedirs(STATIC_IMAGE_DIR, exist_ok=True)
app.mount("/static/images", StaticFiles(directory=STATIC_IMAGE_DIR), name="static_images")

# LINE Bot setup
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

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

@app.post("/upload/zip")
async def upload_zip(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")
    
    # Create a directory for zip files if it doesn't exist
    ZIP_DIR = os.path.join(os.path.dirname(__file__), 'static', 'zips')
    os.makedirs(ZIP_DIR, exist_ok=True)
    
    # Read the file content
    file_bytes = await file.read()
    logging.info(f"[DEBUG] Received zip file: {file.filename}, size: {len(file_bytes)} bytes")
    
    # Save with timestamp prefix
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"upload_{timestamp}_{file.filename}"
    filepath = os.path.join(ZIP_DIR, filename)
    
    # Save the file
    with open(filepath, 'wb') as f:
        f.write(file_bytes)
    
    return {
        "status": "success",
        "message": f"File uploaded successfully",
        "filename": filename,
        "size": len(file_bytes)
    }

@app.get("/static/images/{filename}")
async def get_image(filename: str):
    image_path = os.path.join(STATIC_IMAGE_DIR, filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Image not found: {filename}")
    
    return FileResponse(image_path)

@app.get("/api/images")
async def list_images():
    try:
        files = os.listdir(STATIC_IMAGE_DIR)
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        return {
            "status": "success",
            "images": image_files,
            "count": len(image_files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/set-take-photo")
async def set_take_photo():
    global take_photo_requested
    take_photo_requested = True
    return {"status": "success", "message": "Photo request set to true"}

@app.get("/api/check-take-photo")
async def check_take_photo():
    global take_photo_requested
    if take_photo_requested:
        take_photo_requested = False  # Reset the flag after checking
        return {"status": "success", "take_photo": True}
    return {"status": "success", "take_photo": False}

@app.post("/upload/image")
async def upload_image(file: UploadFile = File(...)):
    # Check if file is an image
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Read the file content
    file_bytes = await file.read()
    logging.info(f"[DEBUG] Received image file: {file.filename}, size: {len(file_bytes)} bytes, content_type: {file.content_type}")
    
    # Save with timestamp prefix
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"rpi_{timestamp}_{file.filename}"
    filepath = os.path.join(STATIC_IMAGE_DIR, filename)
    
    # Save the file
    with open(filepath, 'wb') as f:
        f.write(file_bytes)
    
    # Process the image
    success, response_text = process_image(filepath)
    
    return {
        "status": "success" if success else "error",
        "message": response_text,
        "filename": filename,
        "size": len(file_bytes),
        "url": f"/static/images/{filename}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage
import os
from dotenv import load_dotenv
from .line_bot.handler import handle_text_message, handle_image_message, process_image, handler
from .models.database import Base
from .database import engine, get_db
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from .models.database import FoodItem
from fastapi.responses import FileResponse
import zipfile
import shutil
import json
import requests
import base64

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
    processed_foods = [
        f for f in foods
        if not (f.name.startswith("Object") and f.category == "unknown")
    ]
    return [
        {
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "added_date": f.added_date.strftime('%Y-%m-%d'),
            "expiry_date": f.expiry_date.strftime('%Y-%m-%d') if f.expiry_date else None,
            "status": f.status,
            "temp_object_id": f.temp_object_id
        }
        for f in processed_foods
    ]

@app.post("/fridge/image")
async def process_fridge_image(file: UploadFile = File(...)):
    try:
        # Read the uploaded file
        image_bytes = await file.read()
        logging.info(f"[DEBUG] Received file: {file.filename}, size: {len(image_bytes)} bytes, content_type: {file.content_type}")
        
        # Save image to static/images with timestamp like LINE bot does
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"api_{timestamp}_{file.filename}" if file.filename else f"api_{timestamp}.jpg"
        filepath = os.path.join(STATIC_IMAGE_DIR, filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        logging.info(f"[DEBUG] Image saved to: {filepath}")
        
        # Process the image using the same pipeline as LINE bot
        success, response_text = process_image(filepath)
        logging.info(f"[DEBUG] Image processing result: {success}, Response: {response_text}")
        
        if success:
            return {
                "status": "success", 
                "message": "Image uploaded and sent for processing",
                "filename": filename,
                "processing_response": response_text
            }
        else:
            return {
                "status": "partial_success",
                "message": f"Image saved but processing failed: {response_text}",
                "filename": filename
            }
            
    except Exception as e:
        logging.error(f"[ERROR] Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# Helper function to process the uploaded zip file
# This function will be run in the background

def process_zip_file(zip_path):
    import time
    from app.models.database import FoodItem, Base
    from app.database import SessionLocal
    
    # 1. Unzip the file to a temp directory
    temp_dir = zip_path + "_unzipped"
    os.makedirs(temp_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # 2. Load JSON files from the 'json' subdirectory
    def load_json(filename):
        with open(os.path.join(temp_dir, 'json', filename), 'r') as f:
            return json.load(f)
    try:
        old_json = load_json('old.json')
        new_json = load_json('new.json')
        match_json = load_json('match.json')
        delete_json = load_json('delete.json')
        add_json = load_json('add.json')
    except Exception as e:
        print(f"[ERROR] Failed to load JSONs: {e}")
        shutil.rmtree(temp_dir)
        return

    # 3. Open DB session
    db = SessionLocal()
    try:
        # 4. Delete items in delete.json
        for entry in delete_json:
            old_id = entry['old_object_id']
            item = db.query(FoodItem).filter(FoodItem.temp_object_id == old_id).first()
            if item:
                db.delete(item)
        db.commit()

        # 5. Update matched items (change temp_object_id)
        for entry in match_json:
            old_id = entry['old_object_id']
            new_id = entry['new_object_id']
            item = db.query(FoodItem).filter(FoodItem.temp_object_id == old_id).first()
            if item:
                item.temp_object_id = new_id
        db.commit()

        # 6. Add new items from add.json
        for entry in add_json:
            new_id = entry['new_object_id']
            # You may want to extract more info from new_json (like bounding_box, image_path)
            # For now, just add with temp_object_id
            new_item = FoodItem(temp_object_id=new_id, name=f"Object {new_id}", category="unknown", status="fresh")
            db.add(new_item)
        db.commit()
    finally:
        db.close()

    # 7. Update images in static/ind_images
    IND_IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'static', 'ind_images')
    # Remove all existing images
    for f in os.listdir(IND_IMAGES_DIR):
        file_path = os.path.join(IND_IMAGES_DIR, f)
        if os.path.isfile(file_path):
            os.remove(file_path)
    # Copy images for all current items (based on new_json)
    for obj in new_json:
        img_src = os.path.join(temp_dir, os.path.basename(obj['image_path']))
        img_dst = os.path.join(IND_IMAGES_DIR, os.path.basename(obj['image_path']))
        if os.path.exists(img_src):
            shutil.copy(img_src, img_dst)

    # 8. Clean up temp dir
    shutil.rmtree(temp_dir)

    # 9. Analyze images and update FoodItem info
    update_food_items_from_images()

def analyze_image_with_openai(image_path):
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv()
    ngrok_base = os.getenv('VITE_NGROK_URL_BASE')
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"apikey:{api_key}")
    client = OpenAI(api_key=api_key)
    filename = os.path.basename(image_path)
    image_url = f"{ngrok_base}/static/ind_images/{filename}"
    
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "user", "content": "Analyze the image and list all visible food items, their estimated category, expiry date (if possible), and whether they look fresh, spoiling, or spoiled. Return your answer as a JSON object with keys: name, category, expiry_date, status. If you don't know expiry_date, return null."},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image", 
                            "image_url": image_url
                        }
                    ]
                }
            ]
        )
        content = response.output_text
        import json as pyjson
        start = content.find('{')
        end = content.rfind('}') + 1
        json_str = content[start:end]
        return pyjson.loads(json_str)
    except Exception as e:
        print(f"[ERROR] OpenAI API call failed or response parsing failed: {e}")
        return None

def update_food_items_from_images():
    IND_IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'static', 'ind_images')
    from app.models.database import FoodItem
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        for filename in os.listdir(IND_IMAGES_DIR):
            if filename.endswith('.png'):
                try:
                    temp_object_id = int(filename.split('_')[1].split('.')[0])  # e.g., object_3.png → 3
                except Exception as e:
                    print(f"[ERROR] Could not parse temp_object_id from {filename}: {e}")
                    continue
                image_path = os.path.join(IND_IMAGES_DIR, filename)
                food_info = analyze_image_with_openai(image_path)
                item = db.query(FoodItem).filter(FoodItem.temp_object_id == temp_object_id).first()
                if item and food_info:
                    item.name = food_info.get('name', item.name)
                    item.category = food_info.get('category', item.category)
                    item.status = food_info.get('status', item.status)
                    expiry = food_info.get('expiry_date')
                    if expiry:
                        from datetime import datetime
                        try:
                            item.expiry_date = datetime.fromisoformat(expiry)
                        except Exception:
                            item.expiry_date = None
            db.commit()
    finally:
        db.close()

@app.post("/upload/zip")
async def upload_zip(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")
    ZIP_DIR = os.path.join(os.path.dirname(__file__), 'static', 'zips')
    os.makedirs(ZIP_DIR, exist_ok=True)
    file_bytes = await file.read()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"upload_{timestamp}_{file.filename}"
    filepath = os.path.join(ZIP_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(file_bytes)
    # Add background task for processing
    background_tasks.add_task(process_zip_file, filepath)
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

# @app.post("/upload/image")
# async def upload_image(file: UploadFile = File(...)):
#     # Check if file is an image
#     if not file.content_type.startswith('image/'):
#         raise HTTPException(status_code=400, detail="Only image files are allowed")
    
#     # Read the file content
#     file_bytes = await file.read()
#     logging.info(f"[DEBUG] Received image file: {file.filename}, size: {len(file_bytes)} bytes, content_type: {file.content_type}")
    
#     # Save with timestamp prefix
#     timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#     filename = f"rpi_{timestamp}_{file.filename}"
#     filepath = os.path.join(STATIC_IMAGE_DIR, filename)
    
#     # Save the file
#     with open(filepath, 'wb') as f:
#         f.write(file_bytes)
    
#     # Process the image
#     success, response_text = process_image(filepath)
    
#     return {
#         "status": "success" if success else "error",
#         "message": response_text,
#         "filename": filename,
#         "size": len(file_bytes),
#         "url": f"/static/images/{filename}"
#     }

@app.get("/static/ind_images/{filename}")
async def get_ind_image(filename: str):
    ind_images_dir = os.path.join(os.path.dirname(__file__), 'static', 'ind_images')
    image_path = os.path.join(ind_images_dir, filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Image not found: {filename}")
    return FileResponse(image_path)

@app.delete("/fridge/foods/{food_id}")
def delete_food(food_id: int, db: Session = Depends(get_db)):
    food_item = db.query(FoodItem).filter(FoodItem.id == food_id).first()
    if not food_item:
        raise HTTPException(status_code=404, detail="Food item not found")
    db.delete(food_item)
    db.commit()
    return {"status": "success", "message": f"Deleted food item {food_id}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
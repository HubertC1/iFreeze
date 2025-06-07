from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from app.database import get_db, Base, engine
from app.models.database import FoodItem
from datetime import datetime

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Serve the React frontend at /liff
frontend_build_dir = os.path.join(os.path.dirname(__file__), '../liff-frontend/dist')
app.mount("/liff", StaticFiles(directory=frontend_build_dir, html=True), name="liff")

# If there are any references to the web app or API URL, update them to use the ngrok URL
NGROK_URL_BASE = os.getenv('NGROK_URL_BASE', 'http://localhost:8000')
WEBAPP_URL = f'{NGROK_URL_BASE}/liff/'

@app.get("/")
async def root():
    return {"message": "Welcome to iFreeze API"}

@app.get("/fridge/foods")
def get_foods(db: Session = Depends(get_db)):
    foods = db.query(FoodItem).all()
    return [
        {
            "id": food.id,
            "name": food.name,
            "category": food.category,
            "status": food.status,
            "added_date": food.added_date.strftime('%Y-%m-%d'),
            "expiry_date": food.expiry_date.strftime('%Y-%m-%d') if food.expiry_date else None
        }
        for food in foods
    ] 
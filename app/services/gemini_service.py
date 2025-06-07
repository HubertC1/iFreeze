import os
import requests
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Gemini Pro text model
GEMINI_TEXT_MODEL = "gemini-pro"
# Gemini Pro vision model
GEMINI_VISION_MODEL = "gemini-pro-vision"

HEADERS = {"Content-Type": "application/json"}


def get_recipe_from_fridge(fridge_items: list):
    """Call Gemini to generate a recipe based on fridge items."""
    prompt = (
        "You are a smart fridge assistant. Here is a list of foods in the fridge: "
        f"{', '.join(fridge_items)}. "
        "Some of these may be going spoiled. Identify which ones are likely spoiling, and suggest a recipe using as many of those as possible. "
        "Return your answer in this format:\n"
        "Spoiling: <comma separated list>\n"
        "Recipe: <recipe title>\nIngredients: <comma separated list>\nInstructions: <step by step>\n"
    )
    url = f"{GEMINI_API_URL}/{GEMINI_TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(url, json=data)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def analyze_fridge_image(image_bytes: bytes):
    """Call Gemini vision model to analyze a fridge image and extract food info."""
    import base64
    img_b64 = base64.b64encode(image_bytes).decode()
    prompt = (
        "You are a smart fridge camera. Analyze the image and list all visible food items, their estimated quantity, and whether they look fresh, spoiling, or spoiled. "
        "Return your answer as a JSON list of objects with keys: name, quantity, status."
    )
    url = f"{GEMINI_API_URL}/{GEMINI_VISION_MODEL}:generateContent?key={GEMINI_API_KEY}"
    data = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}}
            ]
        }]
    }
    resp = requests.post(url, json=data)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"] 
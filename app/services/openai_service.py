import os
import requests
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o"  # Use gpt-4o for both text and vision

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
}

def get_recipe_from_fridge(fridge_items: list):
    prompt = (
        "You are a smart fridge assistant. Here is a list of foods in the fridge: "
        f"{', '.join(fridge_items)}. "
        "Some of these may be going spoiled. Identify which ones are likely spoiling, and suggest a recipe using as many of those as possible. "
        "Return your answer in this format:\n"
        "Spoiling: <comma separated list>\n"
        "Recipe: <recipe title>\nIngredients: <comma separated list>\nInstructions: <step by step>\n"
    )
    data = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful kitchen assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    resp = requests.post(OPENAI_API_URL, headers=HEADERS, json=data)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def analyze_fridge_image(image_bytes: bytes):
    import base64
    img_b64 = base64.b64encode(image_bytes).decode()
    prompt = (
        "You are a smart fridge camera. Analyze the image and list all visible food items, their estimated quantity, and whether they look fresh, spoiling, or spoiled. "
        "Return your answer as a JSON list of objects with keys: name, quantity, status."
    )
    data = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful kitchen assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }
        ]
    }
    resp = requests.post(OPENAI_API_URL, headers=HEADERS, json=data)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"] 
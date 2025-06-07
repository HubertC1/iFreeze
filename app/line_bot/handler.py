from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, ImageSendMessage, FlexSendMessage
from linebot.exceptions import InvalidSignatureError
from fastapi import HTTPException
import os
from dotenv import load_dotenv
from ..services.fridge_service import get_fridge_status, add_food_item, remove_food_item, get_fridge_contents
from ..database import get_db
import logging
from datetime import datetime

load_dotenv()

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

STATIC_IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images')
os.makedirs(STATIC_IMAGE_DIR, exist_ok=True)

NGROK_URL_BASE = os.getenv('NGROK_URL_BASE', 'http://localhost:8000')
WEBAPP_URL = f"{NGROK_URL_BASE}/liff/"

# Helper to build a food card bubble for Flex Message
def build_food_bubble(food, webapp_url):
    return {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": food["name"], "weight": "bold", "size": "lg", "wrap": True},
                {"type": "text", "text": f"Status: {food['status']}", "size": "md", "color": "#888888", "margin": "md"},
                {"type": "text", "text": f"Category: {food['category']}", "size": "sm", "color": "#aaaaaa", "margin": "sm"},
                {"type": "text", "text": f"Added: {food['added_date']}", "size": "sm", "color": "#aaaaaa", "margin": "sm"},
                {"type": "text", "text": f"Expiry: {food['expiry_date'] or '-'}", "size": "sm", "color": "#aaaaaa", "margin": "sm"},
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "View in Web App",
                        "uri": webapp_url
                    },
                    "style": "primary",
                    "margin": "lg"
                }
            ]
        }
    }

def handle_text_message(event):
    text = event.message.text.lower()
    db = next(get_db())
    try:
        if text == "recipe":
            response = "[DEBUG] Recipe feature is temporarily disabled."
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response)
            )
        elif text.startswith("add "):
            # Format: "add item_name quantity"
            try:
                _, item_name, quantity = text.split()
                add_food_item(item_name, float(quantity), db)
                response = f"✅ Added {quantity} of {item_name} to your fridge!"
            except ValueError:
                response = "❌ Please use format: add item_name quantity"
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response)
            )
        
        elif text.startswith("remove "):
            # Format: "remove item_name"
            try:
                _, item_name = text.split()
                remove_food_item(item_name, db)
                response = f"✅ Removed {item_name} from your fridge!"
            except ValueError:
                response = "❌ Please use format: remove item_name"
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response)
            )
        
        elif text == "status":
            # Get food list for carousel
            from ..models.database import FoodItem
            foods = db.query(FoodItem).all()
            if foods:
                bubbles = [build_food_bubble({
                    "name": f.name,
                    "status": f.status,
                    "category": f.category,
                    "added_date": f.added_date.strftime('%Y-%m-%d'),
                    "expiry_date": f.expiry_date.strftime('%Y-%m-%d') if f.expiry_date else None
                }, WEBAPP_URL) for f in foods[:5]]
                flex_message = FlexSendMessage(
                    alt_text="Fridge Items",
                    contents={
                        "type": "carousel",
                        "contents": bubbles
                    }
                )
            else:
                # No food, show a single card
                flex_message = FlexSendMessage(
                    alt_text="Fridge is empty",
                    contents={
                        "type": "bubble",
                        "body": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {"type": "text", "text": "Fridge is empty!", "weight": "bold", "size": "lg"},
                                {
                                    "type": "button",
                                    "action": {
                                        "type": "uri",
                                        "label": "Open Web App",
                                        "uri": WEBAPP_URL
                                    },
                                    "style": "primary",
                                    "margin": "lg"
                                }
                            ]
                        }
                    }
                )
            line_bot_api.reply_message(event.reply_token, flex_message)
        
        else:
            help_text = """🤖 iFreeze Bot Commands:\n\n- Type \"add item_name quantity\" to add items\n- Type \"remove item_name\" to remove items\n- Type \"status\" to check fridge contents\n- Type \"recipe\" to get a recipe suggestion\n- Type \"help\" to see this message"""
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=help_text)
            )
    finally:
        db.close()

def handle_image_message(event):
    db = next(get_db())
    try:
        message_content = line_bot_api.get_message_content(event.message.id)
        image_bytes = b"".join(chunk for chunk in message_content.iter_content(1024))
        logging.info(f"[DEBUG] Received image of size: {len(image_bytes)} bytes")
        # Save image to static/images with a unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"line_{event.message.id}_{timestamp}.jpg"
        filepath = os.path.join(STATIC_IMAGE_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        response = f"[DEBUG] Image received and saved as: {filepath}"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response)
        )
    finally:
        db.close() 
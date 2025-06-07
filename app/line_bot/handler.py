from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage
from linebot.exceptions import InvalidSignatureError
from fastapi import HTTPException
import os
from dotenv import load_dotenv
from ..services.fridge_service import get_fridge_status, add_food_item, remove_food_item
from ..database import get_db

load_dotenv()

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

def handle_text_message(event):
    text = event.message.text.lower()
    db = next(get_db())
    try:
        if text.startswith("add "):
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
            status = get_fridge_status(db)
            response = "📊 Fridge Status:\n\n" + status
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response)
            )
        
        else:
            help_text = """🤖 iFreeze Bot Commands:
            
- Type \"add item_name quantity\" to add items
- Type \"remove item_name\" to remove items
- Type \"status\" to check fridge contents
- Type \"help\" to see this message"""
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=help_text)
            )
    finally:
        db.close()

def handle_image_message(event):
    # Save the image and process it
    message_content = line_bot_api.get_message_content(event.message.id)
    
    # TODO: Save image and process with YOLO API
    # For now, just acknowledge receipt
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="📸 Image received! Processing your fridge contents...")
    ) 
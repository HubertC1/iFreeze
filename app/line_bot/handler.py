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
import subprocess
import requests

load_dotenv()

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

STATIC_IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images')
os.makedirs(STATIC_IMAGE_DIR, exist_ok=True)

NGROK_URL_BASE = os.getenv('VITE_NGROK_URL_BASE', 'http://localhost:8000')
WEBAPP_URL = f"{NGROK_URL_BASE}/liff/"
PROCESSING_API_BASE = os.getenv('PROCESSING_API_BASE', 'https://2111-103-196-86-108.ngrok-free.app')

def process_image(image_path):
    """Process an image by sending it to the processing API without waiting for response"""
    try:
        print(f"[DEBUG] Starting to process image: {image_path}")
        processing_url = f"{PROCESSING_API_BASE}/process"
        print(f"[DEBUG] Processing URL: {processing_url}")
        
        print("[DEBUG] Opening image file...")
        with open(image_path, 'rb') as image_file:
            print("[DEBUG] File opened successfully")
            files = {'file': image_file}
            print("[DEBUG] Sending POST request to processing API (async)...")
            
            # Send request without waiting for response
            result = requests.post(processing_url, files=files, timeout=1)
            # print("[DEBUG] Request sent successfully")
            print(f"[DEBUG] Response: {result.text}")
            
            return True, "Image sent for processing"
            
    except requests.exceptions.Timeout:
        # Timeout is expected since we're not waiting for response
        print("[DEBUG] Request sent (timeout expected)")
        return True, "Image sent for processing"
    except Exception as e:
        print(f"[DEBUG] Error sending request: {str(e)}")
        return False, f"Failed to send for processing: {str(e)}"

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
        if text == "take photo":
            # Create a trigger file
            trigger_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'triggers')
            os.makedirs(trigger_dir, exist_ok=True)
            trigger_file = os.path.join(trigger_dir, 'take_photo.trigger')
            
            # Create an empty trigger file
            with open(trigger_file, 'w') as f:
                f.write('')
            
            # SCP the trigger file to Raspberry Pi
            try:
                rpi_host = os.getenv('RPI_HOST', 'raspberrypi.local')
                rpi_user = os.getenv('RPI_USER', 'pi')
                rpi_trigger_dir = os.getenv('RPI_TRIGGER_DIR', '/home/team5/ifridge/')
                
                # Create the command
                scp_command = f"scp {trigger_file} {rpi_user}@{rpi_host}:{rpi_trigger_dir}/"
                
                # Execute SCP
                result = subprocess.run(scp_command, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    response = "📸 Photo request sent! Taking a photo..."
                else:
                    response = f"❌ Failed to send photo request: {result.stderr}"
                
                # Remove the local trigger file
                os.remove(trigger_file)
                
            except Exception as e:
                response = f"❌ Error sending photo request: {str(e)}"
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response)
            )
            
        elif text == "recipe":
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
        
        # Process the image
        print(f"[DEBUG] Processing image: {filepath}")
        success, response_text = process_image(filepath)
        print(f"[DEBUG] Image processing result: {success}, Response: {response_text}")
        if not success:
            response_text = f"Image saved but {response_text}"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_text)
        )
    except Exception as e:
        logging.error(f"[ERROR] Error processing image: {str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"❌ Error processing image: {str(e)}")
        )
    finally:
        db.close() 
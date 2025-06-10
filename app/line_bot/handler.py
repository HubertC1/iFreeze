from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, ImageSendMessage, FlexSendMessage, PostbackAction, PostbackEvent
from linebot.exceptions import InvalidSignatureError
from fastapi import HTTPException
import os
from dotenv import load_dotenv
from ..services.fridge_service import get_fridge_status, add_food_item, remove_food_item, get_fridge_contents
from ..services.recipe_service import get_recipe_suggestion
from ..database import get_db
import logging
from datetime import datetime, timedelta
import subprocess
import requests
import json
import time

load_dotenv()

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

STATIC_IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images')
os.makedirs(STATIC_IMAGE_DIR, exist_ok=True)

NGROK_URL_BASE = os.getenv('VITE_NGROK_URL_BASE', 'http://localhost:8000')
WEBAPP_URL = f"{NGROK_URL_BASE}/liff/"
PROCESSING_API_BASE = os.getenv('PROCESSING_API_BASE', 'https://2111-103-196-86-108.ngrok-free.app')

# Dictionary to store selected items for each user
user_selected_items = {}
# Dictionary to store last recipe generation time for each user
last_recipe_generation = {}

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
def build_food_bubble(food, webapp_url, is_selected=False):
    # Define status colors with opacity for background
    status_colors = {
        "spoiled": "#FFE5E5",    # Light red
        "spoiling": "#FFF4E5",   # Light orange
        "fresh": "#E5FFE5"       # Light green
    }
    
    status_color = status_colors.get(food["status"].lower(), "#FFFFFF")
    
    logging.info(f"[DEBUG] Building bubble for food: {food['name']}, id: {food['id']}, is_selected: {is_selected}")
    
    return {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "☑️" if is_selected else "⬜️",
                            "size": "sm",
                            "flex": 1
                        },
                        {
                            "type": "text",
                            "text": food["name"],
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True,
                            "flex": 5
                        }
                    ]
                },
                {"type": "text", "text": f"Status: {food['status']}", "size": "md", "color": "#000000", "margin": "md"},
                {"type": "text", "text": f"Category: {food['category']}", "size": "sm", "color": "#666666", "margin": "sm"},
                {"type": "text", "text": f"Added: {food['added_date']}", "size": "sm", "color": "#666666", "margin": "sm"},
                {"type": "text", "text": f"Expiry: {food['expiry_date'] or '-'}", "size": "sm", "color": "#666666", "margin": "sm"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "lg",
                    "contents": [
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "Select for Recipe",
                                "data": json.dumps({
                                    "action": "toggle_recipe_item",
                                    "item_id": str(food["id"]),  # Convert to string for JSON
                                    "item_name": food["name"]
                                })
                            },
                            "style": "primary",
                            "color": "#27AE60"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "uri",
                                "label": "View in Web App",
                                "uri": webapp_url
                            },
                            "style": "secondary",
                            "margin": "sm"
                        }
                    ]
                }
            ],
            "backgroundColor": status_color
        }
    }

def handle_text_message(event):
    text = event.message.text.lower()
    db = next(get_db())
    try:
        if text == "take photo":
            # Make the curl request to trigger photo
            try:
                rpi_api_base = os.getenv('RPI_API_BASE')
                response = requests.get(f"{rpi_api_base}/trigger-photo")
                if response.status_code == 200:
                    # Wait a moment for the photo to be saved
                    time.sleep(2)
                    
                    # Get the most recent photo from static/images
                    image_files = [f for f in os.listdir(STATIC_IMAGE_DIR) if f.endswith('.jpg')]
                    if image_files:
                        # Sort by modification time (newest first)
                        latest_image = max(image_files, key=lambda x: os.path.getmtime(os.path.join(STATIC_IMAGE_DIR, x)))
                        
                        # Send both text and image messages
                        line_bot_api.reply_message(
                            event.reply_token,
                            [
                                TextSendMessage(text="📸 Photo taken! Here's what I see:"),
                                ImageSendMessage(
                                    original_content_url=f"{NGROK_URL_BASE}/static/images/{latest_image}",
                                    preview_image_url=f"{NGROK_URL_BASE}/static/images/{latest_image}"
                                )
                            ]
                        )
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="📸 Photo request sent! Taking a photo...")
                        )
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"❌ Failed to trigger photo: {response.status_code}")
                    )
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"❌ Error triggering photo: {str(e)}")
                )
            
        elif text == "recipe":
            # Get food list for carousel with selection status
            from ..models.database import FoodItem
            foods = db.query(FoodItem).all()
            if foods:
                # Sort foods by status priority (spoiled -> spoiling -> fresh)
                status_priority = {"spoiled": 0, "spoiling": 1, "fresh": 2}
                sorted_foods = sorted(foods, key=lambda x: status_priority.get(x.status.lower(), 3))
                
                # Get user's selected items
                user_id = event.source.user_id
                selected_items = user_selected_items.get(user_id, set())
                
                bubbles = [build_food_bubble({
                    "id": f.id,
                    "name": f.name,
                    "status": f.status,
                    "category": f.category,
                    "added_date": f.added_date.strftime('%Y-%m-%d'),
                    "expiry_date": f.expiry_date.strftime('%Y-%m-%d') if f.expiry_date else None
                }, WEBAPP_URL, f.id in selected_items) for f in sorted_foods[:5]]
                
                # Add a "Generate Recipe" button at the end with the same size bubble
                bubbles.append({
                    "type": "bubble",
                    "size": "kilo",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"Selected Items: {len(selected_items)}",
                                "weight": "bold",
                                "size": "lg",
                                "margin": "md"
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "postback",
                                    "label": "Generate Recipe with Selected Items",
                                    "data": json.dumps({
                                        "action": "generate_recipe"
                                    })
                                },
                                "style": "primary",
                                "color": "#27AE60",
                                "margin": "lg"
                            }
                        ]
                    }
                })
                
                flex_message = FlexSendMessage(
                    alt_text="Select Items for Recipe",
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
                        "size": "kilo",
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
                # Sort foods by status priority (spoiled -> spoiling -> fresh)
                status_priority = {"spoiled": 0, "spoiling": 1, "fresh": 2}
                sorted_foods = sorted(foods, key=lambda x: status_priority.get(x.status.lower(), 3))
                
                bubbles = [build_food_bubble({
                    "id": f.id,
                    "name": f.name,
                    "status": f.status,
                    "category": f.category,
                    "added_date": f.added_date.strftime('%Y-%m-%d'),
                    "expiry_date": f.expiry_date.strftime('%Y-%m-%d') if f.expiry_date else None
                }, WEBAPP_URL) for f in sorted_foods[:5]]
                
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
            
            try:
                line_bot_api.reply_message(event.reply_token, flex_message)
            except Exception as e:
                logging.error(f"Error sending flex message: {str(e)}")
                # Fallback to text message if flex message fails
                status_text = get_fridge_status(db)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=status_text)
                )
        
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

@handler.add(PostbackEvent)
def handle_postback(event):
    try:
        print("shut the fuck up")
        data = json.loads(event.postback.data)
        action = data.get("action")
        user_id = event.source.user_id
        
        logging.info(f"[DEBUG] Received postback: action={action}, data={data}, user_id={user_id}")
        
        if action == "toggle_recipe_item":
            item_id = int(data.get("item_id"))  # Convert to int since IDs are integers
            item_name = data.get("item_name")
            
            logging.info(f"[DEBUG] Processing toggle_recipe_item: item_id={item_id}, item_name={item_name}")
            
            if not item_id:
                logging.error("[DEBUG] No item_id in postback data")
                return
                
            if user_id not in user_selected_items:
                user_selected_items[user_id] = set()
                logging.info(f"[DEBUG] Created new selection set for user {user_id}")
            
            logging.info(f"[DEBUG] Before toggle - Current selections for user {user_id}: {user_selected_items[user_id]}")
            
            if item_id in user_selected_items[user_id]:
                user_selected_items[user_id].remove(item_id)
                logging.info(f"[DEBUG] Removed item {item_id} ({item_name}) from selections")
            else:
                user_selected_items[user_id].add(item_id)
                logging.info(f"[DEBUG] Added item {item_id} ({item_name}) to selections")
            
            logging.info(f"[DEBUG] After toggle - Current selections for user {user_id}: {user_selected_items[user_id]}")
            
            # Send updated carousel
            db = next(get_db())
            try:
                from ..models.database import FoodItem
                foods = db.query(FoodItem).all()
                status_priority = {"spoiled": 0, "spoiling": 1, "fresh": 2}
                sorted_foods = sorted(foods, key=lambda x: status_priority.get(x.status.lower(), 3))
                
                logging.info(f"[DEBUG] Building carousel with {len(sorted_foods)} items")
                
                bubbles = [build_food_bubble({
                    "id": f.id,
                    "name": f.name,
                    "status": f.status,
                    "category": f.category,
                    "added_date": f.added_date.strftime('%Y-%m-%d'),
                    "expiry_date": f.expiry_date.strftime('%Y-%m-%d') if f.expiry_date else None
                }, WEBAPP_URL, f.id in user_selected_items[user_id]) for f in sorted_foods[:5]]
                
                logging.info(f"[DEBUG] Built {len(bubbles)} bubbles, selection states: {[f.id in user_selected_items[user_id] for f in sorted_foods[:5]]}")
                
                # Add Generate Recipe button
                bubbles.append({
                    "type": "bubble",
                    "size": "kilo",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"Selected Items: {len(user_selected_items[user_id])}",
                                "weight": "bold",
                                "size": "lg",
                                "margin": "md"
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "postback",
                                    "label": "Generate Recipe with Selected Items",
                                    "data": json.dumps({
                                        "action": "generate_recipe"
                                    })
                                },
                                "style": "primary",
                                "color": "#27AE60",
                                "margin": "lg"
                            }
                        ]
                    }
                })
                
                flex_message = FlexSendMessage(
                    alt_text="Select Items for Recipe",
                    contents={
                        "type": "carousel",
                        "contents": bubbles
                    }
                )
                line_bot_api.reply_message(event.reply_token, flex_message)
                logging.info("[DEBUG] Sent updated carousel")
            finally:
                db.close()
            
        elif action == "generate_recipe":
            if not user_selected_items.get(user_id):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="Please select at least one item for the recipe!")
                )
                return
                
            db = next(get_db())
            try:
                from ..models.database import FoodItem
                selected_foods = db.query(FoodItem).filter(FoodItem.id.in_(user_selected_items[user_id])).all()
                
                logging.info(f"[DEBUG] Generating recipe for user {user_id} with items: {[f.name for f in selected_foods]}")
                
                recipe = get_recipe_suggestion(db, selected_foods)
                
                # Clear selections after generating recipe
                user_selected_items[user_id] = set()
                
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=recipe)
                )
            finally:
                db.close()
    except Exception as e:
        logging.error(f"[DEBUG] Error in postback handler: {str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"Sorry, there was an error processing your request: {str(e)}")
        ) 
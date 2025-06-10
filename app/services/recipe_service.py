import aiohttp
import os
from dotenv import load_dotenv
from ..schemas.schemas import RecipeSuggestion
from ..database import get_db
from sqlalchemy.orm import Session
from ..models.database import FoodItem
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def get_recipe_suggestion(db: Session, selected_foods=None) -> str:
    """Get a recipe suggestion based on selected ingredients in the fridge"""
    if not selected_foods:
        return "Please select at least one item for the recipe!"
    
    # Sort foods by status priority (spoiled -> spoiling -> fresh)
    status_priority = {"spoiled": 0, "spoiling": 1, "fresh": 2}
    sorted_foods = sorted(selected_foods, key=lambda x: status_priority.get(x.status.lower(), 3))
    
    # Create a list of available ingredients with status indicators
    ingredients = []
    for food in sorted_foods:
        status = food.status.lower()
        if status == "spoiled":
            ingredients.append(f"⚠️ {food.name} - SPOILED")
        elif status == "spoiling":
            ingredients.append(f"⚠️ {food.name} - SPOILING")
        else:
            ingredients.append(food.name)
    
    ingredients_text = "\n".join(ingredients)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    try:
        response = client.responses.create(
            model="gpt-3.5-turbo",
            input=[
                {"role": "user", "content": f"""Based on the following selected ingredients, suggest a recipe I can make. 
Please prioritize using the items marked with ⚠️ (spoiled or spoiling) first:

{ingredients_text}

Please provide:
1. Recipe name
2. List of ingredients needed (including what I have and what I need to buy)
3. Step-by-step instructions
4. Estimated cooking time
5. Difficulty level

Format the response in a clear, easy-to-read way. Make sure to use the items that are about to spoil first!"""}
            ]
        )
        return response.output_text
    except Exception as e:
        return f"Sorry, I couldn't generate a recipe suggestion at the moment. Error: {str(e)}" 
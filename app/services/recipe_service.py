import aiohttp
import os
from dotenv import load_dotenv
from ..schemas.schemas import RecipeSuggestion
from ..database import get_db
from sqlalchemy.orm import Session

load_dotenv()

LLM_API_URL = os.getenv('LLM_API_URL')

async def get_recipe_suggestion(db: Session = next(get_db())) -> RecipeSuggestion:
    # Get current fridge contents
    from .fridge_service import get_fridge_contents
    ingredients = get_fridge_contents(db)
    
    # Call LLM API to get recipe suggestion
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{LLM_API_URL}/generate_recipe",
            json={"ingredients": ingredients}
        ) as response:
            if response.status == 200:
                recipe_data = await response.json()
                return RecipeSuggestion(**recipe_data)
            else:
                # Fallback to a default recipe if API fails
                return RecipeSuggestion(
                    title="Simple Stir Fry",
                    ingredients=["Any vegetables in your fridge", "Soy sauce", "Oil"],
                    instructions=[
                        "Cut vegetables into bite-sized pieces",
                        "Heat oil in a pan",
                        "Stir fry vegetables until tender",
                        "Add soy sauce to taste"
                    ],
                    estimated_time="15 minutes",
                    difficulty="Easy"
                ) 
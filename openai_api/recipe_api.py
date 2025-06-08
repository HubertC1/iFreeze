from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import openai
import os
import json

app = FastAPI()

# Set your OpenAI API key here or use environment variable
api_key = os.getenv('OPENAI_API_KEY')
client = openai.OpenAI(api_key=api_key)

class IngredientsRequest(BaseModel):
    ingredients: List[str]

class RecipeSummaryResponse(BaseModel):
    title: str
    url: str
    summary: str
    ingredients: List[str]
    instructions: str

# Define structured output schema for OpenAI
recipe_schema = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "The title of the recipe"
        },
        "url": {
            "type": "string",
            "description": "URL to the recipe source or 'N/A' if not available"
        },
        "summary": {
            "type": "string",
            "description": "A brief summary of the recipe"
        },
        "ingredients": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of ingredients needed for the recipe"
        },
        "instructions": {
            "type": "string",
            "description": "Step-by-step cooking instructions"
        }
    },
    "required": ["title", "url", "summary", "ingredients", "instructions"],
    "additionalProperties": False
}

def find_recipe_with_web_search(ingredients: List[str]):
    response = client.chat.completions.create(
        model="gpt-4o-search-preview",
        web_search_options={},
        messages=[
            {"role": "system", "content": "You are a helpful assistant that finds recipes based on given ingredients. You must return structured JSON data."},
            {"role": "user", "content": f"Find a recipe that uses these ingredients: {', '.join(ingredients)} from the website. Create a recipe with title, URL (use 'N/A' if not from a specific source), summary, complete ingredient list, and detailed instructions."}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "recipe_response",
                "schema": recipe_schema
            }
        }
    )
    
    # Parse the structured JSON response
    content = response.choices[0].message.content
    recipe_data = json.loads(content)
    
    return recipe_data

@app.post("/find_recipe", response_model=RecipeSummaryResponse)
def find_recipe(request: IngredientsRequest):
    try:
        recipe = find_recipe_with_web_search(request.ingredients)
        return RecipeSummaryResponse(
            title=recipe['title'],
            url=recipe['url'],
            summary=recipe['summary'],
            ingredients=recipe['ingredients'],
            instructions=recipe['instructions']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("recipe_api:app", host="0.0.0.0", port=8000, reload=True) 
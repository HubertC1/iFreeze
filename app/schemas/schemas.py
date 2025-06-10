from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class FoodItemBase(BaseModel):
    name: str
    category: str
    expiry_date: Optional[datetime] = None
    status: str

class FoodItemCreate(FoodItemBase):
    pass

class FoodItem(FoodItemBase):
    id: int
    added_date: datetime

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    line_user_id: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    last_interaction: datetime

    class Config:
        from_attributes = True

class RecipeSuggestion(BaseModel):
    title: str
    ingredients: List[str]
    instructions: List[str]
    estimated_time: str
    difficulty: str 
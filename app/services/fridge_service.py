from sqlalchemy.orm import Session
from ..models.database import FoodItem
from datetime import datetime, timedelta
from ..database import get_db

def get_fridge_contents(db: Session):
    """Get all non-spoiled food items in the fridge"""
    foods = db.query(FoodItem).filter(FoodItem.status != 'spoiled').all()
    return [food.name for food in foods]

def get_fridge_status(db: Session) -> str:
    """Get a formatted status of the fridge contents"""
    entries = db.query(FoodItem).all()
    
    if not entries:
        return "Your fridge is empty! 🧊"
    
    # Sort entries by status priority (spoiled -> spoiling -> fresh)
    status_priority = {"spoiled": 0, "spoiling": 1, "fresh": 2}
    sorted_entries = sorted(entries, key=lambda x: status_priority.get(x.status.lower(), 3))
    
    status_lines = []
    for entry in sorted_entries:
        status = entry.status.lower()
        if status == "spoiled":
            emoji = "🔴"
        elif status == "spoiling":
            emoji = "🟡"
        else:
            emoji = "🟢"
        status_lines.append(f"{emoji} {entry.name} - {entry.status}")
    
    return "Fridge Contents:\n" + "\n".join(status_lines)

def add_food_item(name: str, quantity: float, db: Session = next(get_db())):
    """Add a new food item to the fridge"""
    food_item = db.query(FoodItem).filter(FoodItem.name == name).first()
    if not food_item:
        food_item = FoodItem(
            name=name,
            category="other",
            status="fresh",
            expiry_date=datetime.utcnow() + timedelta(days=7)
        )
        db.add(food_item)
        db.commit()
    return food_item

def remove_food_item(name: str, db: Session = next(get_db())):
    """Remove a food item from the fridge"""
    food_item = db.query(FoodItem).filter(FoodItem.name == name).first()
    if food_item:
        db.delete(food_item)
        db.commit()
        return True
    return False

def update_fridge_from_gemini(food_list, db: Session):
    for item in food_list:
        name = item.get("name")
        status = item.get("status", "fresh")
        food_item = db.query(FoodItem).filter(FoodItem.name == name).first()
        if not food_item:
            food_item = FoodItem(
                name=name,
                category="other",
                status=status,
                expiry_date=datetime.utcnow() + timedelta(days=7)
            )
            db.add(food_item)
        else:
            food_item.status = status
    db.commit()

def check_spoilage(db: Session):
    """Check for items that might be spoiling soon"""
    foods = db.query(FoodItem).filter(FoodItem.status == "spoiling").all()
    return [food.name for food in foods] 
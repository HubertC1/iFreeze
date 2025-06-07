from sqlalchemy.orm import Session
from ..models.database import FoodItem, FridgeEntry
from datetime import datetime, timedelta
from ..database import get_db

def get_fridge_contents(db: Session):
    """Get all non-spoiled food items in the fridge"""
    entries = db.query(FridgeEntry).join(FridgeEntry.food_item).filter(
        FridgeEntry.is_spoiled == False
    ).all()
    
    return [entry.food_item.name for entry in entries]

def get_fridge_status(db: Session) -> str:
    """Get a formatted status of the fridge contents"""
    entries = db.query(FridgeEntry).join(FridgeEntry.food_item).all()
    
    if not entries:
        return "Your fridge is empty! 🧊"
    
    status_lines = []
    for entry in entries:
        status = "🟢" if not entry.is_spoiled else "🔴"
        status_lines.append(f"{status} {entry.food_item.name} ({entry.quantity})")
    
    return "\n".join(status_lines)

def add_food_item(name: str, quantity: float, db: Session = next(get_db())):
    """Add a new food item to the fridge"""
    # Check if food item exists
    food_item = db.query(FoodItem).filter(FoodItem.name == name).first()
    
    if not food_item:
        # Create new food item
        food_item = FoodItem(
            name=name,
            category="other",  # Default category
            status="fresh",
            expiry_date=datetime.utcnow() + timedelta(days=7)  # Default expiry: 7 days
        )
        db.add(food_item)
        db.flush()
    
    # Create new fridge entry
    entry = FridgeEntry(
        food_item_id=food_item.id,
        quantity=quantity,
        is_spoiled=False
    )
    db.add(entry)
    db.commit()

def remove_food_item(name: str, db: Session = next(get_db())):
    """Remove a food item from the fridge"""
    food_item = db.query(FoodItem).filter(FoodItem.name == name).first()
    if food_item:
        # Remove all entries for this food item
        db.query(FridgeEntry).filter(FridgeEntry.food_item_id == food_item.id).delete()
        db.commit()
        return True
    return False

def update_fridge_from_gemini(food_list, db: Session):
    for item in food_list:
        name = item.get("name")
        quantity = float(item.get("quantity", 1))
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
            db.flush()
        else:
            food_item.status = status
        entry = FridgeEntry(
            food_item_id=food_item.id,
            quantity=quantity,
            is_spoiled=(status == "spoiled")
        )
        db.add(entry)
    db.commit()

def check_spoilage(db: Session):
    """Check for items that might be spoiling soon"""
    entries = db.query(FridgeEntry).join(FridgeEntry.food_item).filter(
        FridgeEntry.is_spoiled == False
    ).all()
    
    spoiling_items = []
    for entry in entries:
        if entry.food_item.status == "spoiling":
            spoiling_items.append(entry.food_item.name)
    
    return spoiling_items 
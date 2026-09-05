import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gym_store.db")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "store_config.json")
BILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bills")
ORDERS_DB_FILE = os.path.join(BILLS_DIR, "active_orders.json")

class StoreConfig(BaseModel):
    store_name: str = "Sauda AI Storefront"
    agent_name: str = "Rohan"
    agent_tone: str = "Persuasive, Energetic & Friendly"
    active_coupon: str = "FIT10"
    discount_percentage: float = 10.0
    free_gift_threshold: float = 1999.0
    free_gift_name: str = "MuscleBlaze Premium Shaker Bottle (Free)"
    active_offers: List[str] = [
        "Coupon Code 'FIT10': Instant 10% discount on all orders.",
        "Free Shaker bottle on orders above ₹1,999.",
        "Combo deal: Whey + Creatine saves ₹300."
    ]
    knowledge_specs: str = "MuscleBlaze Biozyme Whey is Labdoor USA certified for accuracy and purity, providing 50% higher protein absorption."

def get_store_config() -> StoreConfig:
    """Fetch current merchant store & agent configuration."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return StoreConfig(**data)
        except Exception:
            pass
    config = StoreConfig()
    save_store_config(config)
    return config

def save_store_config(config: StoreConfig):
    """Save merchant store & agent configuration to persistent JSON."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)

def get_all_merchant_products() -> List[Dict[str, Any]]:
    """Fetch complete product catalog for merchant CRUD view."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, category, flavour, price_inr, stock_count, rating, description FROM products ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    
    products = []
    from api_server import PRODUCT_IMAGES
    for r in rows:
        pid = r[0]
        products.append({
            "id": pid,
            "name": r[1],
            "category": r[2],
            "flavour": r[3],
            "price_inr": float(r[4]),
            "stock_count": int(r[5]),
            "rating": float(r[6]),
            "description": r[7],
            "image_url": PRODUCT_IMAGES.get(pid, "https://images.unsplash.com/photo-1579722821273-0f6c7d44362f?auto=format&fit=crop&w=600&q=80")
        })
    return products

def add_merchant_product(
    name: str,
    category: str,
    flavour: str,
    price_inr: float,
    stock_count: int,
    rating: float = 4.8,
    description: str = "",
    image_url: str = ""
) -> Dict[str, Any]:
    """Add a new product to SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO products (name, category, flavour, price_inr, stock_count, rating, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, category, flavour, price_inr, stock_count, rating, description))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    if image_url:
        from api_server import PRODUCT_IMAGES
        PRODUCT_IMAGES[new_id] = image_url
        
    print(f"📦 [MERCHANT PRODUCT ADDED] ID #{new_id}: {name} (₹{price_inr})")
    return {
        "status": "success",
        "id": new_id,
        "name": name,
        "message": f"Product '{name}' added to catalog successfully."
    }

def update_merchant_product(
    product_id: int,
    name: str,
    category: str,
    flavour: str,
    price_inr: float,
    stock_count: int,
    rating: float = 4.8,
    description: str = "",
    image_url: str = ""
) -> Dict[str, Any]:
    """Update existing product details in SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE products 
    SET name = ?, category = ?, flavour = ?, price_inr = ?, stock_count = ?, rating = ?, description = ?
    WHERE id = ?
    """, (name, category, flavour, price_inr, stock_count, rating, description, product_id))
    conn.commit()
    conn.close()
    
    if image_url:
        from api_server import PRODUCT_IMAGES
        PRODUCT_IMAGES[product_id] = image_url
        
    print(f"✏️ [MERCHANT PRODUCT UPDATED] ID #{product_id}: {name} (₹{price_inr})")
    return {
        "status": "success",
        "id": product_id,
        "message": f"Product #{product_id} updated successfully."
    }

def delete_merchant_product(product_id: int) -> Dict[str, Any]:
    """Delete product from SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    
    print(f"🗑️ [MERCHANT PRODUCT DELETED] ID #{product_id}")
    return {
        "status": "success",
        "id": product_id,
        "message": f"Product #{product_id} removed from catalog."
    }

def get_merchant_orders_ledger() -> List[Dict[str, Any]]:
    """Fetch live incoming orders ledger for merchant dashboard."""
    if not os.path.exists(ORDERS_DB_FILE):
        return []
    try:
        with open(ORDERS_DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            orders = list(data.values())
            orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return orders
    except Exception:
        return []

import os
import json
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gym_store.db")

GOAL_KEYWORD_MAP = {
    "lean": ["Isolate"],
    "fat loss": ["Isolate"],
    "weight gain": ["Super Gainer"],
    "weight increase": ["Super Gainer"],
    "gain weight": ["Super Gainer"],
    "bulk": ["Super Gainer"],
    "strength": ["Creatine"],
    "energy": ["WrathX"],
    "muscle": ["Biozyme"],
    "lactose": ["Isolate"],
    "lactose sensitivity": ["Isolate"],
    "lactose free": ["Isolate"],
    "लैकोस्ट": ["Isolate"],
    "सेंसिविटी": ["Isolate"],
    "लैक्टोज": ["Isolate"]
}

def search_gym_products(query: str = "", category: str = "", max_price: int = 0, limit: int = 1) -> str:
    """Search for gym products/supplements in SQLite database with compact payload."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    sql = "SELECT id, name, category, flavour, price_inr, stock_count, rating, description FROM products WHERE 1=1"
    params = []
    
    # Check if query matches a fitness goal alias
    q_lower = query.lower().strip()
    matched_goal_keywords = []
    is_goal_search = False
    for goal_key, keywords in GOAL_KEYWORD_MAP.items():
        if goal_key in q_lower:
            matched_goal_keywords.extend(keywords)
            is_goal_search = True
            break # Match top priority goal
            
    if matched_goal_keywords:
        or_clauses = " OR ".join(["name LIKE ? OR description LIKE ? OR category LIKE ?" for _ in matched_goal_keywords])
        sql += f" AND ({or_clauses})"
        for kw in matched_goal_keywords:
            params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
    elif query:
        words = query.strip().split()
        for word in words:
            if word.lower() in ['protein', 'price', 'rate', 'cost', 'stock']:
                continue
            sql += " AND (name LIKE ? OR description LIKE ? OR category LIKE ?)"
            params.extend([f"%{word}%", f"%{word}%", f"%{word}%"])
            
    if category:
        sql += " AND category LIKE ?"
        params.append(f"%{category}%")
    if max_price > 0:
        sql += " AND price_inr <= ?"
        params.append(max_price)
        
    actual_limit = 1 if is_goal_search else (limit if limit > 0 else 1)
    sql += f" LIMIT {actual_limit}"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "No matching products found."
        
    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "name": r[1],
            "category": r[2],
            "flavour": r[3],
            "price_inr": r[4],
            "price": f"₹{r[4]}",
            "stock_count": r[5],
            "stock": r[5],
            "rating": r[6],
            "description": r[7]
        })
    return json.dumps(results, ensure_ascii=False)

# Ultra-lean schema for token optimization
DB_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_gym_products",
        "description": "Search gym products by name, category, or fitness goal (e.g. 'lean body', 'weight gain', 'strength', 'Biozyme').",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords or goal (e.g. 'lean body', 'weight gain', 'Biozyme', 'Creatine')"},
                "category": {"type": "string", "description": "Category"},
                "max_price": {"type": "integer", "description": "Max price"}
            }
        }
    }
}

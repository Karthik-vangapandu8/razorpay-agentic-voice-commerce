import os
import json
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gym_store.db")

def search_gym_products(query: str = "", category: str = "", max_price: int = 0) -> str:
    """Search for gym products/supplements in SQLite database with compact payload."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    sql = "SELECT name, category, flavour, price_inr, stock_count, rating FROM products WHERE 1=1"
    params = []
    
    if query:
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
        
    sql += " LIMIT 4"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "No matching products found."
        
    results = []
    for r in rows:
        results.append({
            "name": r[0],
            "price": f"₹{r[3]}",
            "stock": r[4],
            "flavour": r[2],
            "rating": r[5]
        })
    return json.dumps(results, ensure_ascii=False)

# Ultra-lean schema for token optimization
DB_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_gym_products",
        "description": "Search gym products, whey, creatine, price, stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords (e.g. 'Biozyme', 'Creatine')"},
                "category": {"type": "string", "description": "Category"},
                "max_price": {"type": "integer", "description": "Max price"}
            }
        }
    }
}

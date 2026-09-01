import sqlite3

DB_PATH = "gym_store.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        flavour TEXT NOT NULL,
        price_inr INTEGER NOT NULL,
        stock_count INTEGER NOT NULL,
        rating REAL NOT NULL,
        description TEXT NOT NULL
    )
    """)
    
    # Clear existing data for fresh seed
    cursor.execute("DELETE FROM products")
    
    # Seed MuscleBlaze-style gym products
    products = [
        (
            "MuscleBlaze Biozyme Performance Whey 2kg",
            "Whey Protein",
            "Rich Milk Chocolate",
            4499,
            35,
            4.8,
            "Labdoor USA certified. 25g protein per scoop, 50% higher protein absorption."
        ),
        (
            "MuscleBlaze Raw Whey Isolate 1kg",
            "Whey Isolate",
            "Unflavored",
            2299,
            20,
            4.6,
            "90% pure whey protein isolate per serving. Zero added sugar, low carb."
        ),
        (
            "MuscleBlaze Creatine Monohydrate 250g",
            "Creatine",
            "Unflavored",
            999,
            50,
            4.9,
            "100% pure micronized creatine monohydrate for strength, power, and muscle volume."
        ),
        (
            "MuscleBlaze Pre-Workout WrathX 300g",
            "Pre-Workout",
            "Fruit Punch",
            1499,
            15,
            4.5,
            "Explosive energy and laser focus with L-Citrulline, Caffeine, and Beta-Alanine."
        ),
        (
            "MuscleBlaze Super Gainer XXL 3kg",
            "Mass Gainer",
            "Chocolate",
            2899,
            8,
            4.4,
            "High calorie mass gainer with 22.5g protein and 112g carbs for heavy bulk."
        ),
        (
            "MuscleBlaze High Protein Peanut Butter 1kg",
            "Healthy Foods",
            "Dark Chocolate Crunchy",
            599,
            60,
            4.7,
            "30g protein per 100g. Made with roasted peanuts and premium whey protein."
        ),
        (
            "MuscleBlaze Fish Oil 1000mg (60 Capsules)",
            "Vitamins & Omega",
            "Unflavored",
            499,
            40,
            4.7,
            "Rich in EPA & DHA omega 3 fatty acids for joint and heart health."
        ),
        (
            "MuscleBlaze MB-VITE Multivitamin (120 Tablets)",
            "Vitamins & Omega",
            "Unflavored",
            799,
            30,
            4.8,
            "Essential 25 vitamins and minerals with amino acid blend for immunity."
        )
    ]
    
    cursor.executemany("""
    INSERT INTO products (name, category, flavour, price_inr, stock_count, rating, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, products)
    
    conn.commit()
    conn.close()
    print("✅ Gym Store Database initialized successfully with 8 MuscleBlaze products!")

if __name__ == "__main__":
    init_db()

import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Product, Store, Sale, Inventory
from app.database import SessionLocal, Base, engine

# Data definitions
PRODUCTS = [
    # Carbonated Drinks
    {"id": "BEV-001", "name": "Cola Blast 330ml", "brand": "ColaBlast", "cat": "Carbonated Drinks", "sub": "Cola", "ml": 330, "price": 1.50},
    {"id": "BEV-002", "name": "Cola Blast Diet 330ml", "brand": "ColaBlast", "cat": "Carbonated Drinks", "sub": "Cola", "ml": 330, "price": 1.60},
    {"id": "BEV-003", "name": "Lemonade Fizz 500ml", "brand": "FizzCo", "cat": "Carbonated Drinks", "sub": "Lemon Soda", "ml": 500, "price": 1.75},
    {"id": "BEV-004", "name": "Ginger Fizz 500ml", "brand": "FizzCo", "cat": "Carbonated Drinks", "sub": "Ginger Ale", "ml": 500, "price": 1.80},
    # Juice
    {"id": "BEV-005", "name": "Citrus Premium Orange 1L", "brand": "CitrusPremium", "cat": "Juice", "sub": "Fruit Juice", "ml": 1000, "price": 3.50},
    {"id": "BEV-006", "name": "Apple Orchard Juice 1L", "brand": "AppleOrchard", "cat": "Juice", "sub": "Fruit Juice", "ml": 1000, "price": 3.20},
    {"id": "BEV-007", "name": "Berry Splash Cranberry 1L", "brand": "BerrySplash", "cat": "Juice", "sub": "Fruit Juice", "ml": 1000, "price": 4.00},
    {"id": "BEV-008", "name": "Mango Heaven Pulp 500ml", "brand": "MangoHeaven", "cat": "Juice", "sub": "Nectar", "ml": 500, "price": 2.50},
    # Water
    {"id": "BEV-009", "name": "Aquaflow Springs Still 500ml", "brand": "Aquaflow", "cat": "Water", "sub": "Still Water", "ml": 500, "price": 1.00},
    {"id": "BEV-010", "name": "Aquaflow Sparkling Mineral 750ml", "brand": "Aquaflow", "cat": "Water", "sub": "Sparkling Water", "ml": 750, "price": 2.00},
    {"id": "BEV-011", "name": "CocoPure Coconut Water 330ml", "brand": "CocoPure", "cat": "Water", "sub": "Coconut Water", "ml": 330, "price": 2.20},
    {"id": "BEV-012", "name": "HydroPlus Alkaline Water 1L", "brand": "HydroPlus", "cat": "Water", "sub": "Alkaline Water", "ml": 1000, "price": 2.50},
    # Energy Drinks
    {"id": "BEV-013", "name": "PowerGrid Red Energy 250ml", "brand": "PowerGrid", "cat": "Energy Drinks", "sub": "Energy Drink", "ml": 250, "price": 2.50},
    {"id": "BEV-014", "name": "PowerGrid Zero Sugar 250ml", "brand": "PowerGrid", "cat": "Energy Drinks", "sub": "Energy Drink", "ml": 250, "price": 2.70},
    {"id": "BEV-015", "name": "Electrolyte Plus Sports 500ml", "brand": "ElectroPlus", "cat": "Energy Drinks", "sub": "Sports Drink", "ml": 500, "price": 2.10},
    {"id": "BEV-016", "name": "JavaBoost Coffee Blend 250ml", "brand": "JavaBoost", "cat": "Energy Drinks", "sub": "Coffee Blend", "ml": 250, "price": 3.00},
    # Dairy Beverages
    {"id": "BEV-017", "name": "DairyFresh Chocolate Milk 250ml", "brand": "DairyFresh", "cat": "Dairy Beverages", "sub": "Flavored Milk", "ml": 250, "price": 1.75},
    {"id": "BEV-018", "name": "DairyFresh Strawberry Shake 330ml", "brand": "DairyFresh", "cat": "Dairy Beverages", "sub": "Milkshake", "ml": 330, "price": 2.25},
    {"id": "BEV-019", "name": "LatteFresh Cold Brew Milk 250ml", "brand": "LatteFresh", "cat": "Dairy Beverages", "sub": "Cold Brew", "ml": 250, "price": 2.50},
    {"id": "BEV-020", "name": "YogoActive Greek Yogurt 330ml", "brand": "YogoActive", "cat": "Dairy Beverages", "sub": "Yogurt Drink", "ml": 330, "price": 2.80}
]

REGIONS = ["North", "South", "East", "West"]
FORMATS = ["Supermarket", "Hypermarket", "Convenience", "Wholesale"]

CITIES = {
    "North": ["Chicago", "Detroit", "Minneapolis", "Milwaukee"],
    "South": ["Houston", "Atlanta", "Miami", "Dallas"],
    "East": ["New York", "Boston", "Philadelphia", "Pittsburgh"],
    "West": ["Los Angeles", "San Francisco", "Seattle", "Denver"]
}

def generate_stores():
    stores = []
    store_counter = 1
    # Generate 10 stores per region = 40 stores
    for region in REGIONS:
        for idx in range(10):
            store_id = f"STR-{store_counter:03d}"
            # Evenly distribute formats
            store_format = FORMATS[idx % len(FORMATS)]
            city = random.choice(CITIES[region])
            store_name = f"{store_format} {city} #{store_counter}"
            stores.append({
                "store_id": store_id,
                "store_name": store_name,
                "region": region,
                "city": city,
                "store_format": store_format
            })
            store_counter += 1
    return stores

def seed_database(db: Session):
    # Set seed for repeatability
    random.seed(42)
    
    # 1. Create Tables if not exist
    Base.metadata.create_all(bind=engine)
    
    # Check if database is already seeded
    if db.query(Product).count() > 0:
        print("Database already seeded. Skipping...")
        return
        
    print("Seeding Products...")
    db_products = []
    for p in PRODUCTS:
        db_p = Product(
            product_id=p["id"],
            product_name=p["name"],
            brand=p["brand"],
            category=p["cat"],
            sub_category=p["sub"],
            pack_size_ml=p["ml"],
            unit_price=p["price"]
        )
        db.add(db_p)
        db_products.append(db_p)
        
    print("Seeding Stores...")
    stores_data = generate_stores()
    db_stores = []
    for s in stores_data:
        db_s = Store(
            store_id=s["store_id"],
            store_name=s["store_name"],
            region=s["region"],
            city=s["city"],
            store_format=s["store_format"]
        )
        db.add(db_s)
        db_stores.append(db_s)
    
    db.commit()

    print("Generating weekly sales and inventory (24 weeks)...")
    start_date = datetime.strptime("2024-01-01", "%Y-%m-%d").date()
    weeks = [start_date + timedelta(weeks=i) for i in range(24)]

    # Store product state to maintain inventory sequence
    # {(store_id, product_id): current_closing_stock}
    inventory_state = {}

    sales_records = []
    inventory_records = []

    # Pre-calculate baseline sales per product/store combination to ensure coherence
    base_sales_cache = {}
    for s in db_stores:
        for p in db_products:
            # Sales base by store format
            if s.store_format == "Wholesale":
                format_base = random.randint(100, 220)
            elif s.store_format == "Hypermarket":
                format_base = random.randint(70, 140)
            elif s.store_format == "Supermarket":
                format_base = random.randint(40, 90)
            else: # Convenience
                format_base = random.randint(10, 35)
                
            # Adjust base by product popularity/pricing (expensive products sell slightly less)
            price_factor = 2.0 / p.unit_price  # higher price -> lower baseline units
            product_factor = random.uniform(0.8, 1.2) * price_factor
            
            base_sales_cache[(s.store_id, p.product_id)] = max(5, int(format_base * product_factor))

    # Loop over weeks
    for week_idx, week in enumerate(weeks):
        print(f"Generating week {week_idx + 1}/24: {week}")
        for s in db_stores:
            for p in db_products:
                base_sales = base_sales_cache[(s.store_id, p.product_id)]
                
                # Seasonality: Soda/Water sells 15% more in summer weeks (weeks 16-24)
                season_lift = 1.0
                if week_idx >= 15 and p.category in ["Carbonated Drinks", "Water", "Energy Drinks"]:
                    season_lift = 1.15
                
                # Weekly variation
                weekly_noise = random.uniform(0.85, 1.15)
                
                # Check for Promotion
                # ~15% chance of promotion for a product at a store in a given week
                promotion_flag = random.random() < 0.15
                promotion_type = None
                discount_pct = 0.0
                promo_lift = 1.0
                
                if promotion_flag:
                    promotion_type = random.choice(["Price Cut", "BOGO", "Bundle", "Display Feature"])
                    if promotion_type == "Price Cut":
                        discount_pct = random.choice([0.10, 0.15, 0.20, 0.25])
                        promo_lift = random.uniform(1.25, 1.45) # 25-45% lift
                    elif promotion_type == "BOGO":
                        discount_pct = 0.50  # BOGO is effectively 50% discount on total units
                        promo_lift = random.uniform(1.45, 1.60) # 45-60% lift (highly attractive)
                    elif promotion_type == "Bundle":
                        discount_pct = random.choice([0.15, 0.20])
                        promo_lift = random.uniform(1.20, 1.35) # 20-35% lift
                    else: # Display Feature
                        discount_pct = random.choice([0.05, 0.10])
                        promo_lift = random.uniform(1.20, 1.30) # 20-30% lift
                
                # Calculate target units sold before inventory check
                units_demanded = int(base_sales * season_lift * weekly_noise * promo_lift)
                if units_demanded < 1:
                    units_demanded = 1
                
                # Inventory tracking
                state_key = (s.store_id, p.product_id)
                if week_idx == 0:
                    # Initial week: set opening stock high to prevent immediate stockouts
                    opening_stock = base_sales * 3
                else:
                    opening_stock = inventory_state[state_key]
                
                # Determine units received
                # Store manager orders to restock up to target levels: target = base_sales * 2.5
                target_stock = int(base_sales * 2.5)
                expected_restock = max(0, target_stock - opening_stock)
                
                # Occasional supply chain disruption (2% chance) or normal delivery variation
                disruption_flag = random.random() < 0.02
                if disruption_flag:
                    units_received = int(expected_restock * 0.1)  # Only receive 10% of order
                else:
                    units_received = int(expected_restock * random.uniform(0.9, 1.1))
                
                available_inventory = opening_stock + units_received
                
                # Check for stockout
                stockout_flag = False
                units_sold = units_demanded
                
                if units_demanded >= available_inventory:
                    # Stockout happens! Demand exceeds or equals available stock
                    units_sold = available_inventory
                    closing_stock = 0
                    stockout_flag = True
                else:
                    closing_stock = available_inventory - units_sold
                    # Occasional stockout due to high daily spikes (even if weekly closing > 0)
                    # Let's say if closing stock is less than 10% of base sales, 20% chance of stockout flag
                    if closing_stock < (base_sales * 0.1) and random.random() < 0.20:
                        stockout_flag = True
                        
                # Update current stock state
                inventory_state[state_key] = closing_stock
                
                # Recalculate revenue based on final actual units sold
                revenue = round(units_sold * p.unit_price * (1 - discount_pct), 2)
                
                # Create records
                sale_rec = Sale(
                    week_start_date=week,
                    product_id=p.product_id,
                    store_id=s.store_id,
                    region=s.region,
                    units_sold=units_sold,
                    revenue=revenue,
                    promotion_flag=promotion_flag,
                    promotion_type=promotion_type,
                    discount_pct=discount_pct
                )
                
                inv_rec = Inventory(
                    week_start_date=week,
                    product_id=p.product_id,
                    store_id=s.store_id,
                    opening_stock=opening_stock,
                    units_received=units_received,
                    units_sold=units_sold,
                    closing_stock=closing_stock,
                    stockout_flag=stockout_flag
                )
                
                sales_records.append(sale_rec)
                inventory_records.append(inv_rec)
                
        # Batch insert for performance
        db.add_all(sales_records)
        db.add_all(inventory_records)
        db.commit()
        sales_records = []
        inventory_records = []
        
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

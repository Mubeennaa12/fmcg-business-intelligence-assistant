import sys
from sqlalchemy import text
from app.database import SessionLocal, engine, Base
from app.models import Product, Store, Sale, Inventory
from app.data_generator import seed_database
from app.analytics import get_kpi_summary, calculate_promotion_uplift, calculate_discount_impact, calculate_inventory_turnover
from app.evaluation import log_evaluation_metric, get_evaluation_summary
import pandas as pd

def run_verification():
    print("--- STARTING DATABASE AND ANALYTICS VERIFICATION ---")
    db = SessionLocal()
    
    try:
        # 1. Create tables and seed data
        Base.metadata.create_all(bind=engine)
        seed_database(db)
        
        # 2. Assert Master Data Counts
        product_count = db.query(Product).count()
        store_count = db.query(Store).count()
        sales_count = db.query(Sale).count()
        inventory_count = db.query(Inventory).count()
        
        print(f"Products Count: {product_count} (Expected: 20)")
        print(f"Stores Count: {store_count} (Expected: 40)")
        print(f"Sales Records Count: {sales_count} (Expected: 19200)")
        print(f"Inventory Records Count: {inventory_count} (Expected: 19200)")
        
        assert product_count == 20, f"Expected 20 products, found {product_count}"
        assert store_count == 40, f"Expected 40 stores, found {store_count}"
        assert sales_count == 19200, f"Expected 19,200 sales records, found {sales_count}"
        assert inventory_count == 19200, f"Expected 19,200 inventory records, found {inventory_count}"
        print("[OK] Master data counts match expectations.")
        
        # 3. Assert Inventory Calculation Consistency
        # opening_stock + units_received - units_sold = closing_stock
        print("Verifying inventory equation consistency...")
        mismatches = db.query(Inventory).filter(
            Inventory.opening_stock + Inventory.units_received - Inventory.units_sold != Inventory.closing_stock
        ).count()
        
        print(f"Inventory math mismatches: {mismatches}")
        assert mismatches == 0, f"Found {mismatches} records violating inventory consistency!"
        print("[OK] Inventory equation holds true for 100% of records.")
        
        # 4. Check Sales vs Inventory units_sold consistency
        print("Verifying sales units match inventory units...")
        mismatched_units = db.execute(text("""
            SELECT COUNT(*) 
            FROM sales s 
            JOIN inventory i ON s.product_id = i.product_id 
                            AND s.store_id = i.store_id 
                            AND s.week_start_date = i.week_start_date
            WHERE s.units_sold != i.units_sold
        """)).scalar()
        
        print(f"Sales and inventory units sold mismatches: {mismatched_units}")
        assert mismatched_units == 0, "Units sold differ between sales and inventory tables!"
        print("[OK] Sales and inventory units sold are fully aligned.")

        # 5. Run Analytics Engine Functions
        print("Testing Analytics Engine...")
        sales_df = pd.read_sql_table("sales", engine)
        inv_df = pd.read_sql_table("inventory", engine)
        
        summary = get_kpi_summary(sales_df, inv_df)
        print("KPI Summary:", summary)
        assert summary["total_revenue"] > 0, "Total revenue should be greater than 0"
        
        uplift = calculate_promotion_uplift(sales_df)
        print(f"Uplift columns: {list(uplift.columns)}")
        assert not uplift.empty, "Promotion uplift calculation returned empty dataframe"
        
        impact = calculate_discount_impact(sales_df)
        print(f"Discount impact rows: {len(impact)}")
        assert not impact.empty, "Discount impact calculation returned empty dataframe"
        
        turnover = calculate_inventory_turnover(sales_df, inv_df)
        print(f"Inventory turnover rows: {len(turnover)}")
        assert not turnover.empty, "Inventory turnover calculation returned empty dataframe"
        print("[OK] Analytics Engine completed all KPI calculations successfully.")
        
        # 6. Test Evaluation logging
        print("Testing Evaluation Logger...")
        initial_eval = get_evaluation_summary(db)
        log_evaluation_metric(
            db=db,
            user_query="Which region generated the most revenue?",
            sql_generated="SELECT region, SUM(revenue) FROM sales GROUP BY region",
            sql_success=True,
            latency_ms=120,
            is_empty_result=False,
            user_satisfaction=1
        )
        post_eval = get_evaluation_summary(db)
        print(f"Initial total queries: {initial_eval['total_queries']}")
        print(f"Post total queries: {post_eval['total_queries']}")
        assert post_eval["total_queries"] == initial_eval["total_queries"] + 1, "Evaluation metric not registered!"
        print("[OK] Evaluation metrics logging verified.")
        
        print("--- ALL VERIFICATIONS PASSED SUCCESSFULLY! ---")
        return True
        
    except Exception as e:
        print(f"[ERROR] VERIFICATION FAILED: {e}", file=sys.stderr)
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)

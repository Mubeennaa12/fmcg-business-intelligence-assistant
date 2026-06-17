import pandas as pd
import numpy as np

def get_kpi_summary(sales_df: pd.DataFrame, inv_df: pd.DataFrame) -> dict:
    """
    Returns high-level summary KPIs for the dashboard cards.
    """
    if sales_df.empty or inv_df.empty:
        return {
            "total_revenue": 0.0,
            "total_units_sold": 0,
            "active_promotions_pct": 0.0,
            "stockout_rate": 0.0
        }
    
    total_rev = float(sales_df["revenue"].sum())
    total_units = int(sales_df["units_sold"].sum())
    
    # Active promotion rate (percentage of records with promotion_flag = True)
    promo_weeks = sales_df["promotion_flag"].sum()
    total_weeks = len(sales_df)
    promo_pct = float((promo_weeks / total_weeks) * 100) if total_weeks > 0 else 0.0
    
    # Stockout rate (percentage of records with stockout_flag = True)
    stockouts = inv_df["stockout_flag"].sum()
    total_inv_records = len(inv_df)
    stockout_rate = float((stockouts / total_inv_records) * 100) if total_inv_records > 0 else 0.0
    
    return {
        "total_revenue": round(total_rev, 2),
        "total_units_sold": total_units,
        "active_promotions_pct": round(promo_pct, 2),
        "stockout_rate": round(stockout_rate, 2)
    }

def calculate_promotion_uplift(sales_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the promotion uplift: average sales units in promo weeks vs non-promo weeks.
    Returns a dataframe grouped by product/category showing the percentage lift.
    """
    if sales_df.empty:
        return pd.DataFrame()
        
    # Group by product/category and promotion flag
    group_cols = ["product_id", "promotion_flag"]
    if "product_name" in sales_df.columns:
        group_cols = ["product_name", "promotion_flag"]
        
    agg = sales_df.groupby(group_cols)["units_sold"].mean().unstack(fill_value=0)
    
    # Check if we have both False and True columns
    if False not in agg.columns:
        agg[False] = 0.0
    if True not in agg.columns:
        agg[True] = 0.0
        
    agg.rename(columns={False: "avg_units_no_promo", True: "avg_units_with_promo"}, inplace=True)
    
    # Calculate percentage uplift
    agg["uplift_pct"] = np.where(
        agg["avg_units_no_promo"] > 0,
        ((agg["avg_units_with_promo"] - agg["avg_units_no_promo"]) / agg["avg_units_no_promo"]) * 100,
        0.0
    )
    
    # Add count of promotions
    counts = sales_df[sales_df["promotion_flag"] == True].groupby(group_cols[0]).size()
    agg["promotion_count"] = counts.reindex(agg.index, fill_value=0)
    
    return agg.reset_index().round(2)

def calculate_discount_impact(sales_df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups sales by discount buckets to show price elasticity / volume changes.
    """
    if sales_df.empty:
        return pd.DataFrame()
        
    # Create discount buckets
    def bucket_discount(pct):
        if pct == 0:
            return "0% (No Discount)"
        elif pct <= 0.15:
            return "1% - 15% (Low)"
        elif pct <= 0.30:
            return "16% - 30% (Medium)"
        elif pct <= 0.49:
            return "31% - 49% (High)"
        else:
            return "50%+ (BOGO / Deep)"
            
    df = sales_df.copy()
    df["discount_bucket"] = df["discount_pct"].apply(bucket_discount)
    
    agg = df.groupby("discount_bucket").agg(
        avg_units_sold=("units_sold", "mean"),
        total_revenue=("revenue", "sum"),
        record_count=("units_sold", "count")
    ).reset_index()
    
    # Sort order for presentation
    sort_order = {
        "0% (No Discount)": 0,
        "1% - 15% (Low)": 1,
        "16% - 30% (Medium)": 2,
        "31% - 49% (High)": 3,
        "50%+ (BOGO / Deep)": 4
    }
    agg["sort_idx"] = agg["discount_bucket"].map(sort_order)
    agg = agg.sort_values("sort_idx").drop(columns=["sort_idx"])
    
    return agg.round(2)

def calculate_inventory_turnover(sales_df: pd.DataFrame, inv_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates inventory turnover: Total Units Sold / Average Inventory.
    """
    if sales_df.empty or inv_df.empty:
        return pd.DataFrame()
        
    # Group sales
    sales_prod = sales_df.groupby("product_id")["units_sold"].sum().reset_index()
    
    # Group inventory to find average stock
    inv_df["avg_stock"] = (inv_df["opening_stock"] + inv_df["closing_stock"]) / 2
    inv_prod = inv_df.groupby("product_id").agg(
        avg_stock=("avg_stock", "mean"),
        stockout_weeks=("stockout_flag", "sum"),
        total_weeks=("stockout_flag", "count")
    ).reset_index()
    
    merged = pd.merge(sales_prod, inv_prod, on="product_id")
    
    # Turnover ratio
    merged["inventory_turnover_ratio"] = np.where(
        merged["avg_stock"] > 0,
        merged["units_sold"] / merged["avg_stock"],
        0.0
    )
    
    merged["stockout_rate_pct"] = np.where(
        merged["total_weeks"] > 0,
        (merged["stockout_weeks"] / merged["total_weeks"]) * 100,
        0.0
    )
    
    return merged.round(2)

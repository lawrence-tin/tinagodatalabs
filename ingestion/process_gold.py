import snowflake.connector
from ingestion.base_ingestion import SNOWFLAKE_CONFIG

def run_gold_transformation():
    """
    Transform Silver data into pre-aggregated Gold tables for UI and ML.
    """
    print("🏗️  Starting Gold Layer transformation...")
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cursor = conn.cursor()

    try:
        # 1. Create Heatmap & Time Insights (Speeds up 'Insights' and 'Strategy' tabs)
        print("🔥 Pre-calculating Brand Insights...")
        cursor.execute("""
            CREATE OR REPLACE TABLE TEAM5PM_PRODUCT.GOLD.BRAND_TIME_INSIGHTS AS
            SELECT 
                client_id,
                brand_id,
                platform,
                DAYNAME(published_at) as day_of_week,
                HOUR(published_at) as hour_of_day,
                AVG(engagement_rate_pct) as avg_engagement_rate,
                AVG(raw_views) as avg_views,
                COUNT(*) as post_count
            FROM TEAM5PM_PRODUCT.SILVER.CANONICAL_PERFORMANCE
            GROUP BY 1, 2, 3, 4, 5
        """)

        # 2. Create AI Training Dataset (Speeds up 'Predict' tab and 'train_model.py')
        # This pre-flattens features using the dedicated stored procedure.
        print("🧠 Calling SP_LOAD_TRAINING_DATASET to flatten AI Training Dataset...")
        cursor.execute("CALL TEAM5PM_PRODUCT.GOLD.SP_LOAD_TRAINING_DATASET()")

        conn.commit()
        print("✅ Gold Layer update complete.")

    except Exception as e:
        print(f"❌ Gold Transformation failed: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_gold_transformation()
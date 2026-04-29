import snowflake.connector
from ingestion.base_ingestion import SNOWFLAKE_CONFIG

def run_silver_transformation():
    """
    Triggers the Snowflake stored procedure to transform Bronze data 
    into the Canonical Silver format for all platforms.
    """
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cursor = conn.cursor()

    print("🏗️  Executing Snowflake Stored Procedure: SP_BUILD_CANONICAL_PERFORMANCE...")

    try:
        cursor.execute("CALL TEAM5PM_PRODUCT.SILVER.SP_BUILD_CANONICAL_PERFORMANCE()")
        result = cursor.fetchone()
        print(f"✅ {result[0]}")
    except Exception as e:
        print(f"❌ Processing failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_silver_transformation()

"""
Shared Ingestion Framework

Provides a unified pipeline for ingesting raw JSON data into Snowflake Bronze.
Logic flow: Fetch (Platform Script) -> Save NDJSON -> Stage in Snowflake -> COPY INTO.
"""

import snowflake.connector
import os
import json
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

# Robustly load .env from the project root (one level up from this file)
env_path = Path(__file__).parent.parent / '.env'
print(f"🔍 Looking for .env at: {env_path.absolute()}")

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    print(f"⚠️ Warning: .env file not found at {env_path.absolute()}")

# -------------------------------
# SNOWFLAKE CONFIG
# -------------------------------
# Map internal keys to expected environment variable names
ENV_VAR_MAPPING = {
    "account": "snowflake_account",
    "user": "snowflake_user",
    "password": "snowflake_password",
    "warehouse": "snowflake_warehouse",
    "database": "snowflake_database",
    "schema": "snowflake_schema",
    "role": "snowflake_role"
}

SNOWFLAKE_CONFIG = {
    "account": os.getenv("snowflake_account"),
    "user": os.getenv("snowflake_user"),
    "password": os.getenv("snowflake_password"),
    "warehouse": os.getenv("snowflake_warehouse"),
    "database": os.getenv("snowflake_database"),
    "schema": os.getenv("snowflake_schema"),
}

print(f"📡 Loaded Snowflake Account: {SNOWFLAKE_CONFIG['account']}")

# -------------------------------
# VALIDATE CONFIG HELPER
# -------------------------------
def validate_config():
    """Ensures all required Snowflake variables are present."""
    for key, value in SNOWFLAKE_CONFIG.items():
        if value is None and key != "role":
            expected_var = ENV_VAR_MAPPING.get(key, key)
            raise Exception(f"❌ Missing environment variable: {expected_var}")

# -------------------------------
# UNIFIED INGESTION FLOW
# -------------------------------
def process_ingestion(platform, records):
    """
    Handles the boilerplate of saving, uploading, and cleaning up.
    """
    if not records:
        print(f"⚠️ No {platform} records fetched. Skipping.")
        return 0

    filename = f"{platform}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.ndjson"
    try:
        save_ndjson(records, filename)
        upload_to_snowflake(filename)
        return len(records)
    finally:
        cleanup_file(filename)

# -------------------------------
# SAVE NDJSON FILE
# -------------------------------
def save_ndjson(records, filename):
    """Saves records as Newline-Delimited JSON, the format expected by Snowflake COPY."""
    if not records:
        raise Exception("❌ No records to save")

    with open(filename, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"💾 Saved {len(records)} records to {filename}")
    return filename


# -------------------------------
# UPLOAD TO SNOWFLAKE BRONZE
# -------------------------------
def upload_to_snowflake(filename):
    print("☁️ Uploading to Snowflake...")
    
    if os.getenv("INGESTION_DRY_RUN") == "True":
        print(f"✨ [DRY RUN] Skipping Snowflake upload for {filename}. Data is valid.")
        return

    # Ensure we have credentials before attempting connection
    validate_config()

    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cursor = conn.cursor()

    try:
        # Create temp stage (safe)
        cursor.execute("CREATE TEMP STAGE IF NOT EXISTS social_stage")

        abs_path = os.path.abspath(filename)

        # Upload file to stage
        cursor.execute(
            f"PUT file://{abs_path} @social_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )

        print(f"📦 Uploaded file: {filename}")

        # COPY INTO with structured extraction (CRITICAL FIX)
        cursor.execute("""
            COPY INTO TEAM5PM_PRODUCT.BRONZE.RAW_SOCIAL_DATA (
                platform,
                platform_id,
                client_id,
                brand_id,
                raw_response,
                ingested_at,
                source_endpoint
            )
            FROM (
                SELECT
                    $1:platform::STRING,
                    $1:platform_id::STRING,
                    $1:client_id::STRING,
                    $1:brand_id::STRING,
                    $1:raw_response,
                    $1:ingested_at::TIMESTAMP_NTZ,
                    $1:source_endpoint::STRING
                FROM @social_stage
            )
            FILE_FORMAT = (TYPE = JSON)
            ON_ERROR = 'CONTINUE'
        """)

        conn.commit()

        # Debug / validation
        cursor.execute("SELECT COUNT(*) FROM TEAM5PM_PRODUCT.BRONZE.RAW_SOCIAL_DATA")
        total_rows = cursor.fetchone()[0]

        print(f"✅ Data loaded successfully")
        print(f"📊 Total rows in BRONZE.RAW_SOCIAL_DATA: {total_rows}")

    except Exception as e:
        print(f"❌ Snowflake upload failed: {e}")
        raise e

    finally:
        cursor.close()
        conn.close()


# -------------------------------
# CLEANUP FILE
# -------------------------------
def cleanup_file(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"🧹 Removed temp file: {filename}")
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")
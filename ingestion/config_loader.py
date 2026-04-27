import pandas as pd
import snowflake.connector
from ingestion.base_ingestion import SNOWFLAKE_CONFIG, validate_config


def get_active_clients(platform: str):
    validate_config()
    try:
        conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
        
        query = f"""
            SELECT 
                client_id,
                brand_id,
                platform,
                api_key,
                access_token,
                platform_account_id
            FROM TEAM5PM_PRODUCT.CONFIG.CLIENT_PLATFORM_CREDENTIALS
            WHERE platform = '{platform}'
              AND is_active = TRUE
        """

        df = pd.read_sql(query, conn)
        df.columns = df.columns.str.lower()
        conn.close()
        return df
    except Exception as e:
        print(f"❌ Failed to fetch config from Snowflake: {e}")
        # Return empty df so the calling loop handles it gracefully
        return pd.DataFrame()
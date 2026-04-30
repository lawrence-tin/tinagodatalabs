import pandas as pd
import snowflake.connector
from ingestion.base_ingestion import SNOWFLAKE_CONFIG, validate_config


def get_active_clients(platform: str, client_id=None, brand_id=None):
    validate_config()
    try:
        conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
        
        query = """
            SELECT 
                organization_id AS client_id,
                brand_id,
                platform,
                api_key,
                access_token,
                platform_account_id
            FROM TEAM5PM_PRODUCT.CONFIG.CLIENT_PLATFORM_CREDENTIALS
            WHERE platform = %s
              AND is_active = TRUE
        """
        params = [platform]

        if client_id:
            query += " AND organization_id = %s"
            params.append(client_id)
        if brand_id:
            query += " AND brand_id = %s"
            params.append(brand_id)

        cursor = conn.cursor()
        cursor.execute(query, params)
        df = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
        df.columns = df.columns.str.lower()
        conn.close()
        return df
    except Exception as e:
        print(f"❌ Failed to fetch config from Snowflake: {e}")
        # Return empty df so the calling loop handles it gracefully
        return pd.DataFrame()
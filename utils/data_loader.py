"""
Utility module for interacting with the Snowflake database.
Contains functions for authentication, multi-tenant configuration management,
and loading processed silver data for the UI.
"""

import pandas as pd
import streamlit as st
import bcrypt
import uuid
from datetime import datetime
from snowflake.connector import connect

# -----------------------------
# SNOWFLAKE CONNECTION
# -----------------------------
def get_connection():
    """Creates a raw connection to Snowflake using Streamlit secrets."""
    return connect(
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        account=st.secrets["snowflake"]["account"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"],
    )

# -----------------------------
# AUTHENTICATION FUNCTIONS
# -----------------------------
def authenticate_user(conn, email, password):
    """
    Authenticates a user against the CONFIG.USERS table.
    Returns user details if successful, None otherwise.
    """
    query = """
        SELECT user_id, email, password_hash
        FROM TEAM5PM_PRODUCT.CONFIG.USERS
        WHERE email = %s
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (email,))
        df_user = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
        if not df_user.empty:
            user_data = df_user.iloc[0]
            # Check password hash
            if bcrypt.checkpw(password.encode('utf-8'), user_data['PASSWORD_HASH'].encode('utf-8')):
                return {"user_id": user_data['USER_ID'], "email": user_data['EMAIL']}
        return None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None

def register_user(conn, email, password):
    """
    Registers a new user by hashing their password and inserting into CONFIG.USERS.
    Returns the new user_id if successful.
    """
    user_id = str(uuid.uuid4())[:8]  # Generate a unique short ID
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO TEAM5PM_PRODUCT.CONFIG.USERS (user_id, email, password_hash) VALUES (%s, %s, %s)",
            (user_id, email, hashed)
        )
        conn.commit()
        return user_id
    except Exception as e:
        st.error(f"Registration error: {e}")
        return None
    finally:
        cursor.close()

def fetch_user_clients(conn, user_id):
    """
    Fetches clients associated with a given user_id.
    """
    query = """
        SELECT
            c.client_id,
            c.client_name,
            ucm.role
        FROM TEAM5PM_PRODUCT.CONFIG.USER_CLIENT_MAP ucm
        JOIN TEAM5PM_PRODUCT.CONFIG.CLIENTS c ON ucm.client_id = c.client_id
        WHERE ucm.user_id = %s
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (user_id,))
        df_clients = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
        df_clients.columns = df_clients.columns.str.lower()
        return df_clients.to_dict(orient='records')
    except Exception as e:
        st.error(f"Error fetching user clients: {e}")
        return []

def fetch_brands(conn, organization_id):
    """
    Fetches brands associated with a given organization_id (client_id).
    """
    query = """
        SELECT brand_id, brand_name
        FROM TEAM5PM_PRODUCT.CONFIG.BRANDS
        WHERE organization_id = %s
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (organization_id,))
        df_brands = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
        df_brands.columns = df_brands.columns.str.lower()
        return df_brands.to_dict(orient='records')
    except Exception as e:
        st.error(f"Error fetching brands: {e}")
        return []

def create_client(conn, user_id, client_name):
    """
    Creates a new client in the CONFIG.CLIENTS table and links it to the user.
    """
    client_id = client_name.lower().replace(" ", "_")
    cursor = conn.cursor()
    try:
        # 1. Insert the new client
        cursor.execute(
            "INSERT INTO TEAM5PM_PRODUCT.CONFIG.CLIENTS (client_id, client_name) VALUES (%s, %s)",
            (client_id, client_name)
        )
        # 2. Map the current user to this client as an 'admin'
        cursor.execute(
            "INSERT INTO TEAM5PM_PRODUCT.CONFIG.USER_CLIENT_MAP (user_id, client_id, role) VALUES (%s, %s, %s)",
            (user_id, client_id, 'admin')
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error creating client: {e}")
        return False
    finally:
        cursor.close()

def create_brand(conn, organization_id, brand_name):
    """
    Creates a new brand under a specific organization.
    """
    brand_id = brand_name.lower().replace(" ", "_")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO TEAM5PM_PRODUCT.CONFIG.BRANDS (brand_id, organization_id, brand_name) VALUES (%s, %s, %s)",
            (brand_id, organization_id, brand_name)
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error creating brand: {e}")
        return False
    finally:
        cursor.close()

def save_platform_credentials(conn, organization_id, brand_id, platform, account_id, api_key):
    """
    Saves API credentials for a specific client and platform.
    """
    query = """
        INSERT INTO TEAM5PM_PRODUCT.CONFIG.CLIENT_PLATFORM_CREDENTIALS 
        (organization_id, brand_id, platform, platform_account_id, api_key, access_token, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
    """
    try:
        cursor = conn.cursor()
        # Now explicitly mapping organization and brand
        cursor.execute(query, (organization_id, brand_id, platform, account_id, api_key, api_key))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error saving credentials: {e}")
        return False
    finally:
        cursor.close()

def fetch_platform_connections(conn, organization_id):
    """
    Fetches all platform connections for a given organization.
    Uses a JOIN with BRANDS to ensure only existing brands are displayed.
    """
    query = """
        SELECT c.organization_id, c.brand_id, c.platform, c.platform_account_id, c.is_active
        FROM TEAM5PM_PRODUCT.CONFIG.CLIENT_PLATFORM_CREDENTIALS c
        JOIN TEAM5PM_PRODUCT.CONFIG.BRANDS b 
          ON c.brand_id = b.brand_id 
          AND c.organization_id = b.organization_id
        WHERE c.organization_id = %s
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (organization_id,))
        df = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
        df.columns = df.columns.str.lower()
        return df
    except Exception as e:
        st.error(f"Error fetching platform connections: {e}")
        return pd.DataFrame()

def delete_platform_connection(conn, organization_id, brand_id, platform):
    """
    Removes a platform connection from the database.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM TEAM5PM_PRODUCT.CONFIG.CLIENT_PLATFORM_CREDENTIALS WHERE organization_id = %s AND brand_id = %s AND platform = %s",
            (organization_id, brand_id, platform)
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error deleting connection: {e}")
        return False
    finally:
        cursor.close()

def update_platform_credentials(conn, organization_id, brand_id, platform, account_id, api_key):
    """
    Updates existing API credentials for a specific client and platform.
    """
    query = """
        UPDATE TEAM5PM_PRODUCT.CONFIG.CLIENT_PLATFORM_CREDENTIALS
        SET platform_account_id = %s, api_key = %s, access_token = %s
        WHERE organization_id = %s AND brand_id = %s AND platform = %s
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (account_id, api_key, api_key, organization_id, brand_id, platform))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error updating credentials: {e}")
        return False
    finally:
        cursor.close()

def fetch_org_platform_keys(conn, organization_id, platform):
    """
    Fetches unique API keys previously used by this organization for a specific platform.
    """
    query = """
        SELECT DISTINCT api_key
        FROM TEAM5PM_PRODUCT.CONFIG.CLIENT_PLATFORM_CREDENTIALS
        WHERE organization_id = %s AND platform = %s AND api_key IS NOT NULL
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (organization_id, platform))
        keys = [row[0] for row in cursor.fetchall()]
        return keys
    except Exception as e:
        print(f"Error fetching existing keys: {e}")
        return []



# -----------------------------

def fetch_brand_stats(conn, organization_id, brand_id, platform):
    """
    Fetches the latest sync time and record count for a specific brand/platform from Silver.
    """
    query = """
        SELECT 
            MAX(published_at) as last_sync,
            COUNT(*) as record_count
        FROM TEAM5PM_PRODUCT.SILVER.CANONICAL_PERFORMANCE
        WHERE client_id = %s AND brand_id = %s AND platform = %s
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (organization_id, brand_id, platform))
        row = cursor.fetchone()
        if row and row[0]:
            last_sync = row[0]
            # Ensure last_sync is a datetime object for formatting
            if not isinstance(last_sync, datetime):
                last_sync = pd.to_datetime(last_sync)
            
            return last_sync.strftime('%Y-%m-%d %H:%M'), int(row[1])
    except Exception as e:
        # Log the error but return default values to avoid crashing the UI
        print(f"Error fetching brand stats for {organization_id}/{brand_id}/{platform}: {e}")
        pass
    return "Never", 0


# -----------------------------



# -----------------------------
# SILVER DATA LOADER
# -----------------------------
def load_silver_data(conn, organization_id=None, brand_id=None, platform=None):

    query = """
        SELECT *
        FROM TEAM5PM_PRODUCT.SILVER.CANONICAL_PERFORMANCE
        WHERE 1=1
    """
    params = []
    if organization_id and organization_id != "All":
        query += " AND client_id = %s"
        params.append(organization_id)
    
    if brand_id and brand_id != "All":
        query += " AND brand_id = %s"
        params.append(brand_id)

    if platform and platform != "All":
        query += " AND platform = %s"
        params.append(platform)

    cursor = conn.cursor()
    cursor.execute(query, params)
    df = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])

    df.columns = df.columns.str.lower()

    # Convert numeric columns from Decimal (Snowflake default) to float for calculations
    numeric_cols = ["engagement_rate_pct", "raw_views", "duration_seconds", "raw_likes", "total_engagement"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")

    return df


# -----------------------------
# GOLD DATA (optional future use)
# -----------------------------
def load_gold_data(conn):
    query = """
        SELECT *
        FROM TEAM5PM_PRODUCT.GOLD.AI_TRAINING_DATASET
    """

    cursor = conn.cursor()
    cursor.execute(query)
    df = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
    df.columns = df.columns.str.lower()

    return df
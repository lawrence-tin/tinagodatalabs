import pandas as pd
import streamlit as st
from snowflake.connector import connect

# -----------------------------
# SNOWFLAKE CONNECTION
# -----------------------------
def get_connection():
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
# SILVER DATA LOADER
# -----------------------------
def load_silver_data(conn, client_id=None, platform=None):

    query = """
        SELECT *
        FROM TEAM5PM_PRODUCT.SILVER.CANONICAL_PERFORMANCE
        WHERE 1=1
    """

    if client_id and client_id != "All":
        query += f" AND client_id = '{client_id}'"
    
    if platform and platform != "All":
        query += f" AND platform = '{platform}'"

    df = pd.read_sql(query, conn)

    df.columns = df.columns.str.lower()

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

    df = pd.read_sql(query, conn)
    df.columns = df.columns.str.lower()

    return df
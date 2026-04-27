import joblib
import streamlit as st
from snowflake.snowpark import Session
import os


# -----------------------------
# SINGLE MODEL LOADER (SAAS SAFE)
# -----------------------------
@st.cache_resource
def load_model(client_id: str, platform: str):

    try:
        from snowflake.snowpark.context import get_active_session
        session = get_active_session()
    except:
        # Fallback for local development using secrets
        session = Session.builder.configs(st.secrets["snowflake"]).create()

    model_name = f"{client_id}_{platform}.joblib.gz"
    default_model = "engagement_model.joblib.gz"

    # 1. Local Development Check (try specific model first, then fall back to default)
    for name in [model_name, default_model]:
        local_dev_path = os.path.join(os.getcwd(), "models", name)
        if os.path.exists(local_dev_path):
            return joblib.load(local_dev_path)

    # 2. SaaS Production Path (Snowflake Stage)
    temp_dir = os.path.join(os.getcwd(), "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Try specific model from Snowflake stage, then fall back to default model
    for name in [model_name, default_model]:
        stage_path = f"@TEAM5PM_PRODUCT.GOLD.MODELS/{name}"
        try:
            # Download from Snowflake stage to local temp
            files = session.file.get(stage_path, temp_dir)
            
            if files:
                local_path = os.path.join(temp_dir, name)
                return joblib.load(local_path)
        except Exception:
            # If specific model fails (e.g., doesn't exist on stage), try the next one
            continue

    # 3. Fail gracefully if no model is found anywhere
    st.error(f"Model not found: {model_name}")
    st.info(
        f"We couldn't find a specific model for **{client_id}** on **{platform}**. "
        f"Please ensure `{model_name}` or `{default_model}` exists in your local `models/` "
        "folder or the Snowflake `@MODELS` stage."
    )
    st.stop()
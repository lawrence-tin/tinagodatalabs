import joblib
import streamlit as st
import os
from datetime import datetime

@st.cache_resource
def load_model(org_id, brand_id, platform):
    """
    Loads the trained model. In an MVP, we use a single global model.
    In production, you could load brand-specific models here.
    """
    brand_model_path = f"models/{brand_id}/model.joblib.gz"
    global_model_path = "models/global_model.joblib.gz"
    legacy_model_path = "models/engagement_model.joblib.gz"
    
    # 1. Try Brand-Specific Model
    if brand_id != "All" and os.path.exists(brand_model_path):
        return joblib.load(brand_model_path)
    
    # 2. Try Global Model
    if os.path.exists(global_model_path):
        return joblib.load(global_model_path)

    # 3. Try Legacy Model (Fallback)
    if os.path.exists(legacy_model_path):
        return joblib.load(legacy_model_path)

    st.warning("No ML model found. Using global defaults.")
    return None

def get_model_status(brand_id):
    """
    Returns the status and last trained timestamp of the model for a brand.
    """
    brand_model_path = f"models/{brand_id}/model.joblib.gz"
    global_model_path = "models/global_model.joblib.gz"
    
    if brand_id != "All" and os.path.exists(brand_model_path):
        mtime = os.path.getmtime(brand_model_path)
        dt_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        return "✅ Brand Trained", dt_str
        
    if os.path.exists(global_model_path):
        mtime = os.path.getmtime(global_model_path)
        dt_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        return "⚠️ Global Fallback", dt_str
        
    return "❌ Not Trained", "N/A"
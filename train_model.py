"""
Model Training Pipeline

Implements the hierarchical model architecture:
1. Global Model: Fallback for all brands.
2. Brand Models: Personalised models trained only on a specific brand's history.
"""

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os
from utils.data_loader import get_connection, load_gold_training_data
from utils.features import build_features, EXPECTED_ORDER

def train_model_on_gold(df):
    """Trains a model using pre-calculated features from the Gold Layer."""
    # 1. Platform Encoding (since it's stored as a string in Gold)
    plat_map = {"youtube": 0, "tiktok": 1, "instagram": 2, "facebook": 3}
    df["platform_encoded"] = df["platform"].str.lower().map(plat_map).fillna(0)
    
    # 2. Select Features (X) and Label (y)
    X = df[EXPECTED_ORDER].fillna(0)
    y = df["label_engagement_rate"].fillna(0)

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model

def train_global_model():
    """
    Trains a global fallback model AND individual brand models.
    """
    conn = get_connection()
    print("Fetching Gold Training Dataset...")
    df = load_gold_training_data(conn)
    
    if df.empty or len(df) < 5:
        print("❌ Not enough data to train any model. Ingest more videos first.")
        return

    os.makedirs("models", exist_ok=True)

    # 1. Train & Save Global Model
    print("🧠 Training Global Fallback Model...")
    global_model = train_model_on_gold(df)
    joblib.dump(global_model, "models/global_model.joblib.gz")
    # Keep legacy path for safety during transition
    joblib.dump(global_model, "models/engagement_model.joblib.gz")

    # 2. Train & Save Brand-Specific Models
    brands = df['brand_id'].unique()
    for brand_id in brands:
        brand_df = df[df['brand_id'] == brand_id]
        
        if len(brand_df) >= 5:
            print(f"🧠 Training Specific Model for Brand: {brand_id}...")
            brand_model = train_model_on_gold(brand_df)
            
            brand_dir = f"models/{brand_id}"
            os.makedirs(brand_dir, exist_ok=True)
            joblib.dump(brand_model, f"{brand_dir}/model.joblib.gz")
        else:
            print(f"⏭️ Skipping {brand_id}: Not enough data (found {len(brand_df)})")

    print("✅ Training cycle complete.")

if __name__ == "__main__":
    train_global_model()
import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from utils.data_loader import get_connection
from utils.features import EXPECTED_ORDER

def load_training_data(client_id, brand_id):
    """
    Fetches training data from the GOLD layer for a specific brand.
    """
    conn = get_connection()
    query = """
        SELECT *
        FROM TEAM5PM_PRODUCT.GOLD.AI_TRAINING_DATASET
        WHERE client_id = %s
        AND brand_id = %s
    """
    try:
        # Using parameterized query for security and reliability
        df = pd.read_sql(query, conn, params=(client_id, brand_id))
        df.columns = df.columns.str.lower()
        return df
    finally:
        conn.close()

def train_model(client_id, brand_id):
    """
    Trains a per-brand model and saves it to disk.
    """
    df = load_training_data(client_id, brand_id)

    if df.empty or len(df) < 5:
        raise ValueError(f"Insufficient data to train model for brand: {brand_id}. Need at least 5 records.")

    # -------------------------------
    # ENCODE PLATFORM (Same logic as features.py)
    # -------------------------------
    if 'platform' in df.columns and 'platform_encoded' not in df.columns:
        plat_map = {"youtube": 0, "tiktok": 1, "instagram": 2, "facebook": 3, "all": 0}
        df['platform_encoded'] = df['platform'].str.lower().map(plat_map).fillna(0).astype(int)

    # -------------------------------
    # FEATURES (Aligned with concept.md)
    # -------------------------------
    feature_cols = EXPECTED_ORDER
    target_col = "label_engagement_rate"

    # Ensure all required columns are present in the dataframe
    missing_cols = [col for col in feature_cols + [target_col] if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in training data: {', '.join(missing_cols)}")

    X = df[feature_cols].fillna(0)
    y = df[target_col].fillna(0)

    # Initialize and fit model
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        random_state=42
    )
    model.fit(X, y)

    # Save model locally
    save_path = f"models/{client_id}"
    os.makedirs(save_path, exist_ok=True)
    
    model_file = f"{save_path}/{brand_id}.joblib"
    joblib.dump(model, model_file)
    
    print(f"✅ Model saved successfully: {model_file}")
    return model
import joblib
import os

def load_model(client_id, brand_id):
    """
    Loads a pre-trained joblib model for a specific client/brand.
    """
    model_path = f"models/{client_id}/{brand_id}.joblib"

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")

    return joblib.load(model_path)
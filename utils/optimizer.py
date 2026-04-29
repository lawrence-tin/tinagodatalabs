import pandas as pd
import numpy as np
from itertools import product
from utils.features import extract_context_features, EXPECTED_ORDER

def generate_scenarios():
    """
    Generate all possible combinations of categorical/discrete inputs.
    """
    durations = [60, 300, 600, 900, 1200]
    hours = [10, 14, 16, 18, 20, 22]  # High-traffic windows
    money_flags = [0, 1]
    question_flags = [0, 1]
    number_flags = [0, 1]
    weekends = [0, 1]
    title_lengths = [30, 55, 85] # Short, Medium, Long

    combos = list(product(durations, hours, money_flags, question_flags, number_flags, weekends, title_lengths))
    
    return pd.DataFrame(combos, columns=[
        "duration_seconds", 
        "publish_hour_utc", 
        "has_money_symbol", 
        "has_question_mark", 
        "has_numbers",
        "is_weekend",
        "title_length"
    ])

def build_feature_frame(scenarios, df_silver, platform_name):
    """
    Prepares the full feature set required by the model using silver data averages.
    """
    # Get contextual averages once
    context = extract_context_features(df_silver)

    # Platform encoding
    platform_map = {"youtube": 0, "tiktok": 1, "instagram": 2, "facebook": 3, "all": 0}
    scenarios["platform_encoded"] = platform_map.get(platform_name.lower(), 0)
    
    # Apply historical context to every row in the scenario grid
    for col, value in context.items():
        scenarios[col] = value

    return scenarios[EXPECTED_ORDER]

def run_optimization(model, df_silver, platform):
    """
    Orchestrates the simulation and returns the top 10 ranked scenarios.
    """
    # 1. Generate grid
    scenarios = generate_scenarios()
    
    # 2. Map features to model requirements
    features = build_feature_frame(scenarios.copy(), df_silver, platform)
    
    # 3. Batch Inference (Vectorized - very fast)
    scenarios["predicted_engagement"] = model.predict(features)
    
    # 4. Rank and return
    return scenarios.sort_values("predicted_engagement", ascending=False).head(10)
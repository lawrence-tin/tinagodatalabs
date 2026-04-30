import pandas as pd
import numpy as np
from itertools import product
from utils.features import EXPECTED_ORDER

def generate_scenarios():
    """
    Generate all possible combinations of categorical/discrete inputs.
    """
    durations = [240, 360, 480, 600, 900, 1200]
    hours = list(range(0, 24, 2))  # Every 2 hours
    money_flags = [0, 1]
    question_flags = [0, 1]
    number_flags = [0, 1]

    combos = list(product(durations, hours, money_flags, question_flags, number_flags))
    
    return pd.DataFrame(combos, columns=[
        "duration_seconds", 
        "publish_hour_utc", 
        "has_money_symbol", 
        "has_question_mark", 
        "has_numbers"
    ])

def build_feature_frame(scenarios, df_silver, platform):
    """
    Prepares the full feature set required by the model using silver data averages.
    """
    # Use historical averages as the 'baseline' state for the simulation
    avg_views = float(df_silver['raw_views'].mean()) if 'raw_views' in df_silver.columns else 0
    avg_engagement = float(df_silver['engagement_rate_pct'].mean())
    avg_duration = float(df_silver['duration_seconds'].mean())

    # Static/Inferred features
    scenarios["title_length"] = 10
    scenarios["is_weekend"] = 0
    
    # History-based features (Contextual scaling)
    scenarios["rolling_avg_views_5"] = avg_views
    scenarios["rolling_avg_engagement_5"] = avg_engagement
    scenarios["rolling_avg_duration_5"] = avg_duration
    scenarios["prev_video_views"] = avg_views
    scenarios["prev_video_engagement"] = avg_engagement
    scenarios["prev_video_duration"] = avg_duration
    scenarios["prev_video_has_money"] = scenarios["has_money_symbol"]

    # Platform encoding matching utils.features mapping
    plat_map = {"youtube": 0, "tiktok": 1, "instagram": 2, "facebook": 3, "all": 0}
    scenarios["platform_encoded"] = plat_map.get(str(platform).lower(), 0)

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
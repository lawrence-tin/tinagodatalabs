import pandas as pd
import numpy as np
from itertools import product
from utils.features import EXPECTED_ORDER, extract_title_features

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

def build_feature_frame(scenarios, df_silver, platform, category="Other", tags="", current_title=""):
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

    # If a current_title is provided, use its extracted features as a baseline
    # The optimizer will still explore variations of has_money_symbol, etc.
    title_feats = extract_title_features(current_title)
    scenarios["title_length"] = title_feats["title_length"] # Use actual title length

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

    # Contextual features from current session
    cat_map = {"Entertainment": 0, "Education": 1, "Vlog": 2, "News": 3, "Other": 4}
    scenarios["category_encoded"] = cat_map.get(category, 4)
    scenarios["tag_count"] = len([t for t in tags.split(",") if t.strip()])

    return scenarios[EXPECTED_ORDER]

def run_optimization(model, df_silver, platform, category="Other", tags="", current_title=""):
    """
    Orchestrates the simulation and returns the top 10 ranked scenarios.

    Important: we enforce some duration diversity so the UI doesn't show
    the same duration for all options when the model ranking degenerates.
    """
    scenarios = generate_scenarios()

    features = build_feature_frame(scenarios.copy(), df_silver, platform, category, tags, current_title)

    scenarios["predicted_engagement"] = model.predict(features)

    ranked = scenarios.sort_values("predicted_engagement", ascending=False)

    # Pick top results with unique durations first, then fill remainder.
    target_rows = 10
    picked = []
    seen_durations = set()

    for _, row in ranked.iterrows():
        dur = int(row["duration_seconds"])
        if dur not in seen_durations:
            picked.append(row)
            seen_durations.add(dur)
        if len(picked) >= min(target_rows, len(seen_durations)):
            # If we already collected enough diverse durations, we can stop early.
            if len(picked) >= 10:
                break

    # If we didn't reach target_rows (e.g., very small grid), fill with next best.
    if len(picked) < target_rows:
        for _, row in ranked.iterrows():
            picked.append(row)
            if len(picked) >= target_rows:
                break

    out = pd.DataFrame(picked).drop_duplicates(subset=["duration_seconds", "publish_hour_utc", "has_money_symbol", "has_question_mark", "has_numbers"], keep="first")
    return out.head(target_rows)

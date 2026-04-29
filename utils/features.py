import pandas as pd
import re

# -------------------------------
# FEATURE CONTRACT (Single Source of Truth)
# -------------------------------
EXPECTED_ORDER = [
    "duration_seconds",
    "title_length",
    "has_money_symbol",
    "has_question_mark",
    "has_numbers",
    "publish_hour_utc",
    "is_weekend",
    "platform_encoded",
    "rolling_avg_views_5",
    "rolling_avg_engagement_5",
    "rolling_avg_duration_5",
    "prev_video_views",
    "prev_video_engagement",
    "prev_video_duration",
    "prev_video_has_money"
]

def extract_title_features(title: str):
    title = title or ""
    return {
        "title_length": len(title),
        "has_money_symbol": int("$" in title),
        "has_question_mark": int("?" in title),
        "has_numbers": int(bool(re.search(r"\d", title))),
    }

def extract_time_features(hour: int, weekend: bool):
    return {
        "publish_hour_utc": hour,
        "is_weekend": int(weekend),
    }

def extract_context_features(df_silver: pd.DataFrame):
    if df_silver is None or df_silver.empty:
        return {
            "rolling_avg_views_5": 0,
            "rolling_avg_engagement_5": 0,
            "rolling_avg_duration_5": 0,
            "prev_video_views": 0,
            "prev_video_engagement": 0,
            "prev_video_duration": 0,
            "prev_video_has_money": 0,
        }

    df_sorted = df_silver.sort_values("published_at")
    last_5 = df_sorted.tail(5)
    prev = df_sorted.iloc[-1]

    return {
        "rolling_avg_views_5": float(last_5["raw_views"].mean()),
        "rolling_avg_engagement_5": float(last_5["engagement_rate_pct"].mean()),
        "rolling_avg_duration_5": float(last_5["duration_seconds"].mean()),
        "prev_video_views": float(prev["raw_views"]),
        "prev_video_engagement": float(prev["engagement_rate_pct"]),
        "prev_video_duration": float(prev["duration_seconds"]),
        "prev_video_has_money": int("$" in str(prev.get("content_title", ""))),
    }

def build_features(duration, title, hour, weekend, df_silver, platform_name):
    """
    Standardized feature builder for both training and prediction.
    """
    features = {}
    features["duration_seconds"] = duration
    
    # Platform encoding
    plat_map = {"youtube": 0, "tiktok": 1, "instagram": 2, "facebook": 3, "all": 0}
    features["platform_encoded"] = plat_map.get(str(platform_name).lower(), 0)

    # Update from sub-extractors
    features.update(extract_title_features(title))
    features.update(extract_time_features(hour, weekend))
    features.update(extract_context_features(df_silver))

    # Return DataFrame with guaranteed column order
    df = pd.DataFrame([features])
    return df[EXPECTED_ORDER]
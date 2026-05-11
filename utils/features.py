import pandas as pd
import re

# -------------------------------
# FEATURE CONTRACT (Single Source of Truth)
# -------------------------------
EXPECTED_ORDER = [
    "duration_seconds",
    "title_length",
    "has_hashtags",
    "has_emojis",
    "has_money_symbol",
    "has_question_mark",
    "has_numbers",
    "has_exclamation",
    "has_uppercase",
    "has_mentions",
    "has_call_to_action",
    "hashtag_count",
    "mention_count",
    "publish_hour_utc",
    "is_weekend",
    "platform_encoded",
    "rolling_avg_views_5",
    "rolling_avg_engagement_5",
    "rolling_avg_duration_5",
    "prev_video_views",
    "prev_video_engagement",
    "prev_video_duration",
    "prev_video_has_money",
    "brand_avg_views_30",
    "brand_avg_engagement_30",
    "brand_post_frequency_7",
    "days_since_last_post"
]

def extract_title_features(title: str):
    # Snowflake/pandas can yield NaN (float) for missing text fields.
    # Coerce to string safely so len()/regex won't crash.
    if title is None:
        title = ""
    else:
        title = str(title)

    # Match Snowflake logic for CTA detection
    cta_keywords = ["link in bio", "subscribe", "follow", "comment below", "shop now"]
    has_cta = any(kw in title.lower() for kw in cta_keywords)

    # Detect emojis (basic range)
    has_emojis = bool(re.search(r'[^\x00-\x7F]+', title))

    # Detect uppercase pattern (4 or more consecutive caps)
    has_uppercase = bool(re.search(r'[A-Z]{4,}', title))

    return {
        "title_length": len(title),
        "has_hashtags": int("#" in title),
        "has_emojis": int(has_emojis),
        "has_money_symbol": int(any(s in title.upper() for s in ["$", "USD", "€"])),
        "has_question_mark": int("?" in title),
        "has_numbers": int(bool(re.search(r"\d", title))),
        "has_exclamation": int("!" in title),
        "has_uppercase": int(has_uppercase),
        "has_mentions": int("@" in title),
        "has_call_to_action": int(has_cta),
        "hashtag_count": len(re.findall(r"#\w+", title)),
        "mention_count": len(re.findall(r"@\w+", title)),
    }

def extract_time_features(hour: int, weekend: bool):
    return {
        "publish_hour_utc": hour,
        "is_weekend": int(weekend),
    }

def extract_context_features(df_silver: pd.DataFrame):
    if df_silver is None or df_silver.empty:
        return {k: 0.0 for k in [
            "rolling_avg_views_5", "rolling_avg_engagement_5", "rolling_avg_duration_5", 
            "prev_video_views", "prev_video_engagement", "prev_video_duration", "prev_video_has_money",
            "brand_avg_views_30", "brand_avg_engagement_30", "brand_post_frequency_7", "days_since_last_post"
        ]}

    # Ensure data is sorted for rolling metrics
    df_sorted = df_silver.sort_values("published_at") if "published_at" in df_silver.columns else df_silver
    last_5 = df_sorted.tail(5)
    last_30 = df_sorted.tail(30)
    prev = df_sorted.iloc[-1]

    # Calculate Days Since Last Post
    days_since = 0
    if not df_sorted.empty:
        last_date = df_sorted.iloc[-1]["published_at"]
        days_since = (pd.Timestamp.utcnow().tz_localize(None) - last_date.tz_localize(None)).days

    return {
        "rolling_avg_views_5": float(last_5["raw_views"].mean()),
        "rolling_avg_engagement_5": float(last_5["engagement_rate_pct"].mean()),
        "rolling_avg_duration_5": float(last_5["duration_seconds"].mean()),
        "prev_video_views": float(prev["raw_views"]),
        "prev_video_engagement": float(prev["engagement_rate_pct"]),
        "prev_video_duration": float(prev["duration_seconds"]),
        "prev_video_has_money": int("$" in str(prev.get("content_title", ""))),
        "brand_avg_views_30": float(last_30["raw_views"].mean()),
        "brand_avg_engagement_30": float(last_30["engagement_rate_pct"].mean()),
        "brand_post_frequency_7": len(df_sorted[df_sorted["published_at"] > (pd.Timestamp.utcnow() - pd.Timedelta(days=7))]),
        "days_since_last_post": max(0, days_since)
    }

def build_features(duration, title, hour, weekend, df_silver, platform_name):
    """
    Standardized feature builder for both training and prediction.
    """
    features = {}
    features["duration_seconds"] = duration
    
    # Platform encoding matching train_model.py
    plat_map = {"youtube": 0, "tiktok": 1, "instagram": 2, "facebook": 3, "all": 0}
    features["platform_encoded"] = plat_map.get(str(platform_name).lower(), 0)

    # Extract components
    features.update(extract_title_features(title))
    features.update(extract_time_features(hour, weekend))
    features.update(extract_context_features(df_silver))

    # Ensure correct column order and type
    df_out = pd.DataFrame([features])
    return df_out[EXPECTED_ORDER]

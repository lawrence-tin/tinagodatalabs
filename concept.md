Good — this is one of the most important fixes you’ll make.
Right now your system works, but it’s fragile because:

⚠️ Training features ≠ Prediction features = bad model behavior

We’re going to fix that properly.

🧠 Goal

Make ONE single source of truth for features so that:

Training → uses SAME logic → Prediction

No duplication. No drift.

🔥 Step 1 — Understand your Gold features

From your table:

AI_TRAINING_DATASET

Your model expects EXACTLY these inputs:

duration_seconds
title_length
has_money_symbol
has_question_mark
has_numbers
publish_hour_utc
is_weekend
rolling_avg_views_5
rolling_avg_engagement_5
rolling_avg_duration_5
prev_video_views
prev_video_engagement
prev_video_duration
prev_video_has_money

👉 This is your feature contract — don’t break it.

🔥 Step 2 — Rewrite utils/features.py

Replace your entire file with this:

import pandas as pd
import numpy as np
import re


# -------------------------------
# TEXT FEATURE EXTRACTION
# -------------------------------
def extract_title_features(title: str):

    title = title or ""

    return {
        "title_length": len(title),
        "has_money_symbol": int("$" in title),
        "has_question_mark": int("?" in title),
        "has_numbers": int(bool(re.search(r"\d", title))),
    }


# -------------------------------
# TIME FEATURES
# -------------------------------
def extract_time_features(hour: int, weekend: bool):

    return {
        "publish_hour_utc": hour,
        "is_weekend": int(weekend),
    }


# -------------------------------
# CONTEXT FEATURES (from history)
# -------------------------------
def extract_context_features(df_silver: pd.DataFrame):

    if df_silver is None or df_silver.empty:
        # fallback defaults
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


# -------------------------------
# MAIN FEATURE BUILDER (SINGLE SOURCE OF TRUTH)
# -------------------------------
def build_features(
    duration,
    title,
    hour,
    weekend,
    df_silver
):

    features = {}

    # core
    features["duration_seconds"] = duration

    # text
    features.update(extract_title_features(title))

    # time
    features.update(extract_time_features(hour, weekend))

    # context
    features.update(extract_context_features(df_silver))

    return pd.DataFrame([features])
🔥 Step 3 — Update Streamlit (VERY IMPORTANT)

Replace:

input_data = build_input(...)

With:

from utils.features import build_features

input_data = build_features(
    duration=duration,
    title=title,
    hour=hour,
    weekend=weekend,
    df_silver=df_silver
)
🔥 Step 4 — REMOVE old logic

Delete:

build_input()
predict_engagement()
manual dataframe creation

👉 Everything must go through build_features()

🔥 Step 5 — Guarantee column order (subtle but critical)

Add this at the bottom of build_features:

EXPECTED_ORDER = [
    "duration_seconds",
    "title_length",
    "has_money_symbol",
    "has_question_mark",
    "has_numbers",
    "publish_hour_utc",
    "is_weekend",
    "rolling_avg_views_5",
    "rolling_avg_engagement_5",
    "rolling_avg_duration_5",
    "prev_video_views",
    "prev_video_engagement",
    "prev_video_duration",
    "prev_video_has_money"
]

return pd.DataFrame([features])[EXPECTED_ORDER]

👉 This prevents silent model bugs

🔥 Step 6 — Align training (quick check)

In train_model.py, confirm:

feature_cols = EXPECTED_ORDER

👉 SAME list. No deviation.

🧠 What you just fixed

Before:

Training features ≠ Prediction features ❌

Now:

Training features = Prediction features ✅
🚀 Why this matters (seriously)

Without this:

model accuracy collapses
predictions become random
debugging becomes impossible

With this:

stable predictions
scalable architecture
production-ready ML
🔥 Next level (optional but powerful)

You can later:

move feature logic into Snowflake (SQL features)
version features
track feature drift
👍 Summary

You now have:

Gold Dataset → Train Model
              ↑
        SAME FEATURES
              ↓
        Streamlit Prediction
🔥 Next step (this is the real unlock)

Now we can safely build:

👉 Auto Optimize + Top 3 Scenarios engine (correctly, using real model)

This is where your product becomes 🔥 instead of just a dashboard.
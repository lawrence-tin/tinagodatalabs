import pandas as pd

def build_input(
    duration,
    title,
    money,
    question,
    numbers,
    hour,
    weekend,
    df
):
    avg_views = df['raw_views'].mean()
    avg_engagement = df['engagement_rate_pct'].mean()
    avg_duration = df['duration_seconds'].mean()

    return pd.DataFrame([{
        "duration_seconds": duration,
        "title_length": len(title) if title else 0,
        "has_money_symbol": int(money),
        "has_question_mark": int(question),
        "has_numbers": int(numbers),
        "publish_hour_utc": hour,
        "is_weekend": int(weekend),

        # engineered features
        "rolling_avg_views_5": avg_views,
        "rolling_avg_engagement_5": avg_engagement,
        "rolling_avg_duration_5": avg_duration,
        "prev_video_views": avg_views,
        "prev_video_engagement": avg_engagement,
        "prev_video_has_money": int(money)
    }])
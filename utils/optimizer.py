import pandas as pd

def auto_optimize(model, df):
    best_score = -1
    best_config = None

    avg_views = df['raw_views'].mean()
    avg_engagement = df['engagement_rate_pct'].mean()
    avg_duration = df['duration_seconds'].mean()

    for duration in [300, 480, 600, 900]:
        for hour in range(12, 22):
            for money in [0, 1]:
                for question in [0, 1]:
                    for numbers in [0, 1]:

                        input_data = pd.DataFrame([{
                            "duration_seconds": duration,
                            "title_length": 10,
                            "has_money_symbol": money,
                            "has_question_mark": question,
                            "has_numbers": numbers,
                            "publish_hour_utc": hour,
                            "is_weekend": 0,

                            "rolling_avg_views_5": avg_views,
                            "rolling_avg_engagement_5": avg_engagement,
                            "rolling_avg_duration_5": avg_duration,
                            "prev_video_views": avg_views,
                            "prev_video_engagement": avg_engagement,
                            "prev_video_has_money": money
                        }])

                        score = float(model.predict(input_data)[0])

                        if score > best_score:
                            best_score = score
                            best_config = {
                                "duration": duration,
                                "hour": hour,
                                "money": money,
                                "question": question,
                                "numbers": numbers
                            }

    return best_score, best_config


def top_scenarios(model, df, top_n=3):
    results = []

    avg_views = df['raw_views'].mean()
    avg_engagement = df['engagement_rate_pct'].mean()
    avg_duration = df['duration_seconds'].mean()

    for duration in [300, 480, 600, 900]:
        for hour in range(12, 22):
            for money in [0, 1]:

                input_data = pd.DataFrame([{
                    "duration_seconds": duration,
                    "title_length": 10,
                    "has_money_symbol": money,
                    "has_question_mark": 0,
                    "has_numbers": 0,
                    "publish_hour_utc": hour,
                    "is_weekend": 0,

                    "rolling_avg_views_5": avg_views,
                    "rolling_avg_engagement_5": avg_engagement,
                    "rolling_avg_duration_5": avg_duration,
                    "prev_video_views": avg_views,
                    "prev_video_engagement": avg_engagement,
                    "prev_video_has_money": money
                }])

                score = float(model.predict(input_data)[0])

                results.append({
                    "score": score,
                    "duration": duration,
                    "hour": hour,
                    "money": money
                })

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]
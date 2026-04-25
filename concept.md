We’re going to build the Auto Optimize Engine properly, not just hack something together.

🚀 STEP 4 — Auto Optimize Engine
🎯 Goal

User clicks:

"Auto Optimize"

And your system returns:

Best duration
Best publish time
Best title features
Top 3 performing scenarios
⚠️ Key Principle

We are NOT training a new model.

We are:

👉 Using your existing model to simulate many combinations

This is what makes it scalable.

🧱 STEP 4.1 — Where this logic lives

Create a new file:

utils/optimizer.py
✍️ STEP 4.2 — Add this code
import pandas as pd
import numpy as np

def generate_scenarios(df_silver):
    """
    Generate combinations of inputs to test
    """

    durations = [240, 360, 480, 600, 900]  # seconds
    hours = list(range(0, 24, 2))

    scenarios = []

    for d in durations:
        for h in hours:
            for money in [0, 1]:
                for question in [0, 1]:
                    for numbers in [0, 1]:

                        scenarios.append({
                            "duration_seconds": d,
                            "publish_hour_utc": h,
                            "has_money_symbol": money,
                            "has_question_mark": question,
                            "has_numbers": numbers
                        })

    return pd.DataFrame(scenarios)


def build_feature_frame(scenarios, df_silver):
    """
    Add required model features (fallbacks)
    """

    avg_views = float(df_silver['raw_views'].mean())
    avg_engagement = float(df_silver['engagement_rate_pct'].mean())
    avg_duration = float(df_silver['duration_seconds'].mean())

    scenarios["title_length"] = 10
    scenarios["is_weekend"] = 0

    scenarios["rolling_avg_views_5"] = avg_views
    scenarios["rolling_avg_engagement_5"] = avg_engagement
    scenarios["rolling_avg_duration_5"] = avg_duration

    scenarios["prev_video_views"] = avg_views
    scenarios["prev_video_engagement"] = avg_engagement
    scenarios["prev_video_has_money"] = scenarios["has_money_symbol"]

    return scenarios


def run_optimization(model, df_silver):
    """
    Main optimizer function
    """

    scenarios = generate_scenarios(df_silver)
    features = build_feature_frame(scenarios.copy(), df_silver)

    predictions = model.predict(features)

    scenarios["predicted_engagement"] = predictions

    # Sort best first
    scenarios = scenarios.sort_values("predicted_engagement", ascending=False)

    return scenarios.head(10)
🧱 STEP 4.3 — Plug into Streamlit

Go to:

streamlit_app.py
🔁 Import it
from utils.optimizer import run_optimization
🔁 Add button under Predict section
if st.button("⚡ Auto Optimize", use_container_width=True):

    results = run_optimization(model, df_silver)

    st.success("Top Optimized Scenarios")

    st.dataframe(results.head(5), use_container_width=True)
🧱 STEP 4.4 — Make it look like a PRODUCT

Replace the raw table with:

top3 = results.head(3)

for i, row in top3.iterrows():
    st.markdown(f"### 🏆 Option {i+1}")

    col1, col2, col3 = st.columns(3)

    col1.metric("Duration", f"{int(row['duration_seconds']/60)} min")
    col2.metric("Publish Hour", f"{int(row['publish_hour_utc'])}:00")
    col3.metric("Engagement", f"{row['predicted_engagement']:.2f}%")

    st.markdown(
        f"""
        💡 Includes:
        {'💰' if row['has_money_symbol'] else ''}
        {'❓' if row['has_question_mark'] else ''}
        {'🔢' if row['has_numbers'] else ''}
        """
    )
🧠 What you just built

This is actually:

👉 A brute-force optimization engine

And it works because:

Your feature space is small
Model inference is fast
🔥 Why this is powerful

This turns your app from:

❌ “Predictor”

Into:

✅ Decision engine
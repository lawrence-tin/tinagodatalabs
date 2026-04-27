import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from utils.data_loader import get_connection, load_silver_data
from utils.features import build_input
from core.model_loader import load_model
from utils.optimizer import run_optimization


# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(
    page_title="ContentIQ - AI Video Predictor",
    page_icon="🎬",
    layout="wide"
)

# ---------------------------
# HEADER
# ---------------------------
st.title("🎬 ContentIQ AI")
st.subheader("Predict video performance before you publish")

st.markdown("""
> Upload or describe a video idea and get predicted performance + optimization suggestions.
""")

# ---------------------------
# LOAD DATA + MODEL
# ---------------------------
conn = get_connection()

@st.cache_data(ttl=3600)
def load_data(client_id, platform):
    return load_silver_data(conn, client_id, platform)

# ---------------------------
# SAAS: CLIENT ISOLATION
# ---------------------------
client_id = st.sidebar.selectbox(
    "Client",
    ["All", "team5pm", "mrbeast", "client_a", "client_b"]
)

platform = st.sidebar.selectbox(
    "Platform",
    ["All", "youtube", "tiktok", "instagram", "facebook"]
)

df_silver = load_data(client_id, platform)
model = load_model(client_id, platform)

if df_silver.empty:
    st.warning("No data available")
    st.stop()

# ---------------------------
# NAVIGATION
# ---------------------------
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Overview", "🎬 Predict", "🧪 Simulator", "📊 Insights", "🧠 Strategy"]
)

# =========================================================
# 🏠 OVERVIEW
# =========================================================
if page == "🏠 Overview":

    st.markdown("## 📊 Channel Snapshot")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Videos Analyzed", len(df_silver))
    
    historical_avg_engagement = df_silver['engagement_rate_pct'].mean()
    col2.metric("Avg Engagement", f"{historical_avg_engagement:.2f}%")
    
    col3.metric("Best Video", f"{df_silver['engagement_rate_pct'].max():.2f}%")

    # Channel Health Metric (Last 5 videos vs Historical Average)
    if len(df_silver) >= 5:
        last_5_videos = df_silver.sort_values(by='published_at', ascending=False).head(5)
        last_5_avg_engagement = last_5_videos['engagement_rate_pct'].mean()
        
        if historical_avg_engagement != 0:
            channel_health_delta = ((last_5_avg_engagement - historical_avg_engagement) / historical_avg_engagement) * 100
            col4.metric(
                "Channel Health (Last 5 vs Avg)", 
                f"{last_5_avg_engagement:.2f}%", 
                f"{channel_health_delta:+.1f}% vs Avg"
            )
        else:
            col4.metric("Channel Health (Last 5 vs Avg)", f"{last_5_avg_engagement:.2f}%", "N/A (No historical avg)")
    else:
        col4.metric("Channel Health (Last 5 vs Avg)", "N/A", "Not enough data")

    st.markdown("---")
    st.info("Use the Predict tab to test new video ideas before publishing.")

# =========================================================
# 🎬 PREDICT
# =========================================================
elif page == "🎬 Predict":

    st.markdown("## 🎬 Video Performance Predictor")

    col1, col2 = st.columns(2)

    with col1:
        title = st.text_input("Video Title")
        duration = st.slider("Duration (seconds)", 30, 1800, 480)

        money = st.checkbox("💰 Contains '$'", True)
        question = st.checkbox("❓ Contains '?'")
        numbers = st.checkbox("🔢 Contains numbers")

    with col2:
        hour = st.selectbox("Upload Hour (UTC)", list(range(24)), index=17)
        weekend = st.checkbox("Weekend upload")

    st.markdown("---")

    # ---------------------------
    # SINGLE PREDICTION
    # ---------------------------
    if st.button("🚀 Predict Performance", use_container_width=True):

        input_data = build_input(
            duration, title, money, question, numbers, hour, weekend, df_silver
        )

        prediction = float(model.predict(input_data)[0])
        prediction = max(0, min(prediction, 10))

        st.success(f"🎯 Predicted Engagement: {prediction:.2f}%")

        avg = df_silver["engagement_rate_pct"].mean()
        best = df_silver["engagement_rate_pct"].max()

        c1, c2, c3 = st.columns(3)
        c1.metric("vs Average", f"{((prediction-avg)/avg*100):+.1f}%")
        c2.metric("vs Best", f"{((prediction-best)/best*100):+.1f}%")
        c3.metric("Confidence", "High (MVP Model)")

        st.markdown("### 💡 Recommendations")

        if duration > 900:
            st.warning("Consider shortening video to improve retention")

        if not money:
            st.info("Adding '$' often increases engagement")

        if hour < 14 or hour > 20:
            st.info("Post between 14:00–20:00 UTC")

    # ---------------------------
    # OPTIMIZATION ENGINE
    # ---------------------------
    st.markdown("---")
    st.subheader("⚡ Optimization Engine")

    if st.button("⚡ Run Auto-Optimization", use_container_width=True):
        results = run_optimization(model, df_silver)
        
        st.success("Top 3 Optimized Scenarios Found")
        
        top3 = results.head(3)
        for i, (idx, row) in enumerate(top3.iterrows()):
            st.markdown(f"#### 🏆 Option {i+1}")
            c1, c2, c3 = st.columns(3)
            
            c1.metric("Duration", f"{int(row['duration_seconds']/60)} min")
            c2.metric("Best Time", f"{int(row['publish_hour_utc'])}:00 UTC")
            c3.metric("Engagement", f"{row['predicted_engagement']:.2f}%")
            
            features = []
            if row['has_money_symbol']: features.append("💰 Money Symbol")
            if row['has_question_mark']: features.append("❓ Question Mark")
            if row['has_numbers']: features.append("🔢 Numbers")
            
            st.caption(f"Strategy: {' • '.join(features) if features else 'Standard Title'}")
            st.markdown("---")

    # ---------------------------
    # BULK CSV RANKING
    # ---------------------------
    st.markdown("---")
    st.subheader("📂 Bulk Video Ranking")

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file:

        df_upload = pd.read_csv(uploaded_file)
        predictions = []

        for _, row in df_upload.iterrows():

            input_data = build_input(
                row["duration_seconds"],
                str(row["title"]),
                bool(row["has_money"]),
                bool(row["has_question"]),
                bool(row["has_numbers"]),
                int(row["hour"]),
                False,
                df_silver
            )

            score = float(model.predict(input_data)[0])
            predictions.append(score)

        df_upload["predicted_engagement"] = predictions
        df_upload = df_upload.sort_values("predicted_engagement", ascending=False)

        st.success("Ranked Videos")
        st.dataframe(df_upload, use_container_width=True)

# =========================================================
# 🧪 SIMULATOR
# =========================================================
elif page == "🧪 Simulator":

    st.markdown("## 🧪 What-If Simulator")

    def predict_custom(d, t, m, q, n, h, w):
        input_data = build_input(d, t, m, q, n, h, w, df_silver)
        return float(model.predict(input_data)[0])

    col1, col2 = st.columns(2)

    with col1:
        base_title = st.text_input("Base Title", key="base_title")
        base_duration = st.slider("Base Duration", 30, 1800, 480, key="base_duration")
        base_hour = st.selectbox("Base Hour", list(range(24)), index=17, key="base_hour")

    with col2:
        new_title = st.text_input("New Title", key="new_title")
        new_duration = st.slider("New Duration", 30, 1800, base_duration, key="new_duration")
        new_hour = st.selectbox("New Hour", list(range(24)), index=base_hour, key="new_hour")

        add_money = st.toggle("Add '$'")
        add_question = st.toggle("Add '?'")
        add_numbers = st.toggle("Add numbers")

    if st.button("Run Simulation", use_container_width=True):

        base_score = predict_custom(base_duration, base_title, False, False, False, base_hour, False)
        scenario_score = predict_custom(new_duration, new_title, add_money, add_question, add_numbers, new_hour, False)

        delta = scenario_score - base_score

        c1, c2, c3 = st.columns(3)
        c1.metric("Base", f"{base_score:.2f}%")
        c2.metric("Scenario", f"{scenario_score:.2f}%")
        c3.metric("Impact", f"{delta:+.2f}%")

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Base", x=["Engagement"], y=[base_score]))
        fig.add_trace(go.Bar(name="Scenario", x=["Engagement"], y=[scenario_score]))

        st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 📊 INSIGHTS
# =========================================================
elif page == "📊 Insights":

    st.markdown("## 📊 Historical Insights")

    st.bar_chart(df_silver.groupby("duration_seconds")["engagement_rate_pct"].mean())
    st.line_chart(df_silver.groupby(df_silver["published_at"].dt.month)["engagement_rate_pct"].mean())

# =========================================================
# 🧠 STRATEGY
# =========================================================
elif page == "🧠 Strategy":

    st.markdown("## 🧠 Content Strategy")

    st.markdown("""
    ### 🔥 What works best:
    - Videos between 5–10 minutes  
    - Titles with emotional triggers  
    - Posting between 14:00–20:00 UTC  
    """)

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("---")
st.caption(f"ContentIQ MVP • {datetime.now().strftime('%Y-%m-%d')}")
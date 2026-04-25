import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from utils.data_loader import get_connection, load_silver_data
from utils.features import build_input
from core.model_loader import load_model
from utils.optimizer import auto_optimize, top_scenarios


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
    ["team5pm", "client_a", "client_b"]
)

platform = st.sidebar.selectbox(
    "Platform",
    ["youtube", "tiktok", "instagram", "facebook"]
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

    col1, col2, col3 = st.columns(3)

    col1.metric("Videos Analyzed", len(df_silver))
    col2.metric("Avg Engagement", f"{df_silver['engagement_rate_pct'].mean():.2f}%")
    col3.metric("Best Video", f"{df_silver['engagement_rate_pct'].max():.2f}%")

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

    col1, col2 = st.columns(2)

    with col1:
        if st.button("⚡ Auto Optimize", use_container_width=True):

            score, config = auto_optimize(model, df_silver)

            st.success(f"Best Possible Engagement: {score:.2f}%")
            st.json(config)

    with col2:
        if st.button("🏆 Top 3 Scenarios", use_container_width=True):

            scenarios = top_scenarios(model, df_silver)

            for i, s in enumerate(scenarios, 1):
                st.markdown(f"### #{i}")
                st.write(s)

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
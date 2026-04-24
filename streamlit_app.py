import streamlit as st
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
import plotly.graph_objects as go

from utils.data_loader import get_connection, load_silver_data
from utils.features import build_input
from utils.prediction import load_model

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(
    page_title="ContentIQ - AI Video Predictor",
    page_icon="🎬",
    layout="wide"
)

# ---------------------------
# HEADER (PRODUCT STYLE)
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
def load_data():
    return load_silver_data(conn)

df_silver = load_data()
model = load_model()

# ---------------------------
# NAVIGATION (SIMPLE PRODUCT UI)
# ---------------------------
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Overview", "🎬 Predict", "📊 Insights", "🧠 Strategy"]
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
# 🎬 PREDICT (CORE PRODUCT)
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

    if st.button("🚀 Predict Performance", use_container_width=True):

        input_data = build_input(
            duration,
            title,
            money,
            question,
            numbers,
            hour,
            weekend,
            df_silver
        )

        prediction = model.predict(input_data)[0]

        # Clamp
        prediction = max(0, min(prediction, 10))

        st.success(f"🎯 Predicted Engagement: {prediction:.2f}%")

        avg = df_silver["engagement_rate_pct"].mean()
        best = df_silver["engagement_rate_pct"].max()

        col1, col2, col3 = st.columns(3)

        col1.metric("vs Average", f"{((prediction-avg)/avg*100):+.1f}%")
        col2.metric("vs Best", f"{((prediction-best)/best*100):+.1f}%")
        col3.metric("Confidence", "High (MVP Model)")

        st.markdown("### 💡 Recommendations")

        if duration > 900:
            st.warning("Consider shortening video to improve retention")

        if not money:
            st.info("Adding '$' often increases engagement in this dataset")

        if hour < 14 or hour > 20:
            st.info("Peak performance usually occurs 14:00–20:00 UTC")

# =========================================================
# 📊 INSIGHTS
# =========================================================
elif page == "📊 Insights":

    st.markdown("## 📊 Historical Performance Insights")

    st.bar_chart(df_silver.groupby("duration_seconds")["engagement_rate_pct"].mean())

    st.markdown("---")

    st.line_chart(df_silver.groupby(df_silver["published_at"].dt.month)["engagement_rate_pct"].mean())

# =========================================================
# 🧠 STRATEGY
# =========================================================
elif page == "🧠 Strategy":

    st.markdown("## 🧠 Content Strategy Engine")

    st.info("AI-generated insights based on historical performance patterns.")

    st.markdown("""
    ### 🔥 What works best:
    - Videos between 5–10 minutes
    - Titles with emotional triggers
    - Uploading during peak hours (14:00–20:00 UTC)
    """)

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("---")
st.caption(f"ContentIQ MVP • {datetime.now().strftime('%Y-%m-%d')}")
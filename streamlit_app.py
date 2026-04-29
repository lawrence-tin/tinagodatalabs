import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from utils.data_loader import get_connection, load_silver_data, authenticate_user, fetch_user_clients, create_client, save_platform_credentials, fetch_brands, create_brand
from core.model_loader import load_model
from utils.optimizer import run_optimization
from utils.features import build_features


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

# ---------------------------
# AUTHENTICATION
# ---------------------------
if "user" not in st.session_state:
    st.sidebar.title("Login")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        user = authenticate_user(conn, email, password)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials")
    st.stop() # Stop execution until user logs in

user_id = st.session_state["user"]["user_id"]
user_email = st.session_state["user"]["email"]

st.sidebar.write(f"Logged in as: {user_email}")
if st.sidebar.button("Logout"):
    del st.session_state["user"]
    st.rerun()


@st.cache_data(ttl=3600)
def load_data(org_id, brand_id, platform):
    return load_silver_data(conn, org_id, brand_id, platform)

# ---------------------------
# SAAS: ORGANIZATION & BRAND SELECTION
# ---------------------------
user_orgs = fetch_user_clients(conn, user_id)

if not user_orgs:
    st.warning("You are not assigned to any organizations. Please contact an admin or create one in Settings.")
    st.stop()

org_options = {org['client_name']: org['client_id'] for org in user_orgs}
selected_org_name = st.sidebar.selectbox(
    "Select Organization",
    list(org_options.keys())
)
org_id = org_options[selected_org_name]

brands = fetch_brands(conn, org_id)
if not brands:
    st.sidebar.warning(f"No brands found for {selected_org_name}")
    brand_id = "All"
else:
    brand_options = {b['brand_name']: b['brand_id'] for b in brands}
    brand_options["All Brands"] = "All"
    selected_brand_name = st.sidebar.selectbox("Select Brand", list(brand_options.keys()))
    brand_id = brand_options[selected_brand_name]

# Get the user's role for the currently selected client
user_role = next(c['role'] for c in user_orgs if c['client_id'] == org_id)

platform = st.sidebar.selectbox(
    "Platform",
    ["All", "youtube", "tiktok", "instagram", "facebook"] # Keep "All" for platform filtering
)

df_silver = load_data(org_id, brand_id, platform)

# SAAS: Model Loading with fallback training (Step 5 & 6)
try:
    model = load_model(org_id, brand_id)
except Exception:
    st.sidebar.warning(f"No model found for {brand_id}. Training now...")
    from core.train_model import train_model
    try:
        model = train_model(org_id, brand_id)
        st.sidebar.success("Model trained successfully!")
    except Exception as e:
        st.sidebar.error(f"Training failed: {e}")
        st.stop()

if df_silver.empty:
    st.info("No data found for the selected filters. Try changing your selection or check your credentials.")
    st.stop()

# ---------------------------
# NAVIGATION
# ---------------------------
nav_options = ["🏠 Overview", "🎬 Predict", "🧪 Simulator", "📊 Insights", "🧠 Strategy"]
if user_role == 'admin':
    nav_options.append("⚙️ Settings")
    st.sidebar.success(f"🔓 Admin Access: {selected_org_name}")

page = st.sidebar.radio("Navigation", nav_options)

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

        input_data = build_features(
            duration=duration,
            title=title,
            hour=hour,
            weekend=weekend,
            df_silver=df_silver,
            platform_name=platform
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

        # Strategy feedback logic (re-evaluate based on new features)
        if hour < 14 or hour > 20: # This is still a valid general recommendation
            st.info("Post between 14:00–20:00 UTC")

    # ---------------------------
    # OPTIMIZATION ENGINE
    # ---------------------------
    st.markdown("---")
    st.subheader("⚡ Optimization Engine")

    if st.button("⚡ Run Auto-Optimization", use_container_width=True):
        results = run_optimization(model, df_silver, platform)
        
        avg_engagement = df_silver["engagement_rate_pct"].mean()
        
        st.markdown("### 🚀 Top 3 Performance Blueprints")
        st.write("We simulated over 3,000 combinations to find the highest probability winners for your brand.")

        tabs = st.tabs(["🏆 Blueprint 1", "🥈 Blueprint 2", "🥉 Blueprint 3"])
        
        for i, (idx, row) in enumerate(results.head(3).iterrows()):
            with tabs[i]:
                c1, c2, c3, c4 = st.columns(4)
                
                uplift = ((row['predicted_engagement'] - avg_engagement) / avg_engagement) * 100
                
                c1.metric("Predicted Rate", f"{row['predicted_engagement']:.2f}%")
                c2.metric("Target Uplift", f"{uplift:+.1f}%", delta_color="normal")
                c3.metric("Best Duration", f"{int(row['duration_seconds']/60)}m {int(row['duration_seconds']%60)}s")
                c4.metric("Post Time", f"{int(row['publish_hour_utc'])}:00", "UTC")
                
                # Strategy tags
                tags = []
                if row['has_money_symbol']: tags.append("💰 Include Price/Money")
                if row['has_question_mark']: tags.append("❓ Use Questions")
                if row['has_numbers']: tags.append("🔢 Use List/Numbers")
                if row['is_weekend']: tags.append("🗓️ Weekend Post")
                else: tags.append("💼 Weekday Post")
                
                st.markdown(f"**Recommended Strategy:** {' • '.join(tags)}")

        # Optimization Insights
        st.markdown("#### 🧠 Optimization Insights")
        top_10 = results.head(10)
        
        col_a, col_b = st.columns(2)
        with col_a:
            money_freq = top_10['has_money_symbol'].mean()
            if money_freq > 0.7:
                st.info("💡 **Insight:** 💰 Money symbols are present in 70%+ of your top performing simulations. This is your primary growth lever.")
            
            best_hour = top_10['publish_hour_utc'].mode()[0]
            st.info(f"💡 **Insight:** ⏰ The most consistent high-engagement window for you is around **{best_hour}:00 UTC**.")

        with col_b:
            # Chart Comparison
            chart_df = results.head(5).copy()
            chart_df["Scenario"] = [f"Opt {i+1}" for i in range(len(chart_df))]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_df["Scenario"], y=chart_df["predicted_engagement"], name="Optimized"))
            fig.add_hline(y=avg_engagement, line_dash="dash", line_color="red", annotation_text="Brand Avg")
            fig.update_layout(height=200, margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

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

            input_data = build_features(
                duration=row["duration_seconds"],
                title=str(row["title"]),
                hour=int(row["hour"]),
                weekend=False,
                df_silver=df_silver,
                platform_name=platform
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

    def predict_custom(d, t, h, w, p):
        input_data = build_features(d, t, h, w, df_silver, p)
        return float(model.predict(input_data)[0])

    col1, col2, col3 = st.columns(3)

    with col1:
        base_title = st.text_input("Base Title", key="base_title")
        base_duration = st.slider("Base Duration", 30, 1800, 480, key="base_duration")
        base_hour = st.selectbox("Base Hour", list(range(24)), index=17, key="base_hour")

    with col2:
        new_title = st.text_input("New Title", key="new_title")
        new_duration = st.slider("New Duration", 30, 1800, base_duration, key="new_duration")
        new_hour = st.selectbox("New Hour", list(range(24)), index=base_hour, key="new_hour")

    with col3:
        base_money = st.checkbox("Base: Contains '$'", False, key="base_money")
        base_question = st.checkbox("Base: Contains '?'", False, key="base_question")
        base_numbers = st.checkbox("Base: Contains numbers", False, key="base_numbers")
        
        new_money = st.checkbox("New: Contains '$'", False, key="new_money")
        new_question = st.checkbox("New: Contains '?'", False, key="new_question")
        new_numbers = st.checkbox("New: Contains numbers", False, key="new_numbers")

    if st.button("Run Simulation", use_container_width=True):

        base_score = predict_custom(base_duration, base_title, base_hour, False, platform)
        scenario_score = predict_custom(new_duration, new_title, new_hour, False, platform)

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

# =========================================================
# ⚙️ SETTINGS (Onboarding Flow)
# =========================================================
elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Account Settings")
    
    tab1, tab2, tab3 = st.tabs(["🏢 New Organization", "🏷️ New Brand", "🔗 Connect Platforms"])
    
    with tab1:
        st.subheader("Create a new Client Workspace")
        new_client_name = st.text_input("Client Name (e.g. MrBeast, Red Bull)")
        if st.button("Create Workspace"):
            if new_client_name:
                if create_client(conn, user_id, new_client_name):
                    st.success(f"Client '{new_client_name}' created! Refreshing...")
                    st.rerun()
            else:
                st.error("Please enter a name.")

    with tab2:
        st.subheader(f"Add a Brand to {selected_org_name}")
        new_brand_name = st.text_input("Brand Name (e.g. Nike, MrBeast Gaming)")
        if st.button("Create Brand"):
            if new_brand_name:
                if create_brand(conn, org_id, new_brand_name):
                    st.success(f"Brand '{new_brand_name}' created successfully!")
                    st.rerun()
            else:
                st.error("Please enter a brand name.")

    with tab3:
        st.subheader(f"Connect Platforms for {selected_org_name}")
        
        target_platform = st.selectbox("Platform", ["youtube", "facebook", "instagram", "tiktok"])
        # Handle case where no brands exist yet, default to org_id or an empty list
        brand_ids_for_selection = [b['brand_id'] for b in brands] if brands else [org_id]
        target_brand_id = st.selectbox("Select Brand to Link", brand_ids_for_selection)
        account_id = st.text_input("Platform Account ID / Channel ID")
        api_key = st.text_input("API Key / Access Token", type="password")
        
        if st.button("Link Platform"):
            if account_id and api_key:
                success = save_platform_credentials(
                    conn, 
                    org_id,
                    target_brand_id,
                    target_platform, 
                    account_id, 
                    api_key
                )
                if success:
                    st.success(f"Successfully linked {target_platform}!")
                    st.info("The ingestion engine will pick up this new client on the next run.")
            else:
                st.error("Please fill in all fields.")


# ---------------------------
# FOOTER
# ---------------------------
st.markdown("---")
st.caption(f"ContentIQ MVP • {datetime.now().strftime('%Y-%m-%d')}")
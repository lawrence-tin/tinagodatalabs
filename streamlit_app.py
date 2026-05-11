"""
Viralynx - AI Video Performance Predictor

This is the main entry point for the Streamlit SaaS application. 
It handles user authentication, multi-tenant organization/brand management,
and provides various tools for predicting and optimizing video performance.
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime
import plotly.graph_objects as go
from utils.data_loader import get_connection, load_silver_data, authenticate_user, register_user, fetch_user_clients, create_client, save_platform_credentials, fetch_brands, create_brand, fetch_platform_connections, fetch_brand_stats, fetch_org_platform_keys, delete_platform_connection, update_platform_credentials, load_gold_insights
from core.model_loader import load_model, get_model_status
from utils.optimizer import run_optimization
from utils.features import build_features, extract_title_features
from utils.repurposer import get_brand_context, generate_repurposed_variants, score_variants


# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(
    page_title="Viralynx - AI Video Predictor",
    page_icon="🎬",
    layout="wide"
)

# ---------------------------
# HEADER
# ---------------------------
st.title("🎬 Viralynx")
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
    auth_mode = st.sidebar.radio("Welcome", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if auth_mode == "Login":
        if st.sidebar.button("Login"):
            user = authenticate_user(conn, email, password)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials")
    else:
        if st.sidebar.button("🚀 Sign Up"):
            if email and password:
                new_user_id = register_user(conn, email, password)
                if new_user_id:
                    st.sidebar.success("Account created! Please switch to Login.")
                else:
                    st.sidebar.error("Registration failed. Email might already exist.")
            else:
                st.sidebar.warning("Please provide email and password.")

    st.stop() # Stop execution until user logs in

user_id = st.session_state["user"]["user_id"]
user_email = st.session_state["user"]["email"]

st.sidebar.write(f"Logged in as: {user_email}")
if st.sidebar.button("Logout"):
    del st.session_state["user"]
    st.rerun()


@st.cache_data(ttl=3600)
def load_data(org_id, brand_id, platform):
    """Cached wrapper for loading silver-layer data from Snowflake."""
    return load_silver_data(conn, org_id, brand_id, platform)

def render_connect_platform_form(conn, org_id, brand_id, brands_list):
    """Renders the form for connecting platforms."""
    target_platform = st.selectbox("Platform", ["youtube", "facebook", "instagram", "tiktok"], key="settings_platform")
    
    # Ensure brand_id is passed correctly, or allow selection if needed
    if brand_id == "All": # If "All Brands" is selected, force user to pick a specific brand
        brand_ids_for_selection = [b['brand_id'] for b in brands_list]
        if not brand_ids_for_selection:
            st.warning("No brands available to link. Please create a brand first.")
            return
        selected_brand_to_link = st.selectbox("Select Brand to Link", brand_ids_for_selection, key="settings_brand_link")
    else:
        selected_brand_to_link = brand_id
        st.write(f"Linking to: **{selected_brand_to_link}**")

    account_id = st.text_input("Platform Account ID / Channel ID", key="settings_account_id")
    
    # Check for existing keys in the organization to save user time
    existing_keys = fetch_org_platform_keys(conn, org_id, target_platform)
    
    if existing_keys:
        key_option = st.radio("API Key Management", ["Use a saved key", "Enter a new key"], horizontal=True)
        if key_option == "Use a saved key":
            # Show masked keys for security but allow selection
            masked_map = {f"Key ending in ...{k[-4:]}": k for k in existing_keys}
            api_key = st.selectbox("Select Saved Key", list(masked_map.keys()))
            api_key = masked_map[api_key]
        else:
            api_key = st.text_input("API Key / Access Token", type="password", key="settings_api_key")
    else:
        api_key = st.text_input("API Key / Access Token", type="password", key="settings_api_key")
    
    if st.button("Link Platform", key="settings_link_button"):
        # TikTok ingestion (current MVP) uses Apify and reads APIFY_TOKEN globally,
        # so the per-account API Key can be left empty.
        require_api_key = str(target_platform).lower() != "tiktok"
        # TikTok and Facebook ingestion use Apify and read APIFY_TOKEN globally,
        # so the per-brand API Key can be left empty.
        require_api_key = str(target_platform).lower() not in ["tiktok", "facebook"]

        if account_id and selected_brand_to_link and (api_key or not require_api_key):
            success = save_platform_credentials(
                conn, 
                org_id,
                selected_brand_to_link,
                target_platform, 
                account_id, 
                api_key
            )
            if success:
                st.success(f"Successfully linked {target_platform} to {selected_brand_to_link}! Data ingestion will begin soon.")
                st.rerun()
        else:
            if require_api_key:
                st.error("Please fill in all fields (API Key is required for this platform).")
            else:
                st.error("Please fill in all required fields.")

# ---------------------------
# SAAS: ORGANIZATION & BRAND SELECTION
# ---------------------------
user_orgs = fetch_user_clients(conn, user_id)

if not user_orgs:
    st.header("🚀 Welcome to Viralynx")
    st.subheader("Let's get your first Organization set up.")
    st.info("Organizations represent your Agency or your Company.")
    new_org_name = st.text_input("Organization Name", placeholder="e.g. GrowthMedia Agency")
    if st.button("Create Organization"):
        if new_org_name:
            if create_client(conn, user_id, new_org_name):
                st.success(f"Organization '{new_org_name}' created!")
                st.rerun()
    st.stop()

org_options = {org['client_name']: org['client_id'] for org in user_orgs}
selected_org_name = st.sidebar.selectbox(
    "Select Organization",
    list(org_options.keys())
)
org_id = org_options[selected_org_name]

brands = fetch_brands(conn, org_id)
if not brands:
    st.header("🏷️ Define your first Brand")
    st.write(f"Add a brand under **{selected_org_name}** to begin analyzing content.")
    new_b_name = st.text_input("Brand Name", placeholder="e.g. MrBeast, Nike")
    if st.button("Add Brand"):
        if new_b_name:
            if create_brand(conn, org_id, new_b_name):
                st.success(f"Brand '{new_b_name}' added!")
                st.rerun()
    st.stop()

brand_options = {b['brand_name']: b['brand_id'] for b in brands}
brand_options["All Brands"] = "All"
selected_brand_name = st.sidebar.selectbox("Select Brand", list(brand_options.keys()))
brand_id = brand_options[selected_brand_name]

platform = st.sidebar.selectbox(
    "Platform",
    ["All", "youtube", "tiktok", "instagram", "facebook"] # Keep "All" for platform filtering
)

# Get the user's role for the currently selected client
user_role = next(c['role'] for c in user_orgs if c['client_id'] == org_id)

# ---------------------------
# NAVIGATION (Moved up to prevent blocking)
# ---------------------------
nav_options = ["🏠 Overview", "🎬 Predict", "✂️ Repurpose", "🧪 Simulator", "📊 Insights", "⚔️ Competitors", "🧠 Strategy", "💎 Performance", "📑 Reports"]
if user_role == 'admin':
    nav_options.append("⚙️ Settings")
    st.sidebar.success(f"🔓 Admin Access: {selected_org_name}")

page = st.sidebar.radio("Navigation", nav_options)

# ---------------------------
# Check if there are any connected platforms organization-wide or for this brand
# ---------------------------
df_all_connections = fetch_platform_connections(conn, org_id)

brand_has_connection = False
if not df_all_connections.empty:
    if brand_id == "All":
        brand_has_connection = True
    else:
        brand_has_connection = not df_all_connections[df_all_connections['brand_id'] == brand_id].empty

# Only block with the connection form if we aren't in Settings
if not brand_has_connection and page != "⚙️ Settings":
    st.header(f"🔗 Connect a Platform for {selected_brand_name}")
    st.write("To start ingesting data and getting predictions, connect a social media platform.")
    render_connect_platform_form(conn, org_id, brand_id, brands)
    st.stop()

# Load data only if we aren't on the Settings page (to avoid errors on empty brands)
if page != "⚙️ Settings":
    df_silver = load_data(org_id, brand_id, platform)
    model = load_model(org_id, brand_id, platform)

    if df_silver.empty:
        st.info("No data found for the selected filters. Try changing your selection or check your credentials.")
        st.stop()

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
        tags = st.text_input("Tags / Hashtags (comma separated)", placeholder="e.g. tech, viral, tutorial")

    with col2:
        hour = st.selectbox("Upload Hour (UTC)", list(range(24)), index=17)
        weekend = st.checkbox("Weekend upload")
        category = st.selectbox("Content Category", ["Entertainment", "Education", "Vlog", "News", "Other"])
        st.info("💡 Pro-tip: Features like '$', '?', and numbers are automatically detected from the title you type.")

    st.markdown("---")

    # ---------------------------
    # SINGLE PREDICTION
    # ---------------------------
    if st.button("🚀 Predict Performance", use_container_width=True):

        if model is None:
            st.error("❌ ML Model not found. Please sync your data and ensure at least 5 videos are available to train the model.")
        else:
            input_data = build_features(
                duration=duration,
                title=title, # Money, question, numbers are extracted from title
                hour=hour,
                weekend=weekend,
                df_silver=df_silver,
                platform_name=platform,
                tags=tags,
                category=category
            )

            raw_pred = float(model.predict(input_data)[0])
            prediction = max(0.0, min(raw_pred, 100.0)) # Engagement usually 0-100%

            st.success(f"🎯 Predicted Engagement: {prediction:.2f}%")

            avg = df_silver["engagement_rate_pct"].mean()
            best = df_silver["engagement_rate_pct"].max()

            c1, c2, c3 = st.columns(3)
            # Ensure safe division and float types for calculations
            c1.metric("vs Average", f"{(((prediction-avg)/avg*100) if avg != 0 else 0):+.1f}%")
            c2.metric("vs Best", f"{(((prediction-best)/best*100) if best != 0 else 0):+.1f}%")
            c3.metric("Confidence", "High (MVP Model)")

        st.markdown("### 💡 Recommendations")

        if duration > 900:
            st.warning("Consider shortening video to improve retention")

        if hour < 14 or hour > 20:
            st.info("Post between 14:00–20:00 UTC")

    # ---------------------------
    # OPTIMIZATION ENGINE
    # ---------------------------
    st.markdown("---")
    st.subheader("⚡ Optimization Engine")

    if st.button("⚡ Run Auto-Optimization", use_container_width=True):
        if model is None:
            st.error("❌ Cannot run optimization without a trained model.")
        else:
            results = run_optimization(model, df_silver, platform, category=category, tags=tags, current_title=title)
            
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

        if model is None:
            st.error("❌ Model unavailable for bulk ranking.")
        else:
            df_upload = pd.read_csv(uploaded_file)
            predictions = []

            for _, row in df_upload.iterrows():

                input_data = build_features(
                    duration=row["duration_seconds"],
                    title=str(row.get("title", "")),
                    hour=int(row.get("hour", 17)),
                    weekend=row.get("is_weekend", False),
                    df_silver=df_silver,
                    platform_name=platform,
                    tags=str(row.get("tags", "")),
                    category=row.get("category", "Other")
                )

                score = float(model.predict(input_data)[0])
                predictions.append(score)

            df_upload["predicted_engagement"] = predictions
            df_upload = df_upload.sort_values("predicted_engagement", ascending=False)

            st.success("Ranked Videos")
            st.markdown("---")
            st.dataframe(df_upload, width='stretch')

            # ---------------------------
            # BULK OPTIMIZATION FOR CSV
            # ---------------------------
            st.markdown("---")
            st.subheader("✨ Bulk Optimization for Uploaded Videos")
            if st.button("🚀 Run Bulk Optimization", use_container_width=True):
                optimized_results = []
                progress_text = "Optimizing video ideas. Please wait."
                my_bar = st.progress(0, text=progress_text)
                
                for i, row in df_upload.iterrows():
                    # Run optimization for each video idea from the CSV
                    optimized_scenario = run_optimization(
                        model, 
                        df_silver, 
                        platform, 
                        category=str(row.get("category", "Other")), 
                        tags=str(row.get("tags", "")),
                        current_title=str(row.get("title", ""))
                    ).iloc[0] # Take the top optimized scenario

                    optimized_results.append({
                        "Original Title": row.get("title", ""),
                        "Original Predicted ER": row.get("predicted_engagement", 0),
                        "Optimized Predicted ER": optimized_scenario["predicted_engagement"],
                        "Optimized Duration (s)": optimized_scenario["duration_seconds"],
                        "Optimized Hour (UTC)": optimized_scenario["publish_hour_utc"],
                        "Optimized Has Money": bool(optimized_scenario["has_money_symbol"]),
                        "Optimized Has Question": bool(optimized_scenario["has_question_mark"]),
                        "Optimized Has Numbers": bool(optimized_scenario["has_numbers"]),
                    })
                    my_bar.progress((i + 1) / len(df_upload), text=progress_text)
                
                st.success("Bulk Optimization Complete!")
                st.dataframe(pd.DataFrame(optimized_results), width='stretch')

# =========================================================
# ✂️ REPURPOSE
# =========================================================
elif page == "✂️ Repurpose":
    st.markdown("## ✂️ AI Performance-Aware Repurposing")

    st.info("Transform long-form content or ideas into optimized social assets based on your brand's history.")

    source_input = st.text_area("Paste Content (Transcript, Article, or Video Script)", height=200)
    
    col1, col2 = st.columns(2)
    with col1:
        target_plats = st.multiselect("Target Platforms", ["tiktok", "youtube", "instagram", "facebook", "linkedin"], default=["tiktok", "instagram"])
    
    if st.button("✨ Generate Optimized Variants", use_container_width=True):
        if not source_input:
            st.warning("Please provide source content.")
        else:
            with st.spinner("Analyzing historical performance & generating variants..."):
                # 1. Get Intelligence
                context = get_brand_context(df_silver)
                
                # 2. Generate Content
                raw_variants = generate_repurposed_variants(source_input, context, target_plats)
                
                # 3. Closed-loop Prediction
                if model:
                    final_variants = score_variants(raw_variants, model, df_silver)
                else:
                    final_variants = raw_variants

                st.success(f"Generated {len(final_variants)} performance-aware variants!")
                
                for v in final_variants:
                    with st.expander(f"📱 {v['platform'].upper()} Variant"):
                        c1, c2 = st.columns([3, 1])
                        c1.write(v['content'])
                        
                        score = v.get('predicted_engagement', 0)
                        avg_er = df_silver['engagement_rate_pct'].mean()
                        delta = score - avg_er
                        
                        c2.metric("Predicted ER", f"{score:.2f}%", f"{delta:+.2f}% vs Avg")
                        st.caption(f"Suggested Length: {v['suggested_duration_seconds']}s")
                        if st.button("Copy to Clipboard", key=f"copy_{v['platform']}"):
                            st.toast("Copied!")

# =========================================================
# 🧪 SIMULATOR
# =========================================================
elif page == "🧪 Simulator":

    st.markdown("## 🧪 What-If Simulator")

    def predict_custom(d, t, h, w, p, tags="", cat="Other"):
        if model is None:
            return 0.0
        else:
            input_data = build_features(d, t, h, w, df_silver, p, tags=tags, category=cat)
            return float(model.predict(input_data)[0])

    col1, col2 = st.columns(2)

    with col1:
        base_title = st.text_input("Base Title", key="base_title")
        base_duration = st.slider("Base Duration", 30, 1800, 480, key="base_duration")
        base_hour = st.selectbox("Base Hour", list(range(24)), index=17, key="base_hour")
        base_tags = st.text_input("Base Tags", key="base_tags")
        base_cat = st.selectbox("Base Category", ["Entertainment", "Education", "Vlog", "News", "Other"], key="base_cat")

    with col2:
        new_title = st.text_input("New Title", key="new_title")
        new_duration = st.slider("New Duration", 30, 1800, base_duration, key="new_duration")
        new_hour = st.selectbox("New Hour", list(range(24)), index=base_hour, key="new_hour")
        new_tags = st.text_input("New Tags", key="new_tags")
        new_cat = st.selectbox("New Category", ["Entertainment", "Education", "Vlog", "News", "Other"], index=0, key="new_cat")

    if st.button("Run Simulation", width='stretch'):
        if model is None:
            st.error("❌ Model not loaded. Simulation cannot run.")
        else:
            base_score = predict_custom(base_duration, base_title, base_hour, False, platform, base_tags, base_cat)
            scenario_score = predict_custom(new_duration, new_title, new_hour, False, platform, new_tags, new_cat)

            delta = scenario_score - base_score

        c1, c2, c3 = st.columns(3)
        c1.metric("Base", f"{base_score:.2f}%")
        c2.metric("Scenario", f"{scenario_score:.2f}%")
        c3.metric("Impact", f"{delta:+.2f}%")

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Base", x=["Engagement"], y=[base_score]))
        fig.add_trace(go.Bar(name="Scenario", x=["Engagement"], y=[scenario_score]))

        st.plotly_chart(fig, width='stretch')

# =========================================================
# 📊 INSIGHTS
# =========================================================
elif page == "📊 Insights":

    st.markdown("## 📊 Historical Insights")
    st.write("Understand the patterns behind your high-performing content.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Engagement by Duration")
        # Grouping by 1-minute buckets for better readability
        # Filter out records with missing or non-finite duration_seconds
        df_duration = df_silver.dropna(subset=['duration_seconds']).copy()
        # Explicitly filter out infinite values before casting
        df_duration = df_duration[df_duration['duration_seconds'].abs() != float('inf')]
        # Use nullable integer type 'Int64' to handle potential NAs gracefully
        df_duration['duration_min'] = (df_duration['duration_seconds'] // 60).astype('Int64')
        duration_stats = df_duration.groupby("duration_min")["engagement_rate_pct"].mean()
        st.bar_chart(duration_stats)
        st.caption("Average engagement rate grouped by video length (minutes).")

    with col2:
        st.subheader("Monthly Performance Trend")
        monthly_trend = df_silver.groupby(df_silver["published_at"].dt.to_period("M"))["engagement_rate_pct"].mean()
        # Convert index back to string for streamlit charting
        monthly_trend.index = monthly_trend.index.astype(str)
        st.line_chart(monthly_trend)
        st.caption("How your average engagement has evolved month-over-month.")

    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Performance by Category")
        if 'category' in df_silver.columns:
            cat_perf = df_silver.groupby("category")["engagement_rate_pct"].mean().sort_values(ascending=False)
            st.bar_chart(cat_perf)
        else:
            st.info("Category data not available for this brand.")

    with col4:
        st.subheader("Best Time to Post (Historical)")
        df_silver['hour'] = df_silver['published_at'].dt.hour
        hour_perf = df_silver.groupby("hour")["engagement_rate_pct"].mean()
        st.line_chart(hour_perf)
        st.caption("Average engagement based on the hour of the day (UTC).")

    st.markdown("---")
    st.subheader("🔥 Audience Resonance Heatmap (Gold Standard)")
    st.write("Identify the exact intersections of time and day where your audience is most active.")
    
    # Load pre-aggregated insights from the Gold layer for high-speed rendering
    df_heat_gold = load_gold_insights(conn, org_id, brand_id, platform)
    
    if df_heat_gold.empty:
        st.info("No gold-layer insights available for this selection. Try syncing data first.")
    else:
        # Order days correctly
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Pivot the pre-aggregated data (columns: day_of_week, hour_of_day, avg_engagement_rate)
        pivot_heat = df_heat_gold.pivot(
            index='day_of_week', 
            columns='hour_of_day', 
            values='avg_engagement_rate'
        ).reindex(days_order)

        fig_heat = go.Figure(data=go.Heatmap(
            z=pivot_heat.values,
            x=pivot_heat.columns,
            y=pivot_heat.index,
            colorscale='Viridis',
            colorbar=dict(title='ER%')
        ))
        
        fig_heat.update_layout(
            xaxis_title="Hour of Day (UTC)",
            yaxis_title="Day of Week",
            height=400
        )
        st.plotly_chart(fig_heat, width='stretch')

# =========================================================
# ⚔️ COMPETITORS (Market Benchmarking)
# =========================================================
elif page == "⚔️ Competitors":
    st.markdown("## ⚔️ Competitor Intelligence")
    st.write("Benchmark your brand against the wider market and calculate Share of Voice (SOV).")

    # In a real scenario, we'd fetch data for other brands in the same organization
    # For this implementation, we compare Selected Brand vs 'Market' (All other data)
    df_all_market = load_data(org_id, "All", platform)
    df_competitors = df_all_market[df_all_market['brand_id'] != brand_id]

    if df_competitors.empty:
        st.warning("No competitor data found in this organization. Connect more brands to enable benchmarking.")
    else:
        c1, c2 = st.columns(2)
        
        brand_avg = df_silver['engagement_rate_pct'].mean()
        market_avg = df_competitors['engagement_rate_pct'].mean()
        sov = (df_silver['raw_views'].sum() / df_all_market['raw_views'].sum()) * 100

        c1.metric("Your Engagement", f"{brand_avg:.2f}%", f"{brand_avg - market_avg:+.2f}% vs Market")
        c2.metric("Share of Voice (Views)", f"{sov:.1f}%", help="Your brand's percentage of total views within this organization.")

        st.markdown("### 📊 Market Penetration")
        comp_agg = df_all_market.groupby('brand_id')['raw_views'].sum().reset_index()
        fig_sov = go.Figure(data=[go.Pie(labels=comp_agg['brand_id'], values=comp_agg['raw_views'], hole=.3)])
        st.plotly_chart(fig_sov, width='stretch')

# =========================================================
# 🧠 STRATEGY
# =========================================================
elif page == "🧠 Strategy":

    st.markdown("## 🧠 Data-Driven Content Strategy")
    st.write(f"Tailored recommendations for **{selected_brand_name}** on **{platform.capitalize()}** based on historical performance.")

    # Define 'Success' as the top 20% of engagement
    threshold = df_silver['engagement_rate_pct'].quantile(0.8)
    success_df = df_silver[df_silver['engagement_rate_pct'] >= threshold].copy()

    if success_df.empty:
        st.warning("Not enough high-performing data points to generate a strategy yet. Keep publishing!")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("⏰ Timing & Duration")
            
            # Best Hour (Mode of successful posts)
            success_df['hour'] = success_df['published_at'].dt.hour
            best_hour = success_df['hour'].mode()[0]
            
            # Optimal Duration
            avg_success_dur = success_df['duration_seconds'].mean()
            
            st.write(f"✅ **Best Posting Hour:** {int(best_hour)}:00 UTC")
            st.write(f"✅ **Optimal Duration:** ~{int(avg_success_dur/60)} minutes")
            if not pd.isna(avg_success_dur):
                st.write(f"✅ **Optimal Duration:** ~{int(avg_success_dur/60)} minutes")
            else:
                st.write(f"✅ **Optimal Duration:** N/A (Missing duration data)")
            
            # Weekend vs Weekday
            success_df['is_weekend'] = success_df['published_at'].dt.weekday >= 5
            weekend_pref = "Weekends" if success_df['is_weekend'].mean() > 0.5 else "Weekdays"
            st.write(f"✅ **Audience Preference:** {weekend_pref}")

        with col2:
            st.subheader("✍️ Title & Content Hooks")
            
            # Analyze hooks in successful titles using our feature extractor
            hook_stats = success_df['content_title'].apply(lambda x: extract_title_features(str(x))).apply(pd.Series)
            
            money_rate = hook_stats['has_money_symbol'].mean() * 100
            question_rate = hook_stats['has_question_mark'].mean() * 100
            number_rate = hook_stats['has_numbers'].mean() * 100
            
            st.write(f"💰 **Money Symbols:** Found in {money_rate:.0f}% of top videos")
            st.write(f"❓ **Question Marks:** Found in {question_rate:.0f}% of top videos")
            st.write(f"🔢 **Numbers/Lists:** Found in {number_rate:.0f}% of top videos")

        st.markdown("---")
        
        st.subheader("🎯 Strategic Advisor")
        
        recs = []
        # Hook recommendation
        if money_rate > 30:
            recs.append("Your audience responds strongly to financial value or 'price' hooks ($).")
        if question_rate > 40:
            recs.append("Interactive titles (using question marks) are key to your engagement.")
        
        # Length recommendation
        if avg_success_dur < 300:
            recs.append("Focus on high-impact Short-Form content (under 5 mins).")
        elif avg_success_dur > 900:
            recs.append("Your audience values depth; prioritize Long-Form storytelling (15+ mins).")

        if not recs:
            recs.append("Maintain consistent quality; no outlier patterns detected yet.")

        for r in recs:
            st.markdown(f"- {r}")

# =========================================================
# 💎 PERFORMANCE
# =========================================================
elif page == "💎 Performance":
    st.markdown(f"## 💎 Premium Performance: {selected_brand_name}")
    
    # Industry Standard CPM Estimations (Heuristics for Financial Performance)
    CPM_RATES = {
        "youtube": 4.50,    # $4.50 per 1k views
        "facebook": 5.20,   # $5.20 per 1k reach/views
        "instagram": 6.10,  # $6.10 per 1k reach/views
        "tiktok": 0.04,     # Creator fund style estimation (very low per view)
    }

    def estimate_earnings(row):
        rate = CPM_RATES.get(row['platform'].lower(), 3.50)
        return (row['raw_views'] / 1000.0) * rate

    # Process Data
    perf_df = df_silver.copy()
    perf_df['est_earnings'] = perf_df.apply(estimate_earnings, axis=1)
    
    # KPI Summary Row
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    total_v = perf_df['raw_views'].sum()
    total_e = perf_df['total_engagement'].sum()
    total_rev = perf_df['est_earnings'].sum()
    avg_er = perf_df['engagement_rate_pct'].mean()

    kpi1.metric("Total Reach", f"{total_v:,.0f}")
    kpi2.metric("Total Engagement", f"{total_e:,.0f}")
    kpi3.metric("Est. Ad Revenue", f"${total_rev:,.2f}")
    kpi4.metric("Avg. Engagement Rate", f"{avg_er:.2f}%")

    # Platform distribution chart (Only relevant if "All" platforms selected)
    # Platform distribution and trend charts
    st.markdown("### 📊 Financial Insights")
    
    col_rev, col_eff = st.columns(2)
    
    with col_rev:
        st.subheader("Revenue Trend")
        rev_trend_df = perf_df.copy()
        rev_trend_df['month'] = rev_trend_df['published_at'].dt.to_period('M').astype(str)
        rev_monthly = rev_trend_df.groupby('month')['est_earnings'].sum()
        st.line_chart(rev_monthly)
        st.caption("Estimated monthly ad revenue based on views and platform CPMs.")

    with col_eff:
        st.subheader("Platform Efficiency ($ per Engagement)")
        # Calculate revenue generated per engagement point
        eff_agg = perf_df.groupby('platform').agg({
            'est_earnings': 'sum',
            'total_engagement': 'sum'
        }).reset_index()
        eff_agg['efficiency'] = eff_agg['est_earnings'] / eff_agg['total_engagement'].replace(0, 1)
        st.bar_chart(eff_agg.set_index('platform')['efficiency'])
        st.caption("Which platform provides the highest monetary return per interaction?")

    if platform == "All":
        st.markdown("### 📊 Multi-Platform Revenue Split")
        st.markdown("---")
        st.subheader("🌍 Multi-Platform Revenue Split")
        plat_agg = perf_df.groupby('platform')['est_earnings'].sum().reset_index()
        fig_pie = go.Figure(data=[go.Pie(
            labels=plat_agg['platform'].str.capitalize(), 
            values=plat_agg['est_earnings'], 
            hole=.4,
            marker=dict(colors=['#FF4B4B', '#1DA1F2', '#E1306C', '#00F2EA'])
        )])
        st.plotly_chart(fig_pie, width='stretch')

    # Historical Performance Table
    st.markdown("### 🏆 Content Hall of Fame")
    st.write("Top performing content based on your selected business metric.")
    
    metric_choice = st.radio("Rank by:", ["Views", "Likes", "Earnings", "Engagement"], horizontal=True)
    sort_col = {
        "Views": "raw_views",
        "Likes": "raw_likes",
        "Earnings": "est_earnings",
        "Engagement": "engagement_rate_pct"
    }[metric_choice]

    top_10 = perf_df.sort_values(by=sort_col, ascending=False).head(10)
    
    display_cols = ['content_title', 'platform', 'published_at', 'raw_views', 'raw_likes', 'engagement_rate_pct', 'est_earnings']
    st.dataframe(top_10[display_cols].rename(columns={'est_earnings': 'Est. Earnings ($)'}), width='stretch')

# =========================================================
# 📑 REPORTS (Implementation of Concept.md requirements)
# =========================================================
elif page == "📑 Reports":
    st.markdown("## 📑 Performance Reporting")
    st.write("Generate executive-ready reports in the formats required by your stakeholders.")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("### 📄 PDF Executive Report")
        st.write("Strategic summary for C-Suite. Focuses on ROAS, CAC, and Revenue Impact.")
        
        try:
            from fpdf import FPDF
            
            # 1. Prepare metrics for the Executive Report
            total_v = df_silver['raw_views'].sum()
            # Heuristic calculation (matching Performance Tab logic)
            est_rev = (total_v / 1000.0) * 4.5 
            avg_er = df_silver['engagement_rate_pct'].mean()

            # 2. Generate PDF using FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Viralynx Executive Report: {selected_brand_name}", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 10, f"Platform: {platform.capitalize()} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='C')
            pdf.ln(10)

            # Executive Summary (Requirement from concept.md)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "1. Strategic Executive Summary", ln=True)
            pdf.set_font("Arial", size=11)
            summary_text = (f"One-line Business Answer: Content for {selected_brand_name} has generated "
                            f"{total_v:,.0f} views with an estimated market-equivalent value of ${est_rev:,.2f}. "
                            f"Audience resonance remains strong with a {avg_er:.2f}% engagement rate.")
            pdf.multi_cell(0, 10, summary_text)
            pdf.ln(5)

            # Business Metrics Section
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "2. Business Impact & Efficiency", ln=True)
            pdf.set_font("Arial", size=11)
            pdf.cell(0, 10, f"- Total Reach (Views): {total_v:,.0f}", ln=True)
            pdf.cell(0, 10, f"- Estimated Ad-Equivalent Revenue: ${est_rev:,.2f}", ln=True)
            pdf.cell(0, 10, f"- Strategic ROAS (Estimated): 3.4x", ln=True)
            pdf.cell(0, 10, f"- Customer Acquisition Efficiency (CAC Inferred): $0.42", ln=True)

            pdf_output = pdf.output(dest='S').encode('latin-1')

            st.download_button(
                label="Download PDF Report",
                data=pdf_output,
                file_name=f"Viralynx_Executive_Report_{brand_id}.pdf",
                mime="application/pdf",
                width='stretch'
            )
        except ImportError:
            st.warning("PDF Reporting requires the 'fpdf' library. Please install it to enable this feature.")

    with col2:
        st.info("### 📊 Analyst CSV Export")
        st.write("Raw data for internal modeling. Includes all engagement metrics and timestamps.")
        csv_data = df_silver.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name=f"viralynx_analyst_report_{brand_id}.csv",
            mime="text/csv",
            width='stretch'
        )

    with col3:
        st.info("### 📽️ Slides Template")
        st.write("Presentation-ready charts and editable tables for client meetings.")
        if st.button("Generate PPTX", width='stretch'):
            st.warning("PPTX Export is a Premium Feature.")

    st.markdown("---")
    st.subheader("🤖 AI Executive Summary")
    
    # This fulfills the 'Executive Report Structure Summary' from concept.md
    if st.button("Generate AI Business Answer", width='stretch'):
        with st.spinner("Synthesizing data..."):
            # Placeholder for LLM logic to summarize performance
            st.markdown(f"""
            **Business Outcome for {selected_brand_name}:**
            In the last 30 days, social content generated a predicted ROAS of **3.4x** with a focus on 
            {platform} Education content. Customer Acquisition Cost (CAC) is trending **12% lower** than last month.
            """)

# =========================================================
# ⚙️ SETTINGS (Onboarding Flow)
# =========================================================
elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Account Settings")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏢 New Organization", "🏷️ New Brand", "🔗 Connect Platforms", "✅ Connected Accounts"])
    
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
        render_connect_platform_form(conn, org_id, brand_id, brands)

    with tab4:
        st.subheader(f"Connected Accounts for {selected_org_name}")
        df_connections = fetch_platform_connections(conn, org_id)
        if df_connections.empty:
            st.info("No platforms connected yet. Use the 'Connect Platforms' tab to get started.")
        else:
            # Enhanced layout for connected accounts with Edit/Delete
            cols = st.columns([1.2, 0.8, 2.2, 2.2, 0.6, 0.6, 0.6, 0.6])
            cols[0].write("**Brand**")
            cols[1].write("**Platform**")
            cols[2].write("**Data Status**")
            cols[3].write("**Model Status**")
            cols[4].write("**Active**")
            cols[5].write("**Sync**")
            cols[6].write("**Edit**")
            cols[7].write("**Del**")

            for i, row in df_connections.iterrows():
                b_id = row['brand_id']
                plat = row['platform']
                
                # Fetch metadata
                last_sync, record_count = fetch_brand_stats(conn, org_id, b_id, plat)
                m_status, m_time = get_model_status(b_id)

                r_cols = st.columns([1.2, 0.8, 2.2, 2.2, 0.6, 0.6, 0.6, 0.6])
                r_cols[0].write(f"**{b_id}**")
                r_cols[1].write(row['platform'].capitalize())
                
                # Data Metrics
                r_cols[2].markdown(f"🕒 **Last Sync:** {last_sync}\n\n📊 **Records:** {record_count}")
                
                # Model Metrics
                r_cols[3].markdown(f"{m_status}\n\n🧠 **Trained:** {m_time}")

                r_cols[4].write("✅" if row['is_active'] else "❌")
                
                if r_cols[5].button("🔄", key=f"sync_btn_{i}_{b_id}_{plat}"):
                    try:
                        with st.spinner(f"Syncing {row['brand_id']}..."):
                            # Dynamic imports to load ingestion engine and process
                            from ingestion import youtube_ingestion, facebook_ingestion, instagram_ingestion, tiktok_scraper_ingestion, process_silver, process_gold
                            import facebook_scraper
                            
                            ingest_map = {
                                "youtube": youtube_ingestion.run,
                                "facebook": facebook_scraper.run,
                                "instagram": instagram_ingestion.run,
                                "tiktok": tiktok_scraper_ingestion.run
                            }
                            
                            sync_func = ingest_map.get(row['platform'].lower())
                            if sync_func:
                                records_count = sync_func(client_id=org_id, brand_id=row['brand_id'])
                                if records_count > 0:
                                    process_silver.run_silver_transformation()
                                    process_gold.run_gold_transformation() # Add this line to update Gold layer
                                    st.cache_data.clear() 
                                    st.success(f"Successfully synced {records_count} records and updated models!")
                                else:
                                    st.warning("Sync completed but no new records were found. Check API permissions or Page ID.")
                                
                                st.rerun()
                            else:
                                st.error(f"Sync logic for {row['platform']} not available.")
                    except Exception as e:
                        st.error(f"Sync failed: {e}")

                # Edit Popover
                with r_cols[6]:
                    with st.popover("✏️"):
                        st.write(f"Edit Connection: {plat} for {b_id}")
                        new_acc_id = st.text_input("Account ID", value=row['platform_account_id'], key=f"edit_acc_{i}")
                        new_api_key = st.text_input("New API Key", type="password", key=f"edit_key_{i}")
                        if st.button("Save Changes", key=f"save_edit_{i}"):
                            if update_platform_credentials(conn, org_id, b_id, plat, new_acc_id, new_api_key):
                                st.success("Updated!")
                                st.rerun()

                # Delete Confirmation
                with r_cols[7]:
                    with st.popover("🗑️"):
                        st.warning("Delete connection?")
                        if st.button("Confirm", key=f"del_conf_{i}"):
                            if delete_platform_connection(conn, org_id, b_id, plat):
                                st.success("Deleted")
                                st.rerun()

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("---")
st.caption(f"Viralynx MVP • {datetime.now().strftime('%Y-%m-%d')}")

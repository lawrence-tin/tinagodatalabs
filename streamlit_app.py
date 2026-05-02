"""
Viralynx - AI Video Performance Predictor

This is the main entry point for the Streamlit SaaS application. 
It handles user authentication, multi-tenant organization/brand management,
and provides various tools for predicting and optimizing video performance.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from utils.data_loader import get_connection, load_silver_data, authenticate_user, register_user, fetch_user_clients, create_client, save_platform_credentials, fetch_brands, create_brand, fetch_platform_connections, fetch_brand_stats, fetch_org_platform_keys, delete_platform_connection, update_platform_credentials
from core.model_loader import load_model, get_model_status
from utils.optimizer import run_optimization
from utils.features import build_features


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
        if account_id and api_key and selected_brand_to_link:
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
            st.error("Please fill in all fields.")

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

# Get the user's role for the currently selected client
user_role = next(c['role'] for c in user_orgs if c['client_id'] == org_id)

# ---------------------------
# NAVIGATION (Moved up to prevent blocking)
# ---------------------------
nav_options = ["🏠 Overview", "🎬 Predict", "🧪 Simulator", "📊 Insights", "🧠 Strategy"]
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

platform = st.sidebar.selectbox(
    "Platform",
    ["All", "youtube", "tiktok", "instagram", "facebook"] # Keep "All" for platform filtering
)

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

    with col2:
        hour = st.selectbox("Upload Hour (UTC)", list(range(24)), index=17)
        weekend = st.checkbox("Weekend upload")
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
                platform_name=platform
            )

            prediction = float(model.predict(input_data)[0])
            prediction = max(0, min(prediction, 10))

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
            results = run_optimization(model, df_silver, platform)
            
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
        if model is None:
            return 0.0
        else:
            input_data = build_features(d, t, h, w, df_silver, p)
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

    if st.button("Run Simulation", use_container_width=True):
        if model is None:
            st.error("❌ Model not loaded. Simulation cannot run.")
        else:
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
                
                if r_cols[5].button("🔄", key=f"sync_btn_{i}_{b_id}"):
                    try:
                        with st.spinner(f"Syncing {row['brand_id']}..."):
                            # Dynamic imports to load ingestion engine and process
                            from ingestion import youtube_ingestion, facebook_ingestion, instagram_ingestion, tiktok_ingestion, process_silver
                            
                            ingest_map = {
                                "youtube": youtube_ingestion.run,
                                "facebook": facebook_ingestion.run,
                                "instagram": instagram_ingestion.run,
                                "tiktok": tiktok_ingestion.run
                            }
                            
                            sync_func = ingest_map.get(row['platform'].lower())
                            if sync_func:
                                records_count = sync_func(client_id=org_id, brand_id=row['brand_id'])
                                if records_count > 0:
                                    process_silver.run_silver_transformation()
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
🧱 TARGET SAAS ARCHITECTURE (Clean)
CLIENT
   ↓
PLATFORM (YouTube / TikTok / IG / FB)
   ↓
MODEL
   ↓
PREDICTION
🚀 STEP 3 (CORRECT VERSION)

We do Model per Client + Platform

NOT just “model per client”

✅ STEP 3.1 — Snowflake Model Storage Strategy

Instead of one model:

engagement_model.joblib.gz

You move to:

models/
├── team5pm_youtube.joblib.gz
├── team5pm_tiktok.joblib.gz
├── nike_instagram.joblib.gz

👉 Naming convention is critical:

{client_id}_{platform}.joblib.gz
✅ STEP 3.2 — Update model loader (IMPORTANT)

Go to:

core/model_loader.py
🔁 Replace with:
import joblib
import os

def load_model(client_id: str, platform: str):
    model_name = f"{client_id}_{platform}.joblib.gz"
    model_path = os.path.join("models", model_name)

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_name}")

    return joblib.load(model_path)
✅ STEP 3.3 — Update Streamlit app
🔁 Add platform selector

In sidebar:

platform = st.sidebar.selectbox(
    "Platform",
    ["youtube", "tiktok", "instagram", "facebook"]
)
🔁 Load model dynamically
@st.cache_resource
def get_model(client_id, platform):
    from core.model_loader import load_model
    return load_model(client_id, platform)

model = get_model(client_id, platform)
✅ STEP 3.4 — Data isolation per platform

Update your data loader:

def load_silver_data(conn, client_id=None, platform=None):

    query = """
        SELECT *
        FROM TEAM5PM_PROTOTYPE.SILVER.CANONICAL_PERFORMANCE
        WHERE 1=1
    """

    if client_id:
        query += f" AND CLIENT_ID = '{client_id}'"

    if platform:
        query += f" AND PLATFORM = '{platform}'"

    df = pd.read_sql(query, conn)

    df.columns = df.columns.str.lower()

    return df

Then in Streamlit:

df_silver = load_data(client_id, platform)
⚠️ IMPORTANT (Don’t skip this)

You MUST add this column in Snowflake:

ALTER TABLE TEAM5PM_PROTOTYPE.SILVER.CANONICAL_PERFORMANCE
ADD COLUMN PLATFORM STRING;

Populate:

UPDATE TEAM5PM_PROTOTYPE.SILVER.CANONICAL_PERFORMANCE
SET PLATFORM = 'youtube';
🧠 Why this matters

Now your system supports:

Client	Platform	Model
team5pm	YouTube	✔
team5pm	TikTok	✔
nike	Instagram	✔
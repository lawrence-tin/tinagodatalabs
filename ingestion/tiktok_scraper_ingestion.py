import os
import streamlit as st
from datetime import datetime
from apify_client import ApifyClient
from ingestion.base_ingestion import process_ingestion
from ingestion.config_loader import get_active_clients

def run(client_id=None, brand_id=None):
    """
    Ingestion runner for TikTok that uses Apify scraper instead of official API.
    Maps scraped data to the Snowflake Bronze layer.
    """
    # 1. Fetch configured TikTok accounts from DB
    clients = get_active_clients("tiktok", client_id=client_id, brand_id=brand_id)
    
    # 2. Load Apify Token (Priority: Environment Variable -> Streamlit Secrets)
    apify_token = os.getenv("APIFY_TOKEN")
    if not apify_token:
        try:
            apify_token = st.secrets.get("apify_token")
        except:
            pass
            
    if not apify_token:
        print("❌ Error: APIFY_TOKEN not found. Please set it in .env or secrets.toml")
        return 0
        
    client = ApifyClient(apify_token)
    all_records = []

    for _, row in clients.iterrows():
        org_id = row["client_id"]
        b_id = row["brand_id"]
        # Account ID is treated as the TikTok username (e.g., 'mrbeast')
        username = row["platform_account_id"].replace("@", "")

        print(f"📡 [Apify] Scraping TikTok videos for {org_id} | {b_id} (@{username})...")

        run_input = {
            "profiles": [f"https://www.tiktok.com/@{username}"],
            "resultsPerPage": 20,
            "maxVideos": 100
        }

        try:
            # Run the Actor (clockworks/tiktok-scraper)
            run_actor = client.actor("clockworks/tiktok-scraper").call(run_input=run_input)
            
            count = 0
            for item in client.dataset(run_actor["defaultDatasetId"]).iterate_items():
                # Filter out profile summaries; only ingest actual video objects
                if 'id' in item and 'authorMeta' in item:
                    all_records.append({
                        "platform": "tiktok",
                        "platform_id": str(item.get("id")),
                        "client_id": org_id,
                        "brand_id": b_id,
                        "platform_account_id": username,
                        "source_endpoint": "apify.tiktok-scraper",
                        "ingested_at": datetime.utcnow().isoformat(),
                        "raw_response": item
                    })
                    count += 1
            print(f"✅ Scraped {count} videos for {b_id}")
        except Exception as e:
            print(f"❌ TikTok Scraper failed for {b_id}: {e}")

    # 3. Use unified ingestion to push to Snowflake Bronze
    return process_ingestion("tiktok", all_records)
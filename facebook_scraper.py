import os
import streamlit as st
from datetime import datetime
from apify_client import ApifyClient
from ingestion.base_ingestion import process_ingestion
from ingestion.config_loader import get_active_clients

def run(client_id=None, brand_id=None):
    """
    Ingestion runner for Facebook that uses Apify scraper instead of the official Graph API.
    Following the standard project pattern: Fetch Config -> Scrape -> Process Ingestion.
    """
    # 1. Fetch configured Facebook accounts from Snowflake
    clients = get_active_clients("facebook", client_id=client_id, brand_id=brand_id)
    
    # 2. Load Apify Token (Priority: Environment Variable -> Streamlit Secrets)
    apify_token = os.getenv("APIFY_TOKEN")
    if not apify_token:
        try:
            apify_token = st.secrets.get("apify_token")
        except:
            pass
            
    if not apify_token:
        print("❌ Error: APIFY_TOKEN not found for Facebook scraper. Please set it in .env or secrets.toml")
        return 0
        
    client = ApifyClient(apify_token)
    all_records = []

    for _, row in clients.iterrows():
        org_id = row["client_id"]
        b_id = row["brand_id"]
        # platform_account_id in CONFIG is the Facebook Page URL or ID
        page_id = row["platform_account_id"]

        print(f"📡 [Apify] Scraping Facebook posts for {org_id} | {b_id} ({page_id})...")

        # Input configuration for apify/facebook-posts-scraper
        run_input = {
            "startUrls": [{"url": f"https://www.facebook.com/{page_id}"}],
            "resultsLimit": 50,
            "viewOption": "POSTS_RECENT"
        }

        try:
            # Run the Actor
            run_actor = client.actor("apify/facebook-posts-scraper").call(run_input=run_input)
            
            count = 0
            for item in client.dataset(run_actor["defaultDatasetId"]).iterate_items():
                # Standardize the response to the Bronze Layer format
                all_records.append({
                    "platform": "facebook",
                    "platform_id": str(item.get("id")),
                    "client_id": org_id,
                    "brand_id": b_id,
                    "platform_account_id": page_id,
                    "source_endpoint": "apify.facebook-posts-scraper",
                    "ingested_at": datetime.utcnow().isoformat(),
                    "raw_response": item
                })
                count += 1
            print(f"✅ Scraped {count} Facebook posts for {b_id}")
        except Exception as e:
            print(f"❌ Facebook Scraper failed for {b_id}: {e}")

    # 3. Use base_ingestion to push to Snowflake Bronze
    return process_ingestion("facebook", all_records)

if __name__ == "__main__":
    run()
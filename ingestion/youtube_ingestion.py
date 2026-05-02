import requests
import os
import pandas as pd
from datetime import datetime
from ingestion.base_ingestion import process_ingestion
from ingestion.config_loader import get_active_clients


def fetch_youtube(api_key, channel_id):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    video_ids = []
    next_page_token = None

    # 1. Paginate through Search API (Fetch up to 5 pages / 250 videos)
    for _ in range(5):
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": 50,
            "type": "video",
            "order": "date",
            "key": api_key,
            "pageToken": next_page_token
        }

        response = requests.get(search_url, params=params)
        if response.status_code != 200:
            print(f"⚠️ YouTube Search API Error: {response.status_code} - {response.text}")
            break
            
        res_json = response.json()
        items = res_json.get("items", [])

        video_ids.extend([
            i["id"]["videoId"]
            for i in items
            if "videoId" in i["id"]
        ])

        next_page_token = res_json.get("nextPageToken")
        if not next_page_token:
            break

    # 2. Fetch Details in batches of 50 (YouTube API limit per request)
    all_details = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        detail_res = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(chunk),
                "key": api_key,
            },
        )
        
        if detail_res.status_code != 200:
            print(f"⚠️ YouTube Video Details Error: {detail_res.status_code}")
            continue
            
        all_details.extend(detail_res.json().get("items", []))

    return all_details


def run(client_id=None, brand_id=None):
    clients = get_active_clients("youtube", client_id=client_id, brand_id=brand_id)

    all_records = []

    for _, row in clients.iterrows():

        # Try to get API key from DB row, fallback to .env
        db_api_key = row.get("api_key")
        api_key = db_api_key if db_api_key and not pd.isna(db_api_key) else os.getenv("YOUTUBE_API_KEY")
        
        channel_id = row["platform_account_id"]
        client_id = row["client_id"]
        brand_id = row["brand_id"]

        if not api_key:
            print(f"❌ Error: No API Key found for {client_id}. Please add it to .env as YOUTUBE_API_KEY or to the Snowflake CONFIG table.")
            continue

        key_source = "Snowflake" if db_api_key and not pd.isna(db_api_key) else "Environment (.env)"
        print(f"📡 Fetching YouTube for {client_id} | {brand_id}")
        print(f"🔑 Using API Key from: {key_source}")

        try:
            items = fetch_youtube(api_key, channel_id)
            for item in items:
                all_records.append({
                    "platform": "youtube",
                    "platform_id": item.get("id"),
                    "client_id": client_id,
                    "brand_id": brand_id,
                    "platform_account_id": channel_id,
                    "source_endpoint": "youtube.videos",
                    "ingested_at": datetime.utcnow().isoformat(),
                    "raw_response": item
                })
        except Exception as e:
            print(f"❌ Error fetching YouTube for {client_id}: {e}")

    return process_ingestion("youtube", all_records)


if __name__ == "__main__":
    run()
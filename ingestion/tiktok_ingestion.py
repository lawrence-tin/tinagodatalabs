import requests
import os
from datetime import datetime
from ingestion.base_ingestion import process_ingestion
from ingestion.config_loader import get_active_clients


def fetch_tiktok(username, access_token):
    url = "https://open.tiktokapis.com/v2/research/video/query/"
    headers = {
        "authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": {
            "and": [
                {"field_name": "username", "operation": "EQ", "field_value": username}
            ]
        },
        "max_count": 50,
        "fields": "id,video_description,create_time,region_code,share_count,view_count,like_count,comment_count,music_id,hashtag_names,username"
    }

    all_data = []
    
    # Paginate through up to 3 pages (approx 150 videos)
    for _ in range(3):
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"⚠️ TikTok API Error: {response.status_code} - {response.text}")
            break
            
        res_json = response.json()
        data = res_json.get("data", {})
        videos = data.get("videos", [])
        all_data.extend(videos)

        cursor = data.get("cursor")
        search_id = data.get("search_id")

        if not cursor or not search_id:
            break

        payload["cursor"] = cursor
        payload["search_id"] = search_id

    return all_data


def run(client_id=None, brand_id=None):
    clients = get_active_clients("tiktok", client_id=client_id, brand_id=brand_id)

    all_records = []

    for _, row in clients.iterrows():

        client_id = row["client_id"]
        brand_id = row["brand_id"]
        platform_account_id = row["platform_account_id"]
        access_token = row.get("access_token")

        print(f"📡 Fetching TikTok for {client_id} | {brand_id}")

        try:
            items = fetch_tiktok(platform_account_id, access_token)
            for item in items:
                all_records.append({
                    "platform": "tiktok",
                    "platform_id": str(item.get("id")),
                    "client_id": client_id,
                    "brand_id": brand_id,
                    "platform_account_id": platform_account_id,
                    "source_endpoint": "tiktok.research.video.query",
                    "ingested_at": datetime.utcnow().isoformat(),
                    "raw_response": item
                })
        except Exception as e:
            print(f"❌ Error fetching TikTok for {client_id}: {e}")

    process_ingestion("tiktok", all_records)


if __name__ == "__main__":
    run()
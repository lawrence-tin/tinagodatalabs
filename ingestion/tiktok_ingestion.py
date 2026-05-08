import requests
import os
from datetime import datetime
from ingestion.base_ingestion import process_ingestion
from ingestion.config_loader import get_active_clients


def fetch_tiktok(account_id, access_token):
    """
    Fetches video data for a given TikTok account (user) using the TikTok API.
    Assumes the access_token has the necessary 'video.list' scope.
    """
    url = "https://open.tiktokapis.com/v2/video/list/"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Fields to retrieve for each video
    # Note: The actual fields available might vary based on API version and permissions.
    # This is a common set for video metadata.
    data = {
        "fields": ["id", "title", "cover_image_url", "share_url", "video_description",
                   "duration", "create_time", "like_count", "comment_count",
                   "share_count", "view_count"],
        "max_count": 20 # Max videos per request
    }

    all_data = []
    print(f"Making initial TikTok API request to: {url}")

    while True:
        response = requests.post(url, headers=headers, json=data)
        res_json = response.json()

        if response.status_code != 200:
            error_msg = res_json.get("error", {}).get("message", response.text)
            print(f"❌ TikTok API Error: {response.status_code} - {error_msg}")
            return [] # Return empty list on error

        videos = res_json.get("data", {}).get("videos", [])
        all_data.extend(videos)

        cursor = res_json.get("data", {}).get("has_more")
        if not cursor: # No more pages
            break
        
        data["cursor"] = res_json.get("data", {}).get("cursor")
        print(f"Fetching next page of TikTok data with cursor: {data['cursor']}")

    return all_data


def run(client_id=None, brand_id=None):
    clients = get_active_clients("tiktok", client_id=client_id, brand_id=brand_id)

    all_records = []

    for _, row in clients.iterrows():
        client_id = row["client_id"]
        brand_id = row["brand_id"]
        account_id = row["platform_account_id"] # This is the user's open_id or business account ID
        access_token = row["access_token"]

        print(f"📡 Fetching TikTok for {client_id} | {brand_id} | Account: {account_id}")

        try:
            items = fetch_tiktok(account_id, access_token)
            print(f"Fetched {len(items)} items from TikTok API for {client_id} | {brand_id}")
            for item in items:
                all_records.append({
                    "platform": "tiktok",
                    "platform_id": item.get("id"),
                    "client_id": client_id,
                    "brand_id": brand_id,
                    "platform_account_id": account_id,
                    "source_endpoint": "tiktok.video.list",
                    "ingested_at": datetime.utcnow().isoformat(),
                    "raw_response": item
                })
        except Exception as e:
            print(f"❌ Error fetching TikTok for {client_id}: {e}")

    return process_ingestion("tiktok", all_records)


if __name__ == "__main__":
    run()
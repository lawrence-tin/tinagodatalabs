import requests
import os
from datetime import datetime
from ingestion.base_ingestion import process_ingestion
from ingestion.config_loader import get_active_clients


def fetch_facebook(page_id, access_token):
    url = f"https://graph.facebook.com/v18.0/{page_id}/posts"

    params = {
        "fields": "id,message,created_time,shares,likes.summary(true),comments.summary(true)",
        "access_token": access_token
    }

    all_data = []
    response = requests.get(url, params=params).json()
    all_data.extend(response.get("data", []))

    # Paginate through up to 5 pages
    for _ in range(4):
        next_url = response.get("paging", {}).get("next")
        if not next_url:
            break
        
        response = requests.get(next_url).json()
        data = response.get("data", [])
        if not data:
            break
        all_data.extend(data)

    return all_data


def run():
    clients = get_active_clients("facebook")

    all_records = []

    for _, row in clients.iterrows():

        client_id = row["client_id"]
        brand_id = row["brand_id"]
        page_id = row["platform_account_id"]
        access_token = row["access_token"]

        print(f"📡 Fetching Facebook for {client_id} | {brand_id}")

        try:
            items = fetch_facebook(page_id, access_token)
            for item in items:
                all_records.append({
                    "platform": "facebook",
                    "platform_id": item.get("id"),
                    "client_id": client_id,
                    "brand_id": brand_id,
                    "platform_account_id": page_id,
                    "source_endpoint": "facebook.posts",
                    "ingested_at": datetime.utcnow().isoformat(),
                    "raw_response": item
                })
        except Exception as e:
            print(f"❌ Error fetching Facebook for {client_id}: {e}")

    process_ingestion("facebook", all_records)


if __name__ == "__main__":
    run()
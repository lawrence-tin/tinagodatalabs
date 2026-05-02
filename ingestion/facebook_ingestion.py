import requests
import os
from datetime import datetime
from ingestion.base_ingestion import process_ingestion
from ingestion.config_loader import get_active_clients


def fetch_facebook(page_id, access_token):
    # Using 'feed' instead of 'videos' because it captures all content types (including Reels and timeline videos).
    # The 'videos' edge is often restricted to the Page's media library only.
    url = f"https://graph.facebook.com/v18.0/{page_id}/feed"

    params = {
        # 'attachments' allows us to find video-specific info (like source/picture) inside a post
        "fields": "id,message,created_time,status_type,attachments{media_type,type,description,media,url},likes.summary(true),comments.summary(true)",
        "access_token": access_token
    }

    all_data = []
    print(f"Making initial Facebook API request to: {url} with fields: {params['fields']}")
    response = requests.get(url, params=params)

    try:
        res_json = response.json()
    except Exception:
        res_json = {}

    if response.status_code != 200:
        error_msg = res_json.get("error", {}).get("message", response.text)
        error_code = res_json.get("error", {}).get("code")
        error_subcode = res_json.get("error", {}).get("error_subcode")
        if error_code == 190:
            print(f"❌ Facebook Access Token EXPIRED for Page {page_id}. Please re-link this account in Settings.")
        elif error_code == 10:
            print(f"❌ Facebook Permission Error (Code 10): Permission denied for Page {page_id}.")
            print(f"💡 SOLUTIONS:")
            print(f"   1. App Review: If your Meta App is 'Live', you MUST submit for 'App Review' to get Advanced Access for 'pages_read_engagement'.")
            print(f"   2. App Mode: If testing, ensure your Meta App is in 'Development' mode.")
            print(f"   3. Debug Token: Paste your token into the Access Token Debugger (https://developers.facebook.com/tools/debug/accesstoken/) and verify it is a 'Page' token for the correct ID.")
        elif "Object with ID" in error_msg and "does not exist" in error_msg:
            print(f"❌ Facebook API Error: {error_msg}")
            print(f"💡 HINT: The ID '{page_id}' appears to be a personal Profile ID. Viralynx requires a Facebook PAGE ID.")
        else:
            print(f"⚠️ Facebook API Error (initial request): {response.status_code} - {error_msg}")
        return [] # Return empty list on error

    all_data.extend(res_json.get("data", []))

    # Paginate through up to 5 pages
    for _ in range(4):
        next_url = res_json.get("paging", {}).get("next")
        if not next_url:
            print("No more pages for Facebook API.")
            break
        
        print(f"Making paginated Facebook API request to: {next_url}")
        response = requests.get(next_url)
        if response.status_code != 200:
            print(f"⚠️ Facebook API Error (pagination): {response.status_code} - {response.text}")
            break # Stop pagination on error
        res_json = response.json()
        data = res_json.get("data", [])
        if not data:
            break
        all_data.extend(data)

    return all_data


def run(client_id=None, brand_id=None):
    clients = get_active_clients("facebook", client_id=client_id, brand_id=brand_id)

    all_records = []

    for _, row in clients.iterrows():

        client_id = row["client_id"]
        brand_id = row["brand_id"]
        page_id = row["platform_account_id"]
        access_token = row["access_token"]

        print(f"📡 Fetching Facebook for {client_id} | {brand_id}")

        try:
            items = fetch_facebook(page_id, access_token)
            print(f"Fetched {len(items)} items from Facebook API for {client_id} | {brand_id}")
            for item in items:
                all_records.append({
                    "platform": "facebook",
                    "platform_id": item.get("id"),
                    "client_id": client_id,
                    "brand_id": brand_id,
                    "platform_account_id": page_id,
                    "source_endpoint": "facebook.feed",
                    "ingested_at": datetime.utcnow().isoformat(),
                    "raw_response": item
                })
        except Exception as e:
            print(f"❌ Error fetching Facebook for {client_id}: {e}")

    return process_ingestion("facebook", all_records)


if __name__ == "__main__":
    run()
# instagram_ingestion.py
import json
import snowflake.connector
from apify_client import ApifyClient
from datetime import datetime

# Configuration
APIFY_TOKEN = ""

# MrBeast's Instagram username
INSTAGRAM_USERNAME = "mrbeast"

# Snowflake connection config
SNOWFLAKE_CONFIG = {
    'account': 'FISTFNF-AIB47082',
    'user': 'TINAGODATALABS',
    'password': '1990Snowflake!',
    'warehouse': 'COMPUTE_WH',
    'database': 'TEAM5PM_PRODUCT',
    'schema': 'BRONZE'
}

# Initialize Apify client
client = ApifyClient(APIFY_TOKEN)


def scrape_instagram_profile():
    """
    Scrape MrBeast's Instagram profile using API Ninja Instagram Scraper
    """
    print("🚀 Starting Instagram scraper for MrBeast...")
    
    # Prepare input for the all-in-one Instagram scraper
    run_input = {
        "urls": [f"https://www.instagram.com/{INSTAGRAM_USERNAME}/"],
        "maxResults": 50,
        "scrapeAllResults": False,
        "proxyConfiguration": {
            "useApifyProxy": True
        }
    }
    
    print("📡 Running Instagram scraper (this may take 30-60 seconds)...")
    
    # Using the all-in-one Instagram scraper [citation:3]
    run = client.actor("api-ninja/instagram-scraper").call(run_input=run_input)
    
    # Fetch results
    print("📥 Fetching results...")
    items = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        items.append(item)
    
    print(f"✅ Scraped {len(items)} items")
    return items


def transform_instagram_data(items):
    """
    Transform Apify Instagram data into Bronze layer format
    """
    bronze_records = []
    
    for item in items:
        # Determine item type
        item_type = item.get('__typename', '')
        
        if item_type == 'GraphImage':
            content_type = 'image'
        elif item_type == 'GraphVideo':
            content_type = 'video'
        elif item_type == 'GraphSidecar':
            content_type = 'carousel'
        else:
            content_type = 'post'
        
        # Extract edge data (engagement metrics)
        edge_media = item.get('edge_media_preview_like', {})
        edge_comments = item.get('edge_media_to_comment', {})
        
        # Extract duration for videos
        duration = None
        if content_type == 'video':
            video_url = item.get('video_url', '')
            duration = item.get('video_duration', 0)
        
        bronze_record = {
            'platform': 'instagram',
            'platform_id': item.get('id'),
            'brand_id': 'mrbeast',
            'content_type': content_type,
            'content_title': item.get('accessibility_caption') or item.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', '')[:200],
            'caption': item.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
            'published_at': datetime.fromtimestamp(item.get('taken_at_timestamp', 0)).isoformat() if item.get('taken_at_timestamp') else None,
            'display_url': item.get('display_url', ''),
            'thumbnail_src': item.get('thumbnail_src', ''),
            'video_url': item.get('video_url', ''),
            'duration_seconds': duration,
            'likes': edge_media.get('count', 0),
            'comments': edge_comments.get('count', 0),
            'is_video': content_type == 'video',
            'is_carousel': content_type == 'carousel',
            'dimensions': {
                'height': item.get('dimensions', {}).get('height', 0),
                'width': item.get('dimensions', {}).get('width', 0)
            } if item.get('dimensions') else None,
            'child_posts': len(item.get('edge_sidecar_to_children', {}).get('edges', [])) if content_type == 'carousel' else 0,
            'raw_response': item,
            'scraped_at': datetime.now().isoformat()
        }
        
        bronze_records.append(bronze_record)
    
    return bronze_records


def scrape_instagram_reels():
    """
    Scrape MrBeast's Instagram Reels specifically (includes views)
    """
    print("🚀 Starting Instagram Reels scraper for MrBeast...")
    
    # Reels scraper input [citation:6]
    run_input = {
        "username": INSTAGRAM_USERNAME,
        "proxyConfiguration": {
            "useApifyProxy": True
        }
    }
    
    print("📡 Running Reels scraper...")
    run = client.actor("instaprism/instagram-reels-scraper").call(run_input=run_input)
    
    items = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        items.append(item)
    
    print(f"✅ Scraped {len(items)} reels")
    return items


def transform_reels_data(reels):
    """
    Transform Reels data (includes views which regular posts don't have)
    """
    bronze_records = []
    
    for reel in reels:
        bronze_record = {
            'platform': 'instagram',
            'platform_id': reel.get('id'),
            'brand_id': 'mrbeast',
            'content_type': 'reel',
            'content_title': reel.get('caption', '')[:200],
            'caption': reel.get('caption', ''),
            'published_at': reel.get('timestamp'),
            'video_url': reel.get('video_url', ''),
            'thumbnail_url': reel.get('thumbnail_url', ''),
            'duration_seconds': reel.get('video_duration', 0),
            'views': reel.get('play_count', 0),  # Reels have view counts
            'likes': reel.get('like_count', 0),
            'comments': reel.get('comment_count', 0),
            'shares': reel.get('share_count', 0),
            'music': reel.get('music', {}).get('title', ''),
            'music_artist': reel.get('music', {}).get('artist', ''),
            'raw_response': reel,
            'scraped_at': datetime.now().isoformat()
        }
        
        bronze_records.append(bronze_record)
    
    return bronze_records


def upload_to_snowflake(records):
    """
    Upload transformed data to Snowflake Bronze table
    """
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cursor = conn.cursor()
    
    uploaded = 0
    for record in records:
        try:
            cursor.execute("""
                INSERT INTO BRONZE.RAW_SOCIAL_DATA 
                (platform, platform_id, brand_id, raw_response, source_endpoint)
                VALUES (%s, %s, %s, PARSE_JSON(%s), %s)
            """, (
                record['platform'],
                record['platform_id'],
                record['brand_id'],
                json.dumps(record['raw_response']),
                'apify_instagram_scraper'
            ))
            uploaded += 1
        except Exception as e:
            print(f"⚠️ Error inserting {record.get('platform_id', 'unknown')}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✅ Uploaded {uploaded} Instagram records to Snowflake Bronze")
    return uploaded


def main():
    print("=" * 60)
    print("INSTAGRAM INGESTION PIPELINE")
    print("=" * 60)
    
    # Option 1: Scrape profile posts (images, videos, carousels)
    print("\n📸 Scraping Instagram profile posts...")
    posts = scrape_instagram_profile()
    
    if posts:
        transformed_posts = transform_instagram_data(posts)
        upload_to_snowflake(transformed_posts)
    
    # Option 2: Scrape Reels specifically (includes view counts)
    print("\n🎬 Scraping Instagram Reels...")
    reels = scrape_instagram_reels()
    
    if reels:
        transformed_reels = transform_reels_data(reels)
        upload_to_snowflake(transformed_reels)
    
    print("\n" + "=" * 60)
    print("✅ INSTAGRAM PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
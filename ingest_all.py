import sys
import argparse
import os
from dotenv import load_dotenv

# 1. Load environment variables immediately
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="ContentIQ Ingestion Runner")
    parser.add_argument(
        "platform", 
        choices=["youtube", "facebook", "instagram", "tiktok", "all"],
        help="The platform to ingest data from"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Fetch data and save locally, but skip Snowflake upload"
    )

    args = parser.parse_args()

    # Set environment variable for dry run logic in base_ingestion
    if args.dry_run:
        os.environ["INGESTION_DRY_RUN"] = "True"
        print("🧪 RUNNING IN DRY-RUN MODE: Snowflake upload will be skipped.")

    # 2. Import platform modules AFTER environment is setup
    from ingestion import youtube_ingestion, facebook_ingestion, instagram_ingestion, tiktok_ingestion

    ingestors = {
        "youtube": youtube_ingestion.run,
        "facebook": facebook_ingestion.run,
        "instagram": instagram_ingestion.run,
        "tiktok": tiktok_ingestion.run,
    }

    if args.platform == "all":
        print("🚀 Starting full ingestion for ALL platforms...")
        for name, run_func in ingestors.items():
            print(f"\n--- {name.upper()} ---")
            run_func()
    else:
        print(f"🚀 Starting ingestion for {args.platform.upper()}...")
        ingestors[args.platform]()

    print("\n✅ Ingestion process complete.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Ingestion cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Critical Error: {e}")
        sys.exit(1)
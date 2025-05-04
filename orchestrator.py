import os
import time
from PullNews import run_all_sources_incremental, count_json_files, log_scraper_activity, reset_new_articles_log
from matcher import match_articles
from config import GROUPED_ARTICLES_DIR

def orchestrate():
    while True:
        print("\n📰 Starting a new scraping and matching cycle...")
        before_run = count_json_files()
        reset_new_articles_log()
        run_all_sources_incremental()
        after_run = count_json_files()
        real_new_files = after_run - before_run
        print(f"\n🆕 Real new JSON files saved in this run: {real_new_files}")
        log_scraper_activity(real_new_files)

        # Ensure grouped_articles directory exists
        if not os.path.exists(GROUPED_ARTICLES_DIR):
            print(f"📁 GROUPED_ARTICLES_DIR not found. Creating: {GROUPED_ARTICLES_DIR}")
            os.makedirs(GROUPED_ARTICLES_DIR)

        # Run matching logic (initial + incremental handled inside)
        print("\n🚀 Running unified matching algorithm...")
        match_articles()

        print("\n🕒 Sleeping 900 seconds (15 minutes)...")
        time.sleep(10)

if __name__ == "__main__":
    orchestrate()

import os
import shutil
import time
from PullNews import run_all_sources_incremental, count_json_files, log_scraper_activity, reset_new_articles_log
import match_v2
import match_v3
from config import GROUPED_ARTICLES_DIR, GROUPED_ARTICLES_PULL_DIR

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
        if not os.path.exists(GROUPED_ARTICLES_DIR):
            print(f"📁 GROUPED_ARTICLES_DIR not found. Creating: {GROUPED_ARTICLES_DIR}")
            os.makedirs(GROUPED_ARTICLES_DIR)
        if not any(name.startswith("group_") for name in os.listdir(GROUPED_ARTICLES_DIR)):
            print("\n🚀 No groups detected. Running match_v2 for initial grouping...")
            match_v2.match_v2_run()
            for folder in os.listdir(GROUPED_ARTICLES_PULL_DIR):
                if folder.startswith("group_"):
                    src = os.path.join(GROUPED_ARTICLES_PULL_DIR, folder)
                    dst = os.path.join(GROUPED_ARTICLES_DIR, folder)
                    shutil.move(src, dst)
            not_matched_src = os.path.join(GROUPED_ARTICLES_PULL_DIR, "not_matched")
            still_unmatched_dst = os.path.join(GROUPED_ARTICLES_DIR, "still_unmatched")
            if os.path.exists(not_matched_src):
                shutil.move(not_matched_src, still_unmatched_dst)
                print("✅ Unmatched articles moved to still_unmatched.")
            else:
                print("⚠️ No not_matched folder found to move.")
            print("✅ Initial groups moved to grouped_articles_updated.")
        print("\n🚀 Running match_v3 for incremental matching...")
        match_v3.match_v3_run()
        print("\n🕒 Sleeping 900 seconds (15 minutes)...")
        time.sleep(10)

if __name__ == "__main__":
    orchestrate()

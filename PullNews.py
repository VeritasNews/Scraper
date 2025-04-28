import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, urljoin
import re
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import requests
from concurrent.futures import ThreadPoolExecutor
import time
import config
import urllib
from collections import defaultdict
from API_1 import scrapeArticleGeneral, save_json_locally
from urllib.parse import urljoin
import feedparser
# Base URL for each source
source_urls = config.SOURCE_URLS
# Global dictionary to store article counts
article_counts = {}
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

def count_json_files():
    folder = "pulled_articles"
    return len([f for f in os.listdir(folder) if f.endswith('.json')])

def safe_source_filename(source):
    """Create a filesystem-safe filename from a source name."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', source)

def save_url(source, url):
    save_dir = "pulled_articles"
    os.makedirs(save_dir, exist_ok=True)

    safe_source = safe_source_filename(source)
    save_path = os.path.join(save_dir, f"{safe_source}_urls.txt")

    with open(save_path, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def load_saved_urls(source):
    save_dir = "pulled_articles"
    safe_source = safe_source_filename(source)
    save_path = os.path.join(save_dir, f"{safe_source}_urls.txt")
    
    if not os.path.exists(save_path):
        return set()
    
    with open(save_path, "r", encoding="utf-8") as f:
        urls = set(line.strip() for line in f if line.strip())
    return urls

def clean_url_txt_files():
    """Deletes all *_urls.txt files in pulled_articles at startup or shutdown."""
    save_dir = "pulled_articles"
    if not os.path.exists(save_dir):
        return
    
    for filename in os.listdir(save_dir):
        if filename.endswith("_urls.txt"):
            file_path = os.path.join(save_dir, filename)
            try:
                os.remove(file_path)
                print(f"🧹 Deleted URL file: {filename}")
            except Exception as e:
                print(f"⚠️ Could not delete {filename}: {e}")



async def fetch_article(session, url, source):
    """ Asynchronous request to fetch an article """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }
        async with session.get(url, timeout = 10 ) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')

            title_tag = soup.select_one('h1, h2')  # Try multiple header tags
            title_text = title_tag.get_text(strip=True) if title_tag else "Untitled"
            content_text = ""
            #Blocklanıp blocklanmadığımızı test ediyoruz
            if "blocked" in title_text.lower() or "access denied" in title_text.lower():
                print(f"🚫 Blocked by site: {url}")
                return {
                    "title": title_text,
                    "content": "",
                    "url": url,
                    "source": source,
                    "genre": genre,
                    "article_date": datetime.now().isoformat(),
                    "request_date": datetime.now().isoformat(),
                    "is_empty": True,
                    "error": "Blocked by site"
                }
            
            if source == "cnnturk":  # CNNTURK-specific extraction (Already Implemented)
                content_blocks = soup.select("section.detail-content p")
            elif source == "sabah":  # **Sabah-specific extraction**
                # Try multiple selectors based on observed article structures
                content_blocks = (
                    soup.select("div.newsDetailText div.newsBox p") or  # Sports articles
                    soup.select("div.page.flex-grow-1 p") or  # General articles
                    soup.select("div.page[data-page] p") or  # Some dynamic-loaded articles
                    soup.select("main p")  # Last resort for any text within <main>
                )
            elif source == "t24":
                content_blocks = soup.select("div[class*='3QVZl'] p")  # Select paragraphs inside T24 content div
            elif source == "ntv":
                content_blocks = soup.select("div[class*='content-news-tag-selector'] p")  # Select paragraphs inside T24 content div
            elif source == "nefes":
                content_blocks = soup.select("div.post-content p")
                if not content_blocks:
                    content_blocks = soup.select("article p, main p")
            elif source == "haber_sol":
                content_blocks = soup.select("div.article-content div.font-mukta p")
                if not content_blocks:
                    content_blocks = soup.select("article p, div.field__item p, main p")
            elif source == "gazete_duvar":
                content_blocks = soup.select("div.content-text p")
                if not content_blocks:
                    content_blocks = soup.select("article p, main p, div[class*='article-body'] p")
            elif source == "evrensel":
                content_blocks = soup.select("div[class^='news-'] p")  # tüm news-* div'leri hedef alır
                if not content_blocks:
                    content_blocks = soup.select("div[class*='content'] p, article p, main p")
            elif source == "sendika":  # 📌 Bunu buraya ekle
                title_tag = soup.select_one("h3.title")
                title_text = title_tag.get_text(strip=True) if title_tag else "Untitled"
                content_blocks = soup.select("div#news p")
                if not content_blocks:
                    content_blocks = soup.select("article p, main p")
            else:
                # General extraction
                content_blocks = soup.select("div[class*='content'] p, div[class*='article-body'] p, div[class*='news'] p")

            content_text = " ".join([p.get_text(strip=True) for p in content_blocks])

            # Check if the article is empty
            is_empty = len(content_text.strip()) == 0

            # ✅ Extract Genre from URL
            parsed_url = urllib.parse.urlparse(url)
            path_parts = parsed_url.path.strip("/").split("/")  # Split URL path

            ##aşağısı eklendi, "error": "cannot access local variable 'genre' where it is not associated with a value" sorunu çözümü için
            genre = path_parts[0] if path_parts else "unknown" # Use the first part as genre if not "unknown"
            ## 
            if source == "haberturk":
                genre = "unknown"

            return {
                "title": title_text,
                "content": content_text,
                "url": url,
                "source": source,
                "genre": genre,
                "article_date": datetime.now().isoformat(),
                "request_date": datetime.now().isoformat(),
                "is_empty": is_empty
            }
    except Exception as e:
        return {"url": url, "source": source, "error": str(e)}  # ✅ Always return a dictionary



async def scrape_articles_async(article_urls, source):
    """ Run multiple article scrapes concurrently """
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_article(session, url, source) for url in article_urls]  # ✅ Pass source
        results = await asyncio.gather(*tasks)
    return results

rss_sources = {
    "tele1": [
        "https://tele1.com.tr/rss",
        "https://www.tele1.com.tr/rss/tum-mansetler",
        "https://www.tele1.com.tr/rss/bilim-ve-teknoloji-evreni"
    ],
    "gazete_duvar": [ "https://www.gazeteduvar.com.tr/export/rss" ],
    "sozcu": [
        "https://www.sozcu.com.tr/feeds-rss-category-ekonomi",
        "https://www.sozcu.com.tr/feeds-rss-category-spor",
        "https://www.sozcu.com.tr/feeds-rss-category-gundem",
        "https://www.sozcu.com.tr/feeds-son-dakika",
        "https://www.sozcu.com.tr/feeds-haberler",
        "https://www.sozcu.com.tr/feeds-rss-category-dunya"
    ],
    "artıgercek": [
        "https://artigercek.com/export/rss"
    ],
    "politikyol": [ "https://www.politikyol.com/rss" 
                    "https://www.politikyol.com/rss/ekonomi",
                    "https://www.politikyol.com/rss/gundem",
                    "https://www.politikyol.com/rss/emek",
                    "https://www.politikyol.com/rss/politika",
                    "https://www.politikyol.com/rss/spor",],
    "diken": [ "https://www.diken.com.tr/feed/"
            ],
    "yeni_safak": [ "https://www.yenisafak.com/rss?xml=gundem",
                    "https://www.yenisafak.com/rss?xml=ekonomi",
                    "https://www.yenisafak.com/rss?xml=spor",
                    "https://www.yenisafak.com/rss?xml=dunya",
                    "https://www.yenisafak.com/rss?xml=sondakika",
                    "https://www.yenisafak.com/rss?xml=teknoloji",
                    "https://www.yenisafak.com/rss?xml=saglik",
                    "https://www.yenisafak.com/rss?xml=yasam",
                    "https://www.yenisafak.com/rss?xml=kultur-sanat",],
                   
    "trt_haber": [  "https://www.trthaber.com/sondakika.rss",
                  ],
    "halktv" : [    "https://halktv.com.tr/service/rss.php",],
    "haberturk": [  "https://www.haberturk.com/rss",
                    "https://www.haberturk.com/rss/ekonomi.xml",
                    "https://www.haberturk.com/rss/spor.xml",
                    "https://www.haberturk.com/rss/kategori/siyaset.xml",
                    "https://www.haberturk.com/rss/kategori/is-yasam.xml",
                    "https://www.haberturk.com/rss/kategori/gundem.xml",
                    "https://www.haberturk.com/rss/kategori/dunya.xml",
                    "https://www.haberturk.com/rss/kategori/teknoloji.xml",
                   ],

}

def get_articles_from_rss(source, num_articles=100):
    if source not in rss_sources:
        print(f"❌ Source {source} has no defined RSS feeds.")
        return []

    rss_urls = rss_sources[source]
    links = []

    for rss_url in rss_urls:
        print(f"📡 Fetching RSS: {rss_url}")

        try:
            feed = feedparser.parse(rss_url)
            # 🔥 Bozuk RSS yakala
            if getattr(feed, "bozo", False):
                print(f"⚠️ Warning: RSS feed {rss_url} is malformed. Skipping...")
                continue
        except Exception as e:
            print(f"⚠️ Failed to parse RSS feed {rss_url}: {e}")
            continue

        for entry in feed.entries:
            if 'link' in entry and entry.link not in links:
                links.append(entry.link)
                if len(links) >= num_articles:
                    break

        if len(links) >= num_articles:
            break

    print(f"✅ Found {len(links)} articles from {source} RSS.")
    return links

def save_articles_multithreaded(articles):
    print(f"🔄 Saving {len(articles)} articles using multi-threading...")  # Debugging

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(save_json_locally, articles))

    print("✅ All articles saved successfully!")




# Function to find article URLs on the homepage or a category page
def find_article_urls(source, num_articles=30, max_pages=10):
    base_url = source_urls.get(source.lower())
    if not base_url:
        print(f"❌ Source {source} is not supported.")
        return []
    # ✅ Buraya özel kategori sayfaları:
    if source == "evrensel":
        category_urls = [f"{base_url}kategori/{i}" for i in range(1, 11)]
    else:
        category_urls = [base_url]
    try:
        session = requests.Session()
        article_urls = set()
        category_tracking = defaultdict(lambda: {"urls": set(), "empty_pages": 0})  # Tracks URLs and empty page count per category
        page = 1
        stagnant_count = 0  # How many times in a row the article count didn't increase
        prev_article_total = 0

        while len(article_urls) < num_articles and page <= max_pages:
            url = f"{base_url}?page={page}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            }
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            print(f"\n🧪 {url} response preview:\n{response.text[:1000]}\n{'-'*60}\n")
            soup = BeautifulSoup(response.text, 'html.parser')

            new_articles_found = False

            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)

                if any(excluded in full_url for excluded in config.EXCLUDED_URL_KEYWORDS):
                    continue

                parsed_url = urlparse(full_url)
                path_parts = parsed_url.path.strip("/").split("/")
                category = path_parts[0] if path_parts else "unknown"

                if parsed_url.netloc == urlparse(base_url).netloc:
                    if any(keyword in full_url for keyword in config.URL_FIELDS):
                        if full_url not in category_tracking[category]["urls"]:
                            category_tracking[category]["urls"].add(full_url)
                            article_urls.add(full_url)
                            new_articles_found = True

            current_total = len(article_urls)
            if current_total == prev_article_total:
                stagnant_count += 1
            else:
                stagnant_count = 0
            prev_article_total = current_total

            print(f"📄 Checked page {page} for {source}, found {current_total} articles so far.")

            if stagnant_count >= 7:
                print(f"🔁 Stopping early for {source} after {stagnant_count} stagnant pages.")
                break

            page += 1

        print(f"✅ Final count: {len(article_urls)} articles found for {source}")

        return list(article_urls)[:num_articles]

    except requests.RequestException as e:
        print(f"❌ Failed to retrieve articles from {source}: {e}")
        return []





# Track empty content counts globally
empty_content_counts = {}


def create_jsons_from_source(source, num_articles=300):
    if source in rss_sources:
        article_urls = get_articles_from_rss(source, num_articles)
    else:
        article_urls = find_article_urls(source, num_articles)

    if not article_urls:
        print(f"❌ No articles found for {source}")
        article_counts[source] = 0
        empty_content_counts[source] = 0
        return 0  # Return 0 new articles

    # ✅ Yeni kısım: Eski URL'leri yükle
    existing_urls = load_saved_urls(source)

    # ✅ Sadece yeni URL'leri al
    new_article_urls = [url for url in article_urls if url not in existing_urls]

    if not new_article_urls:
        print(f"⚠️ No new articles found for {source}.")
        article_counts[source] = 0
        empty_content_counts[source] = 0
        return 0

    # Fetch the articles
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    articles = loop.run_until_complete(scrape_articles_async(new_article_urls, source))

    # Save the articles
    save_articles_multithreaded(articles)

    # Save newly processed URLs
    for url in new_article_urls:
        save_url(source, url)

    # Count
    empty_count = sum(1 for article in articles if not article.get("content") or article.get("is_empty", False))
    empty_content_counts[source] = empty_count
    article_counts[source] = len(articles)

    print(f"📊 {source}: {len(articles)} articles saved ({empty_count} empty)")

    # ✅ Return kaç yeni article bulundu
    return len(new_article_urls)


import os
import json
import time
from datetime import datetime

# Bu değişkenlerin zaten dosyada tanımlı olması lazım:
# - source_urls
# - create_jsons_from_source
# - article_counts
# - empty_content_counts
def log_scraper_activity(new_articles_count, log_file="scraper_log.txt"):
    """Logs the number of new articles found during a scrape cycle."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if new_articles_count > 0:
        log_entry = f"[{timestamp}] ✅ {new_articles_count} new articles found and saved.\n"
    else:
        log_entry = f"[{timestamp}] ⚠️ No new articles found.\n"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

def run_all_sources_incremental():
    start_time = time.time()

    total_attempted = 0
    total_saved = 0
    total_new_articles = 0

    for source in source_urls.keys():
        new_articles = create_jsons_from_source(source, 300)
        total_new_articles += new_articles

    end_time = time.time()
    execution_time = end_time - start_time

    print("\n📊 SUMMARY:")
    for source, count in article_counts.items():
        empty_count = empty_content_counts.get(source, 0)
        print(f"✅ {source}: {count} articles ({empty_count} empty)")
        total_attempted += count
        total_saved += (count - empty_count)

    print("\n📈 OVERALL:")
    print(f"🔢 Total articles found (including errors and empty ones): {total_attempted}")
    print(f"🗑️ Invalid or empty articles removed: {total_attempted - total_saved}")
    print(f"✅ Final valid articles saved: {total_saved}")
    print(f"⏳ Total execution time: {execution_time:.2f} seconds")
    print(f"\n🆕 New articles found and saved in this run: {total_new_articles}")


if __name__ == "__main__":
    while True:
        before_run = count_json_files()
        run_all_sources_incremental()
        after_run = count_json_files()
        real_new_files = after_run - before_run
        
        print(f"🆕 Real new JSON files saved in this run: {real_new_files}")
        log_scraper_activity(real_new_files)

        print("\n🕒 Sleeping 900 seconds (15 minutes)...")
        time.sleep(900)







# def run_all_sources():
#     """ Runs scraping for all sources, prints a final summary, and measures execution time """
#     start_time = time.time()

#     # Sayaçlar
#     total_attempted = 0
#     total_saved = 0

#     for source in source_urls.keys():
#         create_jsons_from_source(source, 300)

#     end_time = time.time()
#     execution_time = end_time - start_time

#     # ✅ Print Detailed Summary at the End
#     print("\n📊 SUMMARY:")

#     for source, count in article_counts.items():
#         empty_count = empty_content_counts.get(source, 0)
#         print(f"✅ {source}: {count} articles ({empty_count} empty)")

#         total_attempted += count
#         total_saved += (count - empty_count)

#     print("\n📈 OVERALL:")
#     print(f"🔢 Total articles found (including errors and empty ones): {total_attempted}")
#     print(f"🗑️ Invalid or empty articles removed: {total_attempted - total_saved}")
#     print(f"✅ Final valid articles saved: {total_saved}")
#     print(f"⏳ Total execution time: {execution_time:.2f} seconds")

# Example usage
# create_jsons_from_source("gazete_duvar", 300) 
# create_jsons_from_source("cumhuriyet", 30) 
# create_jsons_from_source("milliyet", 300) 

# create_jsons_from_source("ahaber", 30) 
# create_jsons_from_source("sabah", 300)

# Iterate over all sources in source_urls and scrape articles
#create_jsons_from_source("ntv", 300)

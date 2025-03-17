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

# Base URL for each source
source_urls = config.SOURCE_URLS

# Global dictionary to store article counts
article_counts = {}

import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

async def fetch_article(session, url, source):
    """ Asynchronous request to fetch an article """
    try:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')

            title_tag = soup.select_one('h1, h2')  # Try multiple header tags
            title_text = title_tag.get_text(strip=True) if title_tag else "Untitled"

            content_text = ""

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
            else:
                # General extraction
                content_blocks = soup.select("div[class*='content'] p, div[class*='article-body'] p, div[class*='news'] p")

            content_text = " ".join([p.get_text(strip=True) for p in content_blocks])

            # Check if the article is empty
            is_empty = len(content_text.strip()) == 0

            # ✅ Extract Genre from URL
            parsed_url = urllib.parse.urlparse(url)
            path_parts = parsed_url.path.strip("/").split("/")  # Split URL path

            genre = path_parts[0]

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

    try:
        session = requests.Session()
        article_urls = set()
        category_tracking = defaultdict(lambda: {"urls": set(), "empty_pages": 0})  # Tracks URLs and empty page count per category
        page = 1

        while len(article_urls) < num_articles and page <= max_pages:
            url = f"{base_url}?page={page}"  # Modify for different pagination styles
            response = session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            new_articles_found = False  # Track if we find new articles in this iteration

            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)

                # ✅ Exclude unwanted URLs
                if any(excluded in full_url for excluded in config.EXCLUDED_URL_KEYWORDS):
                    continue  # Skip non-article links

                parsed_url = urlparse(full_url)
                path_parts = parsed_url.path.strip("/").split("/")

                # ✅ Determine article category
                category = path_parts[0] if path_parts else "unknown"

                # ✅ Ensure the URL matches article criteria
                if parsed_url.netloc == urlparse(base_url).netloc:
                    if any(keyword in full_url for keyword in config.URL_FIELDS):
                        if full_url not in category_tracking[category]["urls"]:  # Avoid duplicates
                            category_tracking[category]["urls"].add(full_url)
                            article_urls.add(full_url)
                            new_articles_found = True  # Found a new article

            # ✅ Check empty-page condition for stopping per category
            for category, data in category_tracking.items():
                if len(data["urls"]) == 0:
                    data["empty_pages"] += 1
                else:
                    data["empty_pages"] = 0  # Reset if we found articles

            if not new_articles_found:  # If no new articles were found in this entire page
                if all(data["empty_pages"] >= 2 for data in category_tracking.values()):
                    print(f"🔴 No new articles found in any category on page {page}, stopping early for {source}.")
                    break  # Stop if all categories hit the empty page limit

            print(f"📄 Checked page {page} for {source}, found {len(article_urls)} articles so far.")
            page += 1  # Move to the next page

        print(f"✅ Final count: {len(article_urls)} articles found for {source}")

        return list(article_urls)[:num_articles]

    except requests.RequestException as e:
        print(f"❌ Failed to retrieve articles from {source}: {e}")
        return []




# Track empty content counts globally
empty_content_counts = {}

# Track empty content counts globally
empty_content_counts = {}

def create_jsons_from_source(source, num_articles=300):
    """ Scrapes and saves articles using async + threading """
    article_urls = find_article_urls(source, num_articles)
    
    if not article_urls:
        print(f"❌ No articles found for {source}")
        article_counts[source] = 0
        empty_content_counts[source] = 0  # No empty articles
        return
    
    # Use asyncio to fetch articles asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    articles = loop.run_until_complete(scrape_articles_async(article_urls, source))
 
    # ✅ Correctly Count Empty Articles
    empty_count = sum(1 for article in articles if not article.get("content") or article.get("is_empty", False))
    empty_content_counts[source] = empty_count

    # Save articles using multi-threading
    save_articles_multithreaded(articles)

    # Store count for later summary
    article_counts[source] = len(articles)

    # ✅ Print empty count immediately after processing a source
    print(f"📊 {source}: {len(articles)} articles saved ({empty_count} empty)")





def run_all_sources():
    """ Runs scraping for all sources, prints a final summary, and measures execution time """
    start_time = time.time()

    for source in source_urls.keys():
        create_jsons_from_source(source, 300)

    end_time = time.time()
    execution_time = end_time - start_time

    # ✅ Print Summary at the End
    print("\n📊 Summary of articles saved:")
    total = 0
    for source, count in article_counts.items():
        empty_count = empty_content_counts.get(source, 0)
        print(f"✅ {source}: {count} articles ({empty_count} empty)")
        total += count

    print(f"\n📈 Total articles saved: {total}")
    print(f"⏳ Total execution time: {execution_time:.2f} seconds")

# Example usage
# create_jsons_from_source("ntv", 30) 
# create_jsons_from_source("cumhuriyet", 30) 
# create_jsons_from_source("milliyet", 30) 

# create_jsons_from_source("ahaber", 30) 
#create_jsons_from_source("sabah", 300)

# Iterate over all sources in source_urls and scrape articles
run_all_sources()
#create_jsons_from_source("ntv", 300)

import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, urljoin
import re
from urllib.parse import urlparse, urljoin

from API_1 import scrape_news_general, save_json_locally

# Base URL for each source
source_urls = {
    "milliyet": "https://www.milliyet.com.tr/",
    "hurriyet": "https://www.hurriyet.com.tr/",
    "cumhuriyet": "https://www.cumhuriyet.com.tr/",
    # Add additional sources as needed
}

# Function to find article URLs on the homepage or a category page
from urllib.parse import urlparse, urljoin

def find_article_urls(source, num_articles=100):
    base_url = source_urls.get(source.lower())
    if not base_url:
        print(f"Source {source} is not supported.")
        return []
    
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        article_urls = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Parse the URL and split into path segments
            parsed_url = urlparse(full_url)
            path_segments = parsed_url.path.strip('/').split('/')

            # # Criteria to consider a URL as a potential article URL
            # if len(path_segments) >= 3 and not parsed_url.path.endswith('/'):
            #     # Exclude URLs with keywords that are very unlikely to be articles
            #     if not any(keyword in full_url for keyword in ["tag", "category", "etiket", "kategori"]):
            #         print("AAAAAAAA")
            article_urls.add(full_url)
            
            # Continue until we meet the desired number of article URLs
            if len(article_urls) >= num_articles:
                break

        # Convert to list and return the first `num_articles` entries
        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        print(len(list(article_urls)))
        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

        return list(article_urls)[:num_articles]
    
    except requests.RequestException as e:
        print(f"Failed to retrieve articles from {source}: {e}")
        return []




# Function to create JSON files from a given source and number of articles
def create_jsons_from_source(source, num_articles=10):
    # Find article URLs
    article_urls = find_article_urls(source, num_articles)
    print(f"Found {len(article_urls)} URLs for {source}")

    # Iterate over each URL and scrape/save if content is non-empty
    for url in article_urls:
        news_data = scrape_news_general(url)  # Call the existing scrape function
        
        # Only save if content is non-empty
        if news_data['content']:
            save_json_locally(news_data)  # Save function only saves if content is provided
            print(f"Saved JSON for URL: {url}")
        else:
            print(f"Skipped URL with empty content: {url}")

# Example usage
create_jsons_from_source("cumhuriyet", 1000) 




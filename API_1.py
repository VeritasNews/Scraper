import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, Response
from datetime import datetime
from urllib.parse import urlparse
import config

app = Flask(__name__)

# Directory for saving JSON files
PULLED_ARTICLES_SAVE_DIR = config.PULLED_ARTICLES_SAVE_DIR

# Ensure the save directory exists
if not os.path.exists(PULLED_ARTICLES_SAVE_DIR):
    os.makedirs(PULLED_ARTICLES_SAVE_DIR)
    print(f"📂 Created save directory: {PULLED_ARTICLES_SAVE_DIR}")
else:
    print(f"📂 Save directory exists: {PULLED_ARTICLES_SAVE_DIR}")



    
# Function to auto-detect the source based URL dictonary
def detect_source(url):
    source_urls = config.SOURCE_URLS
    for source, base_url in source_urls.items():
        if base_url in url:
            return source.replace("_", " ").title()  # Format for readability
    return "Unknown"


# Function to extract genre from URL path
def get_genre_from_url(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    
    common_genres = {
    "spor": "Sports", "sport": "Sports",
    "ekonomi": "Economy", "economy": "Economy",
    "siyaset": "Politics", "politics": "Politics",
    "gundem": "Current Affairs", "current": "Current Affairs",
    "dunya": "World", "world": "World",
    "teknoloji": "Technology", "technology": "Technology",
    "kultur": "Culture", "culture": "Culture",
    "sanat": "Art", "art": "Art",
    "egitim": "Education", "education": "Education",
    "saglik": "Health", "health": "Health",
    "yasam": "Lifestyle", "lifestyle": "Lifestyle",
    "magazin": "Entertainment", "entertainment": "Entertainment",
    "bilim": "Science", "science": "Science",
    "cevre": "Environment", "environment": "Environment",
    "yerel": "Local News", "local": "Local News",
    "insan-haklari": "Human Rights", "human-rights": "Human Rights",
    "kadin": "Women", "women": "Women",
    "cocuk": "Children", "child": "Children",
    "goc": "Migration", "migration": "Migration",
    "kultur-sanat": "Culture and Arts", "culture-art": "Culture and Arts",
    "finans": "Finance", "finance": "Finance",
    "yatirim": "Investment", "investment": "Investment",
    "otomobil": "Automotive", "automotive": "Automotive",
    "hava-durumu": "Weather", "weather": "Weather",
    "analiz": "Analysis", "analysis": "Analysis",
    "yorum": "Opinion", "opinion": "Opinion",
    "editoryal": "Editorial", "editorial": "Editorial",
    "roportaj": "Interview", "interview": "Interview",
    "video": "Video", "photo": "Video",
    "foto": "Photography", "photo": "Photography",
    "asker": "Military", "military": "Military",
    "savunma": "Defense", "defense": "Defense",
    "ticaret": "Trade", "trade": "Trade",
    "turizm": "Tourism", "tourism": "Tourism",
    "maliye": "Finance", "finance": "Finance",
    "ulasim": "Transportation", "transportation": "Transportation",
    "medya": "Media", "media": "Media",
    "hukuk": "Law", "law": "Law",
    "sektor": "Sector News", "sector": "Sector News",
    "muhasebe": "Accounting", "accounting": "Accounting",
    "internet": "Internet", "internet": "Internet",
    "siber": "Cybersecurity", "cybersecurity": "Cybersecurity",
    "yazilim": "Software", "software": "Software",
    "eglence": "Entertainment", "entertainment": "Entertainment",
    "film": "Movies", "movie": "Movies",
    "muzik": "Music", "music": "Music",
    "dizi": "TV Series", "series": "TV Series",
    "moda": "Fashion", "fashion": "Fashion",
    "astroloji": "Astrology", "astrology": "Astrology",
    "psikoloji": "Psychology", "psychology": "Psychology",
    "yemek": "Food", "food": "Food",
    "tarim": "Agriculture", "agriculture": "Agriculture",
    "hayvanlar": "Animals", "animals": "Animals",
    "politik": "Political", "political": "Political",
    "ulasim": "Transportation", "transportation": "Transportation",
    "hava-durumu": "Weather", "weather": "Weather",
    "emlak": "Real Estate", "real-estate": "Real Estate",
    "sanayi": "Industry", "industry": "Industry",
    "enerji": "Energy", "energy": "Energy",
    "insaat": "Construction", "construction": "Construction",
    "krediler": "Loans", "loans": "Loans",
    "vergi": "Taxation", "tax": "Taxation",
    "bankacilik": "Banking", "banking": "Banking"
    }

    
    for part in path_parts:
        genre = common_genres.get(part.lower())
        if genre:
            return genre
    return "Unknown"  # Default if no genre is found

# Function to extract the article's publication date
def extract_article_date(soup):
    """ Extracts the article publication date from multiple possible sources. """
    date_selectors = [
        ('meta', {'property': 'article:published_time'}),
        ('meta', {'name': 'date'}),
        ('meta', {'name': 'publish_date'}),
        ('meta', {'name': 'article:modified_time'})
    ]

    for tag, attr in date_selectors:
        date_tag = soup.find(tag, attr)
        if date_tag and date_tag.get('content'):
            return date_tag['content']

    return None  # Return None if no valid date is found

def extract_json_ld_data(soup):
    """ Extracts structured JSON-LD data if available. """
    json_ld_tag = soup.find('script', type='application/ld+json')
    if json_ld_tag:
        try:
            data = json.loads(json_ld_tag.string)
            return data
        except json.JSONDecodeError:
            return None
    return None

# General-purpose scraping function
def scrapeArticleGeneral(url):
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # ✅ Try JSON-LD First (Most Reliable)
        json_ld_data = extract_json_ld_data(soup)
        if json_ld_data:
            title = json_ld_data.get("headline", "No Title Found")
            content = json_ld_data.get("articleBody", "").strip()  # Ensure content is not just whitespace
            article_date = json_ld_data.get("datePublished", datetime.now().isoformat())
        else:
            # ✅ HTML-Based Extraction as Fallback
            title_tag = soup.select_one('h1, h2, meta[property="og:title"], meta[name="title"]')
            title = title_tag.get_text(strip=True) if title_tag else "No Title Found"

            content_paragraphs = soup.select('article p, div[class*="content"] p, div[class*="article-body"] p')
            content = " ".join([p.get_text(strip=True) for p in content_paragraphs]).strip()

            article_date = extract_article_date(soup) or datetime.now().isoformat()

        # ✅ Detect Empty Content
        is_empty = len(content) == 0

        # ✅ Extract Images (Optional)
        image_tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        image_url = image_tag["content"] if image_tag else None

        # ✅ Extract Source and Genre
        source = detect_source(url)
        genre = get_genre_from_url(url)

        # ✅ Return Final Data
        news_data = {
            "title": title,
            "content": content,
            "source": source,
            "genre": genre,
            "article_date": article_date,
            "request_date": datetime.now().isoformat(),
            "url": url,
            "image": image_url,  # New field
            "is_empty": is_empty  # ✅ Mark if the content is empty
        }

        return news_data

    except Exception as e:
        return {
            "title": "API failed",
            "content": "",
            "source": detect_source(url),
            "genre": get_genre_from_url(url),
            "article_date": "N/A",
            "request_date": datetime.now().isoformat(),
            "url": url,
            "error": str(e),
            "is_empty": True  # Treat errors as empty content
        }


# Function to save JSON data to a local file with source and publication date
def save_json_locally(data, location=""):
    if location == "":
        location = PULLED_ARTICLES_SAVE_DIR

    # Ensure directory exists
    if not os.path.exists(location):
        os.makedirs(location)

    # Handle missing fields safely
    title = data.get("title", "Untitled")  # Default to "Untitled" if missing
    source = data.get("source", "unknown")  # Default to "unknown"
    article_date = data.get("article_date", "unknown_date")  # Default date

    # Clean title for filename
    filename_title = "".join(c if c.isalnum() else "_" for c in title)[:50]
    filename = f"{source}_{article_date[:10]}_{filename_title}.json"
    filepath = os.path.join(location, filename)

    try:
        print(f"📥 Saving file: {filepath}")  # Debugging line
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ Successfully saved: {filepath}")  # Success message
    except Exception as e:
        print(f"❌ Failed to save file: {filepath}, Error: {e}")


def scrape_cnnturk(url):
    """ Scrapes articles from CNN Türk correctly. """
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # ✅ Extract Title
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "No Title Found"

        # ✅ Extract Content
        content_section = soup.find('section', class_='detail-content')
        if content_section:
            paragraphs = content_section.find_all('p')
            content = " ".join([p.get_text(strip=True) for p in paragraphs]).strip()
        else:
            content = ""

        # ✅ Extract Date
        article_date = extract_article_date(soup) or datetime.now().isoformat()

        # ✅ Extract Image (Optional)
        image_tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        image_url = image_tag["content"] if image_tag else None

        # ✅ Return Structured Data
        return {
            "title": title,
            "content": content,
            "source": "cnnturk",
            "article_date": article_date,
            "request_date": datetime.now().isoformat(),
            "url": url,
            "image": image_url,
            "is_empty": content == ""  # ✅ Mark empty content
        }

    except Exception as e:
        return {
            "title": "API failed",
            "content": "",
            "source": "cnnturk",
            "article_date": "N/A",
            "request_date": datetime.now().isoformat(),
            "url": url,
            "error": str(e),
            "is_empty": True  # ✅ Mark as empty in case of failure
        }


def scrapeArticle(url):
    """ Determines the source and calls the appropriate scraping function. """
    source = detect_source(url)

    if source == "cnnturk":
        print("Using CNN Scraper")
        return scrape_cnnturk(url)  # ✅ Use CNN Türk-specific scraper
    else:
        print("Using General Scraper")
        return scrapeArticleGeneral(url)  # ✅ Use general scraper for other sources


@app.route('/api/scrape', methods=['GET'])
def scrape_news():
    url = request.args.get('url')
    save = request.args.get('save', 'false').lower() == 'true'
    
    if not url:
        return Response(json.dumps({"error": "URL is a required parameter"}), status=400, mimetype='application/json')
    
    news_data = scrapeArticleGeneral(url)
    
    # Save JSON data locally if the 'save' parameter is set to true
    if save:
        print("HIT HIT HIT HIT")
        save_json_locally(news_data)
    else:
        save_json_locally(news_data) # Note: Değiştir Change
        print("NO SAVE NO SAVE NO SAVE")
    
    return Response(json.dumps(news_data, ensure_ascii=False), mimetype='application/json')

if __name__ == '__main__':
    app.run(debug=True)

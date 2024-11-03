import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, Response
from datetime import datetime
from urllib.parse import urlparse

app = Flask(__name__)

# Directory for saving JSON files
SAVE_DIR = "saved_articles"

# Ensure the save directory exists
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Function to auto-detect the source based on URL patterns
def detect_source(url):
    if "hurriyet.com.tr" in url:
        return "Hürriyet"
    elif "sozcu.com.tr" in url:
        return "Sözcü"
    elif "haberturk.com" in url:
        return "Habertürk"
    elif "ntv.com.tr" in url:
        return "NTV"
    elif "milliyet.com.tr" in url:
        return "Milliyet"
    elif "cumhuriyet.com.tr" in url:
        return "Cumhuriyet"
    else:
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
    # Check common meta tags for publication date
    date_tag = soup.find('meta', {'name': 'pubdate'}) or soup.find('meta', {'property': 'article:published_time'}) or soup.find('meta', {'name': 'date'})
    if date_tag and date_tag.get('content'):
        return date_tag['content']  # Return the date found in the tag
    return None  # None if no date is found

# General-purpose scraping function
def scrape_news_general(url):
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.select_one('h1')
        title_text = title.get_text(strip=True) if title else "No Title Found"
        
        content_paragraphs = soup.select('div[class*="content"] p') or soup.select('div[class*="article-body"] p')
        content_text = " ".join([p.get_text(strip=True) for p in content_paragraphs])
        
        # Extract publication date from the article
        article_date = extract_article_date(soup) or datetime.now().isoformat()
        
        source = detect_source(url)
        genre = get_genre_from_url(url)

        # Prepare JSON data with both article_date and request_date
        news_data = {
            "title": title_text,
            "content": content_text,
            "source": source,
            "genre": genre,
            "article_date": article_date,  # Article publication date
            "request_date": datetime.now().isoformat(),  # Date of request
            "url": url
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
            "error": str(e)
        }

# Function to save JSON data to a local file with source and publication date
def save_json_locally(data):
    # Clean title for filename
    filename_title = "".join(c if c.isalnum() else "_" for c in data['title'])[:50]
    # Use the source and article publication date in filename
    filename = f"{data['source']}_{data['article_date'][:10]}_{filename_title}.json"
    filepath = os.path.join(SAVE_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/api/scrape', methods=['GET'])
def scrape_news():
    url = request.args.get('url')
    save = request.args.get('save', 'false').lower() == 'true'
    
    if not url:
        return Response(json.dumps({"error": "URL is a required parameter"}), status=400, mimetype='application/json')
    
    news_data = scrape_news_general(url)
    
    # Save JSON data locally if the 'save' parameter is set to true
    if save:
        save_json_locally(news_data)
    
    return Response(json.dumps(news_data, ensure_ascii=False), mimetype='application/json')

if __name__ == '__main__':
    app.run(debug=True)

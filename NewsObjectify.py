import re
import json
import os
import sys
import io
import uuid
import time
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
from io import BytesIO
import google.generativeai as genai

# ✅ Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ✅ Import config
from config import (
    my_key_gemini,
    GROUPED_ARTICLES_PULL_DIR as INPUT_DIR,
    OBJECTIVE_ARTICLES_DIR as OUTPUT_DIR
)

# ✅ Backend Insert URL
BACKEND_INSERT_URL = "http://localhost:8000/api/insert_single_article/"

# ✅ Configure Gemini
genai.configure(api_key=my_key_gemini)

# === Image Fetching Functions ===
def slugify(text):
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in text.strip())[:60]

def extract_og_image(soup):
    tag = soup.find("meta", property="og:image")
    if tag and tag.get("content"):
        return tag["content"]
    return None

def extract_first_article_img(soup):
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and src.startswith("http"):
            return src
    return None

def download_image(url, save_path):
    try:
        r = requests.get(url, timeout=10)
        img = Image.open(BytesIO(r.content))
        img.save(save_path)
        return True
    except Exception as e:
        print(f"❌ Could not download image {url}: {e}")
        return False

def fetch_article_image(source_urls, output_folder):
    img_path = output_folder / "image.jpg"
    
    for url in source_urls:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")

            img_url = extract_og_image(soup) or extract_first_article_img(soup)
            if img_url and download_image(img_url, img_path):
                return "image.jpg"
        except Exception as e:
            print(f"⚠️ Error accessing {url} for image: {e}")
    return None

# ✅ Helper Functions
def find_matched_news_dirs(base_dir):
    return [
        os.path.join(base_dir, d)
        for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
    ]

def read_json_files(directory):
    articles = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                articles.append(json.load(file))
    return articles

def call_gemini(prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    time.sleep(3)
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return "Error"

def process_articles_with_ai(articles):
    articles_combined = "\n".join([json.dumps(a, ensure_ascii=False) for a in articles])

    prompts = {
        "title": "Bu haber makalelerine dayanarak, 2-3 kelimelik nesnel bir başlık oluşturun:",
        "short_summary": "Bu haber makalelerine dayanarak, 10-25 karakter arasında kısa, salt bilgi içeren bir özet oluşturun:",
        "detailed_summary": "Bu haber makalelerine dayanarak detaylı ve salt bilgi içeren bir özet oluşturun:",
        "category": """
        Bu haber makalesini aşağıdaki kategorilerden birine atayın:
        Siyaset, Eğlence, Spor, Teknoloji, Sağlık, Çevre, Bilim, Eğitim,
        Ekonomi, Seyahat, Moda, Kültür, Suç, Yemek, Yaşam Tarzı, İş Dünyası,
        Dünya Haberleri, Oyun, Otomotiv, Sanat, Tarih, Uzay, İlişkiler, Din,
        Ruh Sağlığı, Magazin. Eğer bulamazsan 'Genel' yaz.
        """
    }

    result = {
        "id": None,
        "articleId": str(uuid.uuid4()),
        "title": call_gemini(f"{prompts['title']}\n{articles_combined}"),
        "summary": call_gemini(f"{prompts['short_summary']}\n{articles_combined}"),
        "longerSummary": call_gemini(f"{prompts['detailed_summary']}\n{articles_combined}"),
        "category": call_gemini(f"{prompts['category']}\n{articles_combined}"),
        "content": "",
        "tags": [],
        "source": list({a["url"].strip() for a in articles if a.get("url")}),
        "location": None,
        "popularityScore": 0,
        "createdAt": datetime.now().isoformat(),
        "image": None,
        "priority": None
    }
    return result

def save_article_folder(article_data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    folder_name = f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    folder_path = OUTPUT_DIR / folder_name
    os.makedirs(folder_path, exist_ok=True)

    # Fetch and save image if source URLs exist
    if article_data.get("source"):
        article_data["image"] = fetch_article_image(article_data["source"], folder_path)

    article_json_path = folder_path / "article.json"
    with open(article_json_path, 'w', encoding='utf-8') as f:
        json.dump(article_data, f, ensure_ascii=False, indent=4)

    print(f"✅ Saved objectified article at {folder_path}")
    return folder_path

def truncate_field(name, value, max_len=100):
    if isinstance(value, str) and len(value) > max_len:
        print(f"✂️ Truncating {name} from {len(value)} to {max_len} chars")
        return value[:max_len]
    return value

def send_article_with_image(folder_path):
    json_path = folder_path / "article.json"
    image_path = folder_path / "image.jpg"

    if not json_path.exists():
        print(f"❌ Missing article.json at {folder_path}")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        json_data["articleId"] = truncate_field("articleId", json_data.get("articleId", ""))
        json_data["category"] = truncate_field("category", json_data.get("category", ""))
        json_data["location"] = truncate_field("location", json_data.get("location", ""))

        source = json_data.get("source")
        # Keep source as list if possible
        if not isinstance(source, list):
            json_data["source"] = [source] if source else []

        files = {}
        if image_path.exists():
            files["image"] = open(image_path, "rb")

        payload = {
            "data": json.dumps(json_data)
        }

        response = requests.post(BACKEND_INSERT_URL, data=payload, files=files)

        if "image" in files:
            files["image"].close()

        if response.status_code == 201:
            print(f"✅ Successfully uploaded: {folder_path.name}")
        else:
            print(f"❌ Upload failed: {response.status_code} → {response.text}")

    except Exception as e:
        print(f"❌ Error uploading {folder_path}: {str(e)}")

def send_all_articles():
    if not OUTPUT_DIR.exists():
        print("❌ No output directory.")
        return

    folders = [f for f in OUTPUT_DIR.iterdir() if f.is_dir()]
    if not folders:
        print("❌ No folders to send.")
        return

    print(f"🚀 Sending {len(folders)} articles...")

    for folder in folders:
        send_article_with_image(folder)

    print("✅ All uploads completed.")

# ✅ MAIN
def main():
    news_dirs = find_matched_news_dirs(INPUT_DIR)

    if not news_dirs:
        print("❌ No matched news directories.")
        return

    print(f"🔍 Found {len(news_dirs)} groups.")

    for news_dir in news_dirs:
        articles = read_json_files(news_dir)

        if not articles:
            print(f"⚠️ No articles found in {news_dir}. Skipping.")
            continue

        # Remove duplicate titles
        unique_titles = set()
        filtered_articles = []
        for a in articles:
            title = a.get("title", "").strip()
            if title and title not in unique_titles:
                unique_titles.add(title)
                filtered_articles.append(a)

        if not filtered_articles:
            print(f"⚠️ No unique articles in {news_dir}. Skipping.")
            continue

        processed_data = process_articles_with_ai(filtered_articles)
        save_article_folder(processed_data)

    send_all_articles()
    print("🎉 Done!")

if __name__ == "__main__":
    main()
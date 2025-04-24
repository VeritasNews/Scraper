import os
import re
import io
import sys
import json
import uuid
import time
import requests
import google.generativeai as genai
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from config import (
    my_key_gemini,
    GROUPED_ARTICLES_PULL_DIR as INPUT_DIR,
    GENERATED_ARTICLES_SAVE_DIR as OUTPUT_DIR,
    DJANGO_API_URL as INSERT_URL,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
genai.configure(api_key=my_key_gemini)

def find_matched_news_dirs(base_dir):
    return [os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]

def call_gemini_with_retry(prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    delays = [1, 3, 5]
    for delay in delays:
        try:
            return model.generate_content(prompt).text.strip()
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️ Rate limit hit. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"❌ Gemini error: {e}")
                break
    return "Error during generation"

def process_articles_with_ai(articles):
    articles_combined = "\n\n".join([a["content"] for a in articles])
    prompts = {
        "title": "Bu haber makalelerine dayanarak, 3-4 kelimelik nesnel bir başlık oluşturun:",
        "summary": "Bu haber makalelerine dayanarak, 10-50 karakter arasında kısa, betimleme içermeyen, salt bilgi içeren bir özet oluşturun:",
        "detailed": "Bu haber makalelerine dayanarak, detaylı ve salt bilgi içeren bir özet oluşturun:",
        "category": """
        Bu haber makalesini aşağıdaki kategorilerden birine atayın:
        Siyaset, Eğlence, Spor, Teknoloji, Sağlık, Çevre, Bilim, Eğitim,
        Ekonomi, Seyahat, Moda, Kültür, Suç, Yemek, Yaşam Tarzı, İş Dünyası,
        Dünya Haberleri, Oyun, Otomotiv, Sanat, Tarih, Uzay, İlişkiler, Din,
        Ruh Sağlığı, Magazin. Eğer uygun değilse 'Genel' yaz.
        """
    }

    return {
        "articleId": str(uuid.uuid4()),
        "title": call_gemini_with_retry(f"{prompts['title']}\n{articles_combined}"),
        "summary": call_gemini_with_retry(f"{prompts['summary']}\n{articles_combined}"),
        "longerSummary": call_gemini_with_retry(f"{prompts['detailed']}\n{articles_combined}"),
        "category": call_gemini_with_retry(f"{prompts['category']}\n{articles_combined}"),
        "content": "",
        "tags": [],
        "source": list(set([a.get("url", "Unknown") for a in articles if a.get("url")])),
        "location": None,
        "popularityScore": 0,
        "createdAt": datetime.utcnow().isoformat() + "Z",  # <-- this line is fixed
        "image": None,
        "priority": None,
    }

def save_article_folder(data):
    folder_name = f"{data['articleId']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    folder_path = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    json_path = os.path.join(folder_path, "article.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"💾 Saved article to: {json_path}")
    return folder_path

def send_article_with_image(folder_path):
    json_path = os.path.join(folder_path, "article.json")
    image_path = os.path.join(folder_path, "image.jpg")  # optional

    if not os.path.exists(json_path):
        print(f"❌ Missing article.json in {folder_path}")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        source = json_data.get("source")
        if isinstance(source, list):
            json_data["source"] = ", ".join(source)
        else:
            json_data["source"] = source or ""

        payload = {"data": json.dumps(json_data)}
        files = {"image": open(image_path, "rb")} if os.path.exists(image_path) else {}

        print(f"📤 Uploading article: {json_data.get('title')[:40]}...")
        res = requests.post(INSERT_URL, data=payload, files=files)

        if "image" in files:
            files["image"].close()

        if res.status_code == 201:
            print("✅ Upload successful.")
        else:
            print(f"❌ Upload failed: {res.status_code} → {res.text}")

    except Exception as e:
        print(f"❌ Error sending article from {folder_path}: {str(e)}")

def process_directory(news_dir):
    print(f"\n📂 Processing group: {news_dir}")
    articles = []
    for file in os.listdir(news_dir):
        if file.endswith(".json"):
            path = os.path.join(news_dir, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    content = data.get("content", "").strip()
                    url = data.get("url", "").strip()
                    if content:
                        articles.append({"content": content, "url": url})
            except Exception as e:
                print(f"⚠️ Error loading {file}: {e}")

    if len(articles) < 2:
        print("⚠️ Not enough articles. Skipping...")
        return

    article_data = process_articles_with_ai(articles)
    folder = save_article_folder(article_data)
    send_article_with_image(folder)

def main():
    print("🔍 Looking for matched directories...")
    start = time.time()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    news_dirs = find_matched_news_dirs(INPUT_DIR)
    if not news_dirs:
        print("❌ No matched directories found.")
        return

    print(f"✅ Found {len(news_dirs)} groups to process.")
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(process_directory, news_dirs)

    print("🎉 All groups processed.")
    print(f"⏱️ Total time: {round(time.time() - start, 2)}s")

if __name__ == "__main__":
    main()

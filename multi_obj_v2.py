import re
import json
import os
import sys
import io
import uuid
import time
import requests
from pprint import pprint
import google.generativeai as genai
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

INSERT_URL = "http://127.0.0.1:8000/api/insert_articles/"
HEADERS = {"Content-Type": "application/json"}

BASE_DIR = r"C:\Dersler\Current\CS491_492_Senior_Project\demo_app_v3\Backend_v3\News_Modules"
INPUT_DIR = r"C:\Dersler\Current\CS491_492_Senior_Project\demo_app_v3\Backend_v3\News_Modules\matched_v2"
OUTPUT_DIR = r"C:\Dersler\Current\CS491_492_Senior_Project\demo_app_v3\Backend_v3\News_Modules\generated_articles"

CONFIG_FILE = "./config.json"
DJANGO_API_URL = "http://127.0.0.1:8000/api/insert_articles/"

API_KEY = "AIzaSyB0SABSrXhbtgP7r5gQELGyeIygZ7aC1MU"
if API_KEY is None:
    sys.exit("❌ API key is missing. Please check your config file.")

genai.configure(api_key=API_KEY)

def find_matched_news_dirs(base_dir):
    return [
        os.path.join(base_dir, d)
        for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
    ]

# ✅ helper to call Gemini with retry on 429
def call_gemini_with_retry(prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    delays = [1, 3, 5]
    for attempt, delay in enumerate(delays):
        try:
            return model.generate_content(prompt).text.strip()
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️ Rate limit hit. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"❌ Unexpected error: {e}")
                break
    return "Error during generation"

def process_articles_with_ai(articles):
    articles_combined = "\n\n".join([article["content"] for article in articles])

    title_prompt = "Bu haber makalelerine dayanarak, 3-4 kelimelik nesnel bir başlık oluşturun:"
    short_summary_prompt = "Bu haber makalelerine dayanarak, 10-50 karakter arasında kısa, betimleme içermeyen, salt bilgi içeren bir özet oluşturun:"
    detailed_summary_prompt = "Bu haber makalelerine dayanarak, detaylı ve salt bilgi içeren bir özet oluşturun:"
    category_prompt = """
    Bu haber makalesini aşağıdaki kategorilerden birine atayın:
    Siyaset
    Eğlence
    Spor
    Teknoloji
    Sağlık
    Çevre
    Bilim
    Eğitim
    Ekonomi
    Seyahat
    Moda
    Kültür
    Suç
    Yemek
    Yaşam Tarzı
    İş Dünyası
    Dünya Haberleri
    Oyun
    Otomotiv
    Sanat
    Tarih
    Uzay
    İlişkiler
    Din
    Ruh Sağlığı
    Magazin

    Eğer uygun bir kategori bulamazsan, 'Genel' olarak belirle. Bu kategorilerden başka hiçbir şey yazma.
    """

    title = call_gemini_with_retry(f"{title_prompt}\n{articles_combined}")
    short_summary = call_gemini_with_retry(f"{short_summary_prompt}\n{articles_combined}")
    detailed_summary = call_gemini_with_retry(f"{detailed_summary_prompt}\n{articles_combined}")
    category = call_gemini_with_retry(f"{category_prompt}\n{articles_combined}")

    article_id = str(uuid.uuid4())
    sources = list(set([article.get("url", "Unknown") for article in articles if article.get("url")]))

    return {
        "id": None,
        "articleId": article_id,
        "title": title,
        "content": "",
        "summary": short_summary,
        "longerSummary": detailed_summary,
        "category": category,
        "tags": [],
        "source": sources,
        "location": None,
        "popularityScore": 0,
        "createdAt": None,
        "image": None,
        "priority": None
    }

def save_json_output(data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"objectified_summary_{timestamp}.json"
    output_filepath = os.path.join(OUTPUT_DIR, output_filename)

    with open(output_filepath, 'w', encoding='utf-8') as output_file:
        json.dump(data, output_file, ensure_ascii=False, indent=4)

    print(f"✅ Output saved locally at {output_filepath}")
    return output_filepath

def send_json_files():
    if not os.path.exists(OUTPUT_DIR):
        print(f"❌ Directory not found: {OUTPUT_DIR}")
        return

    json_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".json")]
    if not json_files:
        print("❌ No JSON files found in generated_articles directory!")
        return

    print(f"🔍 Found {len(json_files)} objectified JSON files. Sending them to the backend...")

    for json_file in json_files:
        json_path = os.path.join(OUTPUT_DIR, json_file)
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            print(f"\n🔹 Sending file: {json_file} to backend...")
            print("📜 JSON Data (First 300 characters):", json.dumps(data, indent=2)[:300])

            response = requests.post(INSERT_URL, json=data, headers=HEADERS)
            response_json = response.json()

            print(f"📜 Backend Response (Status {response.status_code}): {response_json}")

            if response.status_code == 201:
                print(f"✅ Successfully sent {json_file}!")
            else:
                print(f"❌ Failed to send {json_file} (Server Response): {response.text}")

        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in {json_file}, skipping.")
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error for {json_file}: {str(e)}")
        except Exception as e:
            print(f"❌ Unexpected error in {json_file}: {str(e)}")

    print("✅ All objectified JSONs have been processed.")

def process_directory(news_dir):
    print(f"📂 Processing: {news_dir}")
    articles = []

    for filename in os.listdir(news_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(news_dir, filename)
            with open(filepath, "r", encoding="utf-8") as file:
                json_data = json.load(file)
                content = json_data.get("content", "").strip()
                url = json_data.get("url", "").strip()
                if content:
                    articles.append({"content": content, "url": url})

    if len(articles) < 2:
        print(f"⚠️ Not enough valid articles in {news_dir}, skipping...")
        return

    processed_data = process_articles_with_ai(articles)
    save_json_output(processed_data)
    send_json_files()

def main():
    print("Begin")
    start = time.time()

    news_dirs = find_matched_news_dirs(INPUT_DIR)
    if not news_dirs:
        print("❌ No matched directories found in INPUT_DIR!")
        return

    print(f"🔍 Found {len(news_dirs)} directories to process.")

    print("🗑 Deleting old articles before inserting new ones...")
    try:
        requests.get("http://127.0.0.1:8000/api/delete_articles/")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error deleting old articles: {e}")

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(process_directory, news_dirs)

    print("✅ All directories processed successfully!")
    print(f"⏱️ Completed in {round(time.time() - start, 2)} seconds.")
    print("End")

if __name__ == "__main__":
    main()

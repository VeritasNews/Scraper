import re
import json
import os
import sys
import io
import uuid
import time
import requests
import threading
import concurrent.futures
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
from io import BytesIO
import google.generativeai as genai

# ✅ Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

GEMINI_KEYS = [
    "AIzaSyBbORiPLnFon4Xkj5GyF0GRT4EckyGZCzs",
    "AIzaSyB35InVFxlPrGDqPDrQEABnYsDIx964RfU",
    "AIzaSyCXDETtLkiBHka5dTNMkJz1myjkh-SS2jM"
]

# ✅ Import config
from config import (
    my_key_gemini,
    GROUPED_ARTICLES_DIR as INPUT_DIR,
    OBJECTIVE_ARTICLES_DIR as OUTPUT_DIR
)

# ✅ Backend Insert URL
BACKEND_INSERT_URL = "http://localhost:8000/api/insert_single_article/"

# ======== OPTIMIZED KEY MANAGEMENT ========
class KeyManager:
    def __init__(self, keys):
        self.keys = keys
        self.current_index = 0
        self.key_usage = {key: 0 for key in keys}
        self.error_counts = {key: 0 for key in keys}
        self.lock = threading.Lock()  # For thread safety
    
    def get_current_key(self):
        with self.lock:
            return self.keys[self.current_index]
    
    def rotate_key(self, had_error=False):
        with self.lock:
            if had_error:
                self.error_counts[self.keys[self.current_index]] += 1
            
            # Move to next key
            self.current_index = (self.current_index + 1) % len(self.keys)
            return self.keys[self.current_index]
    
    def mark_usage(self, key):
        with self.lock:
            self.key_usage[key] += 1
    
    def get_healthiest_key(self):
        """Return the key with the lowest error count"""
        with self.lock:
            min_errors = min(self.error_counts.values())
            best_keys = [k for k, v in self.error_counts.items() if v == min_errors]
            # Among keys with minimum errors, choose the least used one
            return min(best_keys, key=lambda k: self.key_usage[k])

# Initialize the key manager
key_manager = KeyManager(GEMINI_KEYS)

# ======== IMPROVED API CALL FUNCTION ========
def call_gemini(prompt, retries=3):
    for attempt in range(retries):
        current_key = key_manager.get_current_key()
        genai.configure(api_key=current_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        try:
            # Add small delay to avoid rate limits
            time.sleep(0.5)
            response = model.generate_content(prompt)
            key_manager.mark_usage(current_key)
            return response.text.strip()
        except Exception as e:
            print(f"⚠️ AI Error with key {current_key}: {e}")
            key_manager.rotate_key(had_error=True)
            
            # On last retry, try the healthiest key
            if attempt == retries - 2:
                best_key = key_manager.get_healthiest_key()
                genai.configure(api_key=best_key)
                print(f"🔄 Trying healthiest key for final attempt")
    
    return "Error"

# ======== IMAGE PROCESSING FUNCTIONS ========
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
        r = requests.get(url, timeout=5)
        img = Image.open(BytesIO(r.content))
        img.save(save_path)
        return True
    except Exception as e:
        print(f"❌ Could not download image {url}: {e}")
        return False

def fetch_article_images_parallel(source_urls, output_folder):
    """Fetch images from multiple URLs in parallel"""
    img_path = output_folder / "image.jpg"
    
    # No URLs to process
    if not source_urls:
        return None
    
    def try_fetch_image(url):
        try:
            resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            
            img_url = extract_og_image(soup) or extract_first_article_img(soup)
            if img_url:
                return img_url
        except Exception as e:
            print(f"⚠️ Error accessing {url} for image: {e}")
        return None
    
    # Try to fetch image URLs in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        img_urls = list(executor.map(try_fetch_image, source_urls))
    
    # Filter out None values
    valid_img_urls = [url for url in img_urls if url]
    
    # Try to download the first valid image
    for img_url in valid_img_urls:
        if download_image(img_url, img_path):
            return "image.jpg"
    
    return None

# ======== OPTIMIZED FILE OPERATIONS ========
def find_matched_news_dirs(base_dir):
    base_path = Path(base_dir)
    return [d for d in base_path.iterdir() if d.is_dir()]

def read_json_files(directory):
    """Read all JSON files from a directory in a more efficient way"""
    articles = []
    directory_path = Path(directory)
    
    # Use list comprehension for more efficient file reading
    file_paths = [f for f in directory_path.iterdir() if f.is_file() and f.suffix.lower() == '.json']
    
    # Process files in batches using a ThreadPool
    with concurrent.futures.ThreadPoolExecutor() as executor:
        def read_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                return None
        
        # Map function over all files and filter out None results
        results = executor.map(read_file, file_paths)
        articles = [article for article in results if article is not None]
    
    return articles

# ======== OPTIMIZED AI PROCESSING ========
def process_articles_with_ai(articles):
    articles_combined = "\n".join([json.dumps(a, ensure_ascii=False) for a in articles])
    
    # Combine prompts to reduce number of API calls
    combined_prompt = f"""
    Analyze these news articles and provide the following:
    1. Title (2-3 words): Create an objective title.
    2. Short Summary (10-25 characters): Create a concise, factual summary.
    3. Detailed Summary: Create a detailed and factual combined text as a single article.
    4. Category: Assign one category from this list: Siyaset, Eğlence, Spor, Teknoloji, Sağlık, Çevre, Bilim, Eğitim, Ekonomi, Seyahat, Moda, Kültür, Suç, Yemek, Yaşam Tarzı, İş Dünyası, Dünya Haberleri, Oyun, Otomotiv, Sanat, Tarih, Uzay, İlişkiler, Din, Ruh Sağlığı, Magazin (or 'Genel' if none fit).
    
    Format your response as JSON with keys: "title", "short_summary", "detailed_summary", "category"
    
    Articles:
    {articles_combined}
    """
    
    response_text = call_gemini(combined_prompt)
    
    try:
        # Parse JSON response
        ai_response = json.loads(response_text)
        
        result = {
            "id": None,
            "articleId": str(uuid.uuid4()),
            "title": ai_response.get("title", ""),
            "summary": ai_response.get("short_summary", ""),
            "longerSummary": ai_response.get("detailed_summary", ""),
            "category": ai_response.get("category", "Genel"),
            "content": "",
            "tags": [],
            "source": list({a["url"].strip() for a in articles if a.get("url")}),
            "location": None,
            "popularityScore": 0,
            "createdAt": datetime.now().isoformat(),
            "image": None,
            "priority": None
        }
    except json.JSONDecodeError:
        # Fallback to original method if JSON parsing fails
        print("⚠️ Failed to parse AI response as JSON, falling back to individual calls")
        result = process_articles_with_ai_individual_calls(articles)
        
    return result

def process_articles_with_ai_individual_calls(articles):
    # Original implementation as a fallback
    articles_combined = "\n".join([json.dumps(a, ensure_ascii=False) for a in articles])
    
    prompts = {
        "title": "Bu haber makalelerine dayanarak, 2-3 kelimelik nesnel bir başlık oluştur, bana seçenek verme, sadece salt bilgi içeren başlık ver:",
        "short_summary": "Bu haber makalelerine dayanarak, 10-25 karakter arasında kısa, salt bilgi içeren bir özet oluştur:",
        "detailed_summary": "Bu haber makalelerine dayanarak detaylı ve salt bilgi içeren kombine bir metin oluştur. Tek makale olsun: ",
        "category": """
        Bu haber makalesini aşağıdaki kategorilerden birine ata:
        Siyaset, Eğlence, Spor, Teknoloji, Sağlık, Çevre, Bilim, Eğitim,
        Ekonomi, Seyahat, Moda, Kültür, Suç, Yemek, Yaşam Tarzı, İş Dünyası,
        Dünya Haberleri, Oyun, Otomotiv, Sanat, Tarih, Uzay, İlişkiler, Din,
        Ruh Sağlığı, Magazin. Eğer bulamazsan 'Genel' yaz. Başka bir şey yazma.
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

# ======== OPTIMIZED ARTICLE SAVING ========
def save_article_folder(article_data):
    """Save article data and fetch image in parallel"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    folder_name = f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    folder_path = OUTPUT_DIR / folder_name
    os.makedirs(folder_path, exist_ok=True)
    
    # Start image fetch in a separate thread
    if article_data.get("source"):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(fetch_article_images_parallel, article_data["source"], folder_path)
            
            # Write JSON while image is being fetched
            article_json_path = folder_path / "article.json"
            with open(article_json_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=4)
            
            # Get image result
            article_data["image"] = future.result()
            
            # Update JSON with image info
            if article_data["image"]:
                with open(article_json_path, 'w', encoding='utf-8') as f:
                    json.dump(article_data, f, ensure_ascii=False, indent=4)
    else:
        # No source URLs, just save the JSON
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

# ======== PARALLEL UPLOADING ========
def send_article_with_image(folder_path):
    """Upload a single article with its image"""
    json_path = folder_path / "article.json"
    image_path = folder_path / "image.jpg"

    if not json_path.exists():
        print(f"❌ Missing article.json at {folder_path}")
        return False

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
            return True
        else:
            print(f"❌ Upload failed: {response.status_code} → {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error uploading {folder_path}: {str(e)}")
        return False

def send_all_articles():
    """Upload all articles in parallel with throttling"""
    if not OUTPUT_DIR.exists():
        print("❌ No output directory.")
        return

    folders = [f for f in OUTPUT_DIR.iterdir() if f.is_dir()]
    if not folders:
        print("❌ No folders to send.")
        return

    print(f"🚀 Sending {len(folders)} articles...")
    
    # Use ThreadPoolExecutor with a limited number of workers to avoid overwhelming the server
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(send_article_with_image, folder) for folder in folders]
        
        # Wait for all uploads to complete
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        success_count = sum(1 for result in results if result)
        print(f"✅ {success_count}/{len(folders)} uploads completed successfully.")

# ======== PARALLEL DIRECTORY PROCESSING ========
def process_news_directory(news_dir):
    """Process a single news directory"""
    print(f"Processing directory: {news_dir}")
    articles = read_json_files(news_dir)
    
    if not articles:
        print(f"⚠️ No articles found in {news_dir}. Skipping.")
        return
    
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
        return
    
    processed_data = process_articles_with_ai(filtered_articles)
    save_article_folder(processed_data)

# ======== MAIN FUNCTION ========
def main():
    news_dirs = find_matched_news_dirs(INPUT_DIR)
    
    if not news_dirs:
        print("❌ No matched news directories.")
        return
    
    print(f"🔍 Found {len(news_dirs)} groups.")
    
    # Process directories in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_news_directory, news_dirs)
    
    # Send all processed articles to backend
    # Uncomment to enable upload
    # send_all_articles()
    
    print("🎉 Done!")

if __name__ == "__main__":
    main()
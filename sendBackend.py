import os
import json
import requests
import re
from urllib.parse import urlparse

# ✅ Configure paths
BASE_DIR = r"C:\Users\zeyne\Desktop\bitirme\VeritasNews\Scrapper\Scraper\objectified_jsons"
EXPO_PUBLIC_API_URL = os.getenv('EXPO_PUBLIC_API_URL', 'http://144.91.84.230:8001')  # Default to your new API URL

INSERT_URL = f"{EXPO_PUBLIC_API_URL}/api/insert_single_article/"

def truncate_field(name, value, max_len=100):
    if isinstance(value, str) and len(value) > max_len:
        print(f"✂️ Truncating '{name}' from {len(value)} to {max_len} chars")
        return value[:max_len]
    return value

def extract_source_name(source):
    """
    This function will extract only the domain name (e.g., 'sozcu.com') from a URL.
    If the source is already a name, it will return it as is.
    """
    if isinstance(source, list):
        # If the source is a list, extract domain names for all URLs
        return [urlparse(s).netloc.split('.')[1] if urlparse(s).netloc else s for s in source]
    
    if source:
        # If the source is a URL, extract the domain name
        parsed_url = urlparse(source)
        if parsed_url.netloc:
            return parsed_url.netloc.split('.')[1]  # Extract domain name part (e.g., 'sozcu' from 'sozcu.com')
        else:
            return source  # If it's already a name, return as is
    return ""

def send_article_with_image(folder_path):
    json_path = os.path.join(folder_path, "article.json")
    image_path = os.path.join(folder_path, "image.jpg")

    if not os.path.exists(json_path):
        print(f"❌ Missing article.json in {folder_path}")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Truncate long fields
        json_data["articleId"] = truncate_field("articleId", json_data.get("articleId", ""))
        json_data["category"] = truncate_field("category", json_data.get("category", ""))
        json_data["location"] = truncate_field("location", json_data.get("location", ""))

        # Extract source name (e.g., 'sozcu', 'cnn') from the full URL
        source = json_data.get("source")
        
        # Handle if source is a list or string
        json_data["source"] = extract_source_name(source)

        # Prepare multipart/form-data
        files = {}
        if os.path.exists(image_path):
            files["image"] = open(image_path, "rb")

        payload = {
            "data": json.dumps(json_data)
        }

        print(f"\n📤 Sending article from: {os.path.basename(folder_path)}")
        response = requests.post(INSERT_URL, data=payload, files=files)

        if "image" in files:
            files["image"].close()

        if response.status_code == 201:
            print(f"✅ Success: {os.path.basename(folder_path)}")
        else:
            print(f"❌ Failed: {os.path.basename(folder_path)} → {response.text}")

    except Exception as e:
        print(f"❌ Error processing {folder_path}: {str(e)}")

# ✅ Main loop
def send_all_articles():
    if not os.path.exists(BASE_DIR):
        print(f"❌ Directory not found: {BASE_DIR}")
        return

    folders = [f for f in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, f))]

    if not folders:
        print("❌ No article folders found in the directory.")
        return

    print(f"🔍 Found {len(folders)} article folders. Starting upload...")

    for folder in folders:
        folder_path = os.path.join(BASE_DIR, folder)
        send_article_with_image(folder_path)

    print("✅ All articles processed.")

# ✅ Main execution
if __name__ == "__main__":
    print("🚀 Starting article & image upload process...")
    send_all_articles()
    print("🏁 Upload completed!")

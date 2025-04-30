import os
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
from io import BytesIO
import config

# === CONFIGURATION ===
GENERATED_ARTICLE_DIR = config.OBJECTIVE_ARTICLES_DIR  # Directory with generated article JSONs
OUTPUT_DIR = config.IMAGED_JSON_DIR   # Output directory for updated JSONs
#OUTPUT_IMG_DIR = config.IMAGE_DIR              # Directory to save downloaded images


# === Sanitize title to create a folder-safe name ===
def slugify(text):
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in text.strip())[:60]

# === Extract <meta property="og:image"> ===
def extract_og_image(soup):
    tag = soup.find("meta", property="og:image")
    if tag and tag.get("content"):
        return tag["content"]
    return None

# === Fallback <img> extraction ===
def extract_first_article_img(soup):
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and src.startswith("http"):
            return src
    return None

# === Download and save image ===
def download_image(url, save_path):
    try:
        r = requests.get(url, timeout=10)
        img = Image.open(BytesIO(r.content))
        img.save(save_path)
        return True
    except Exception as e:
        print(f"❌ Could not download image {url}: {e}")
        return False

# === Process one summary article ===
def process_article(json_path: Path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("title", "").strip()
    source_urls = data.get("source", [])
    if not title or not source_urls:
        print(f"⚠️ Skipping {json_path.name}: missing title or source.")
        return

    folder_name = slugify(title)
    article_dir = OUTPUT_DIR / folder_name
    article_dir.mkdir(parents=True, exist_ok=True)

    img_path = article_dir / "image.jpg"
    json_out_path = article_dir / "article.json"

    for url in source_urls:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")

            img_url = extract_og_image(soup) or extract_first_article_img(soup)
            if img_url and download_image(img_url, img_path):
                data["image"] = "image.jpg"
                break
        except Exception as e:
            print(f"⚠️ Error accessing {url}: {e}")

    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved: {folder_name}")

def main():
    if not GENERATED_ARTICLE_DIR.exists():
        print(f"❌ Folder not found: {GENERATED_ARTICLE_DIR}")
        return

    for subdir in GENERATED_ARTICLE_DIR.iterdir():
        article_json = subdir / "article.json"
        if article_json.exists():
            process_article(article_json)

if __name__ == "__main__":
    main()
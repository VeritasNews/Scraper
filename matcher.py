import os
import json
import shutil
import time
import numpy as np
from collections import defaultdict
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util
from config import PULLED_ARTICLES_SAVE_DIR, GROUPED_ARTICLES_DIR, CACHE_FILE

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
SIMILARITY_THRESHOLD = 0.75
MIN_INTERNAL_SIMILARITY = 0.70
model = SentenceTransformer(MODEL_NAME, device="cpu")

# Load embedding cache
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        embedding_cache = json.load(f)
else:
    embedding_cache = {}

def get_article_id(file_path):
    return os.path.basename(file_path)

def batch_encode_and_cache(texts, file_paths):
    uncached_texts, uncached_paths = [], []
    for text, path in zip(texts, file_paths):
        if get_article_id(path) not in embedding_cache:
            uncached_texts.append(text)
            uncached_paths.append(path)
    if uncached_texts:
        print(f"🔄 Caching {len(uncached_texts)} new embeddings...")
        embeddings = model.encode(uncached_texts, convert_to_numpy=True, show_progress_bar=True, batch_size=32)
        for emb, path in zip(embeddings, uncached_paths):
            embedding_cache[get_article_id(path)] = emb.tolist()
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(embedding_cache, f)

def get_embedding(file_path):
    return np.array(embedding_cache[get_article_id(file_path)], dtype=np.float32)

def match_articles():
    start_time = time.time()
    print("🚀 Starting Matching...")

    # Destination structure
    os.makedirs(GROUPED_ARTICLES_DIR, exist_ok=True)
    unmatched_dir = os.path.join(GROUPED_ARTICLES_DIR, "still_unmatched")
    os.makedirs(unmatched_dir, exist_ok=True)

    # Determine whether first run
    is_first_run = not any(f.startswith("group_") for f in os.listdir(GROUPED_ARTICLES_DIR))
    unmatched_articles, unmatched_texts = [], []

    if is_first_run:
        print("🔰 Initial run: loading from pulled_articles...")
        source_dir = PULLED_ARTICLES_SAVE_DIR
        for fname in os.listdir(source_dir):
            if not fname.endswith(".json"): continue
            fpath = os.path.join(source_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                title = data.get("title", "").strip()
                content = data.get("content", "").strip()
                if len(content.split()) > 50:
                    enriched = f"{title}. {title}. {content}"
                    unmatched_articles.append(fpath)
                    unmatched_texts.append(enriched)
                else:
                    shutil.copy(fpath, os.path.join(unmatched_dir, fname))
    else:
        print("🔁 Incremental run: loading from still_unmatched...")
        for fname in os.listdir(unmatched_dir):
            if not fname.endswith(".json"): continue
            fpath = os.path.join(unmatched_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                title = data.get("title", "").strip()
                content = data.get("content", "").strip()
                text = f"{title}. {title}. {content}"
                unmatched_articles.append(fpath)
                unmatched_texts.append(text)

    if not unmatched_articles:
        print("⚠️ No articles to match.")
        return

    batch_encode_and_cache(unmatched_texts, unmatched_articles)
    unmatched_embeddings = [get_embedding(fp) for fp in unmatched_articles]

    # Load groups
    grouped_articles, group_embeddings = {}, {}
    existing_group_ids = [int(f.split("_")[-1]) for f in os.listdir(GROUPED_ARTICLES_DIR) if f.startswith("group_")]
    current_gid = max(existing_group_ids, default=0) + 1

    for folder in os.listdir(GROUPED_ARTICLES_DIR):
        if not folder.startswith("group_"): continue
        gid = int(folder.split("_")[-1])
        group_path = os.path.join(GROUPED_ARTICLES_DIR, folder)
        articles, embeddings = [], []
        for f in os.listdir(group_path):
            if not f.endswith(".json"): continue
            fpath = os.path.join(group_path, f)
            with open(fpath, "r", encoding="utf-8") as f_json:
                data = json.load(f_json)
                title = data.get("title", "").strip()
                content = data.get("content", "").strip()
                text = f"{title}. {title}. {content}"
                articles.append((fpath, text))
                embeddings.append(get_embedding(fpath))
        grouped_articles[gid] = articles
        group_embeddings[gid] = embeddings

    matched_indices = set()
    newly_created = 0

    for idx, emb in enumerate(unmatched_embeddings):
        best_group_id, best_score = None, 0
        for gid, group_embs in group_embeddings.items():
            if not group_embs: continue
            sims = util.cos_sim(emb, np.vstack(group_embs))[0].cpu().numpy()
            if sims.min() > best_score:
                best_score = sims.min()
                best_group_id = gid

        if best_score >= SIMILARITY_THRESHOLD:
            grouped_articles[best_group_id].append((unmatched_articles[idx], unmatched_texts[idx]))
            group_embeddings[best_group_id].append(emb)
            matched_indices.add(idx)
            continue

        for jdx, other_emb in enumerate(unmatched_embeddings):
            if jdx == idx or jdx in matched_indices: continue
            sim = util.cos_sim(emb, other_emb)[0].cpu().item()
            if sim >= SIMILARITY_THRESHOLD:
                grouped_articles[current_gid] = [
                    (unmatched_articles[idx], unmatched_texts[idx]),
                    (unmatched_articles[jdx], unmatched_texts[jdx])
                ]
                group_embeddings[current_gid] = [emb, other_emb]
                matched_indices.update([idx, jdx])
                current_gid += 1
                newly_created += 1
                break

    # Save groups
    for gid, articles in grouped_articles.items():
        if not any(f.startswith("group_") and int(f.split("_")[-1]) == gid for f in os.listdir(GROUPED_ARTICLES_DIR)):
            os.makedirs(os.path.join(GROUPED_ARTICLES_DIR, f"group_{gid}"), exist_ok=True)
        for fpath, _ in articles:
            dest = os.path.join(GROUPED_ARTICLES_DIR, f"group_{gid}", os.path.basename(fpath))
            if os.path.exists(fpath):
                try:
                    shutil.move(fpath, dest)
                except FileNotFoundError:
                    pass

    for idx, fpath in enumerate(unmatched_articles):
        if idx not in matched_indices and os.path.exists(fpath):
            dest = os.path.join(unmatched_dir, os.path.basename(fpath))
            try:
                shutil.move(fpath, dest)
            except FileNotFoundError:
                continue

    print(f"✅ Matching done in {time.time() - start_time:.2f} seconds.")
    print(f"🔗 Articles matched to existing groups: {len(matched_indices)}")
    print(f"🌱 New groups created: {newly_created}")
    print(f"📌 Remaining unmatched: {len(unmatched_articles) - len(matched_indices)}")

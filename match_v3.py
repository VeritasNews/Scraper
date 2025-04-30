import os
import json
import shutil
import time
import numpy as np
from collections import defaultdict
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util
from config import GROUPED_ARTICLES_DIR, CACHE_FILE, NEW_ARTICLES_LOG_DIR

DEST_DIR = GROUPED_ARTICLES_DIR
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
model = SentenceTransformer(MODEL_NAME, device="cpu")

# Load cache
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        embedding_cache = json.load(f)
else:
    embedding_cache = {}

def get_article_id(file_path):
    return os.path.basename(file_path)

def batch_encode_and_cache(texts, file_paths):
    uncached_texts = []
    uncached_paths = []
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

def match_v3_run():
    start_time = time.time()
    print("\n🚀 Starting match_v3_run...")

    grouped_articles, group_embeddings = {}, {}
    newly_created_groups, newly_matched_to_existing = set(), set()
    moved_files = set()

    # Load existing groups
    for folder in os.listdir(GROUPED_ARTICLES_DIR):
        if folder.startswith("group_"):
            group_id = int(folder.split("_")[-1])
            folder_path = os.path.join(GROUPED_ARTICLES_DIR, folder)
            articles = []
            for file in os.listdir(folder_path):
                if file.endswith(".json"):
                    file_path = os.path.join(folder_path, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        title = data.get("title", "").strip()
                        content = data.get("content", "").strip()
                        text = f"{title}. {title}. {content}"
                        if text:
                            articles.append((file_path, text))
            if articles:
                grouped_articles[group_id] = articles
                group_embeddings[group_id] = [
                    get_embedding(fp) for fp, _ in articles if get_article_id(fp) in embedding_cache
                ]

    print(f"✅ Loaded {len(grouped_articles)} groups.")

    # Load unmatched
    unmatched_articles, unmatched_texts = [], []
    unmatched_path = os.path.join(GROUPED_ARTICLES_DIR, "still_unmatched")

    if os.path.exists(unmatched_path):
        for file in os.listdir(unmatched_path):
            if file.endswith(".json"):
                file_path = os.path.join(unmatched_path, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    title = data.get("title", "").strip()
                    content = data.get("content", "").strip()
                    text = f"{title}. {title}. {content}"
                    if text:
                        unmatched_articles.append(file_path)
                        unmatched_texts.append(text)

    if os.path.exists(NEW_ARTICLES_LOG_DIR):
        with open(NEW_ARTICLES_LOG_DIR, "r", encoding="utf-8") as f:
            for file_path in f:
                file_path = file_path.strip()
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f_json:
                        data = json.load(f_json)
                        title = data.get("title", "").strip()
                        content = data.get("content", "").strip()
                        text = f"{title}. {title}. {content}"
                        if text and file_path not in unmatched_articles:
                            unmatched_articles.append(file_path)
                            unmatched_texts.append(text)

    print(f"\n✅ Loaded {len(unmatched_texts)} unmatched articles.")
    if not unmatched_articles:
        print("\n⚠️ No unmatched articles to process.")
        return

    print("\n🔄 Generating embeddings for unmatched articles in batch...")
    batch_encode_and_cache(unmatched_texts, unmatched_articles)
    unmatched_embeddings = [get_embedding(fp) for fp in unmatched_articles]

    matched_unmatched = set()
    new_group_counter = max(grouped_articles.keys(), default=0) + 1
    new_group_count = 0

    # ... (tüm importlar ve üstteki kodlar aynı)

    # Matching
    for idx, unmatched_emb in enumerate(unmatched_embeddings):
        file_path = unmatched_articles[idx]
        unmatched_text = unmatched_texts[idx]
        best_group_id, best_similarity = None, 0

        # 🔍 Check similarity to existing groups
        for group_id, emb_list in group_embeddings.items():
            if emb_list:
                emb_matrix = np.vstack(emb_list)
                sim_scores = util.cos_sim(unmatched_emb, emb_matrix)[0].cpu().numpy()
                min_similarity = np.min(sim_scores)
                if min_similarity > best_similarity:
                    best_similarity = min_similarity
                    best_group_id = group_id

        if best_similarity >= 0.75:
            grouped_articles[best_group_id].append((file_path, unmatched_text))
            group_embeddings[best_group_id].append(unmatched_emb)
            matched_unmatched.add(idx)
            newly_matched_to_existing.add(file_path)
            continue

        # 🤝 Check pairwise similarity to other unmatched articles (but avoid self or same text)
        for jdx, other_emb in enumerate(unmatched_embeddings):
            if jdx == idx or jdx in matched_unmatched:
                continue

            # 💥 Don't allow match if texts are identical (avoid self-matching clone)
            if unmatched_texts[idx].strip() == unmatched_texts[jdx].strip():
                continue

            sim = util.cos_sim(unmatched_emb, other_emb)[0].cpu().item()
            if sim >= 0.75:
                grouped_articles[new_group_counter] = [
                    (file_path, unmatched_text),
                    (unmatched_articles[jdx], unmatched_texts[jdx])
                ]
                group_embeddings[new_group_counter] = [unmatched_emb, other_emb]
                matched_unmatched.update([idx, jdx])
                newly_created_groups.add(new_group_counter)
                new_group_counter += 1
                new_group_count += 1
                break

    # 🔥 Remove groups that accidentally only had one item
    for gid in list(newly_created_groups):
        if len(grouped_articles[gid]) <= 1:
            del grouped_articles[gid]
            del group_embeddings[gid]
            newly_created_groups.remove(gid)

# ... (aşağıdaki "save" ve "print" kısımları aynı şekilde devam edebilir)


    # Save new groups
    for group_id in newly_created_groups:
        articles = grouped_articles[group_id]
        group_folder = os.path.join(DEST_DIR, f"group_{group_id}")
        os.makedirs(group_folder, exist_ok=True)
        for file_path, _ in articles:
            dest_file = os.path.join(group_folder, os.path.basename(file_path))
            if os.path.exists(file_path):
                try:
                    shutil.move(file_path, dest_file)
                    moved_files.add(file_path)
                except FileNotFoundError:
                    continue

    # Save unmatched
    still_unmatched_dir = os.path.join(DEST_DIR, "still_unmatched")
    os.makedirs(still_unmatched_dir, exist_ok=True)
    for idx, file_path in enumerate(unmatched_articles):
        if idx not in matched_unmatched and os.path.exists(file_path):
            dest_path = os.path.join(still_unmatched_dir, os.path.basename(file_path))
            if not (os.path.exists(dest_path) and os.path.samefile(file_path, dest_path)):
                try:
                    shutil.move(file_path, dest_path)
                except FileNotFoundError:
                    continue

    end_time = time.time()
    print("\n✅ Matching and grouping completed.")
    print(f"📆 Total groups formed: {len(grouped_articles)}")
    print(f"⏱️ Execution time: {end_time - start_time:.2f} seconds")
    print(f"📁 Still unmatched articles saved to: {still_unmatched_dir}")
    print("\n📊 Match Summary:")
    print(f"🔗 Matched to existing groups: {len(newly_matched_to_existing)}")
    print(f"🌟 New groups created: {len(newly_created_groups)}")
    print(f"📌 Remaining unmatched: {len(unmatched_articles) - len(matched_unmatched)}")

import os
import json
import shutil
import time
import numpy as np
from sentence_transformers import SentenceTransformer, util
from config import PULLED_ARTICLES_SAVE_DIR, GROUPED_ARTICLES_DIR, CACHE_FILE

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
SIMILARITY_THRESHOLD = 0.75
MIN_INTERNAL_SIMILARITY = 0.70
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
    start = time.time()
    os.makedirs(GROUPED_ARTICLES_DIR, exist_ok=True)
    unmatched_dir = os.path.join(GROUPED_ARTICLES_DIR, "still_unmatched")
    os.makedirs(unmatched_dir, exist_ok=True)

    is_first = not any(f.startswith("group_") for f in os.listdir(GROUPED_ARTICLES_DIR))
    articles, texts = [], []

    source_dir = PULLED_ARTICLES_SAVE_DIR if is_first else unmatched_dir

    for fname in os.listdir(source_dir):
        if not fname.endswith(".json"): continue
        fpath = os.path.join(source_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                title = data.get("title", "").strip()
                content = data.get("content", "").strip()
                if len(content.split()) < 50:
                    dst = os.path.join(unmatched_dir, fname)
                    if os.path.abspath(fpath) != os.path.abspath(dst):
                        shutil.copy(fpath, dst)
                    continue
                text = f"{title}. {title}. {content}"
                articles.append(fpath)
                texts.append(text)
        except:
            dst = os.path.join(unmatched_dir, fname)
            if os.path.abspath(fpath) != os.path.abspath(dst):
                shutil.copy(fpath, dst)

    if not articles:
        print("⚠️ No articles found.")
        return

    batch_encode_and_cache(texts, articles)
    embeddings = [get_embedding(fp) for fp in articles]

    n = len(articles)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        root_x, root_y = find(x), find(y)
        if root_x != root_y:
            parent[root_y] = root_x

    print(f"🔗 Matching {n} articles with threshold {SIMILARITY_THRESHOLD}")
    for i in range(n):
        for j in range(i + 1, n):
            sim = util.cos_sim(embeddings[i], embeddings[j])[0].cpu().item()
            if sim >= SIMILARITY_THRESHOLD:
                union(i, j)

    clusters = {}
    for idx in range(n):
        root = find(idx)
        clusters.setdefault(root, []).append(idx)

    group_ids = [int(f.split("_")[-1]) for f in os.listdir(GROUPED_ARTICLES_DIR) if f.startswith("group_")]
    next_gid = max(group_ids, default=0) + 1
    grouped_count = 0

    for members in clusters.values():
        if len(members) < 2:
            continue
        embed_matrix = np.vstack([embeddings[i] for i in members])
        sim_matrix = util.cos_sim(embed_matrix, embed_matrix).cpu().numpy()
        tril = sim_matrix[np.tril_indices_from(sim_matrix, k=-1)]
        
        # 🔒 Yeni: MIN kontrolünü min üzerinden yap
        if len(tril) == 0 or np.min(tril) < MIN_INTERNAL_SIMILARITY:
            continue

        group_path = os.path.join(GROUPED_ARTICLES_DIR, f"group_{next_gid}")
        os.makedirs(group_path, exist_ok=True)
        for i in members:
            fname = os.path.basename(articles[i])
            dst = os.path.join(group_path, fname)
            if os.path.exists(articles[i]):
                shutil.move(articles[i], dst)
        grouped_count += 1
        next_gid += 1

    for idx in range(n):
        if find(idx) == idx and not any(idx in grp for grp in clusters.values() if len(grp) >= 2):
            src = articles[idx]
            dst = os.path.join(unmatched_dir, os.path.basename(src))
            if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
                shutil.move(src, dst)

    print(f"✅ Matching done in {time.time() - start:.2f}s")
    print(f"📦 Groups formed: {grouped_count}")
    print(f"📌 Still unmatched: {sum(1 for idx in range(n) if find(idx) == idx and not any(idx in g for g in clusters.values() if len(g) >= 2))}")
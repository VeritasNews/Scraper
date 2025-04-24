import os
import json
import shutil
import time
import numpy as np
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from sentence_transformers import SentenceTransformer, util
import config

# --- CONFIGURATION ---
start_time = time.time()
print("🚀 Start Matching Module")

SOURCE_DIR = config.PULLED_ARTICLES_SAVE_DIR
DEST_DIR = config.GROUPED_ARTICLES_PULL_DIR
SIMILARITY_THRESHOLD = 0.75
MIN_INTERNAL_SIMILARITY = 0.75
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# --- SETUP OUTPUT FOLDERS ---
os.makedirs(DEST_DIR, exist_ok=True)
not_matched_dir = os.path.join(DEST_DIR, "not_matched")
os.makedirs(not_matched_dir, exist_ok=True)

# --- LOAD ARTICLES ---
json_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".json")]
articles, file_paths, titles = [], [], []

for filename in json_files:
    path = os.path.join(SOURCE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            title = data.get("title", "").strip()
            content = data.get("content", "").strip()
            if len(content.split()) > 50:  # Filter out short texts
                enriched_text = f"{title}. {title}. {content}"  # Emphasize title
                articles.append(enriched_text)
                file_paths.append(path)
                titles.append(title)
            else:
                shutil.copy(path, os.path.join(not_matched_dir, filename))
    except Exception as e:
        print(f"⚠️ Error parsing {filename}: {e}")
        shutil.copy(path, os.path.join(not_matched_dir, filename))

print(f"✅ Loaded {len(articles)} valid articles.")

# --- EMBEDDING ---
print("🔄 Generating embeddings...")
model = SentenceTransformer(MODEL_NAME)
embeddings = model.encode(articles, convert_to_tensor=True)
similarity_matrix = util.pytorch_cos_sim(embeddings, embeddings).numpy()

# --- UNION-FIND SETUP ---
parent = list(range(len(articles)))

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(x, y):
    root_x, root_y = find(x), find(y)
    if root_x != root_y:
        parent[root_y] = root_x

# --- PARALLEL MATCHING ---
def process_chunk(start, end):
    for i in range(start, end):
        for j in range(i + 1, len(articles)):
            if similarity_matrix[i][j] >= SIMILARITY_THRESHOLD:
                union(i, j)

print("🚀 Matching articles...")
chunk_size = len(articles) // 8 + 1
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(process_chunk, i, min(i + chunk_size, len(articles)))
               for i in range(0, len(articles), chunk_size)]
    for f in futures:
        f.result()

# --- COLLECT & SAVE GROUPS ---
groups = defaultdict(list)
for idx in range(len(articles)):
    groups[find(idx)].append(idx)

matched_indices = set()
group_number = 1

for group_indices in groups.values():
    if len(group_indices) <= 1:
        continue
    # Check internal group similarity
    internal_scores = [similarity_matrix[i][j] for i in group_indices for j in group_indices if i < j]
    avg_sim = np.mean(internal_scores) if internal_scores else 0
    if avg_sim < MIN_INTERNAL_SIMILARITY:
        continue

    group_name = f"group_{group_number}"
    group_path = os.path.join(DEST_DIR, group_name)
    os.makedirs(group_path, exist_ok=True)

    print(f"\n📦 {group_name} ({len(group_indices)} articles, avg_sim={avg_sim:.3f})")
    for idx in group_indices:
        matched_indices.add(idx)
        shutil.copy(file_paths[idx], os.path.join(group_path, os.path.basename(file_paths[idx])))
        print(f"📁 {titles[idx]}")
    group_number += 1

# --- UNMATCHED ARTICLES ---
for idx in range(len(articles)):
    if idx not in matched_indices:
        shutil.copy(file_paths[idx], os.path.join(not_matched_dir, os.path.basename(file_paths[idx])))

print(f"\n✅ Grouping complete. Total matched groups: {group_number - 1}")
print(f"📂 Unmatched articles saved to: {not_matched_dir}")
print(f"⏱️ Execution time: {time.time() - start_time:.2f} seconds")
